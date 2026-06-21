import logging

from django.core.cache import cache
from django.test import override_settings

import pytest

from portal.services.omada import get_success_redirect_url


def test_secure_ssl_redirect_is_env_controlled(settings):
    assert hasattr(settings, "SECURE_SSL_REDIRECT")


def test_allowed_redirect_hosts_setting_controls_omada_redirect(settings):
    settings.ALLOWED_HOSTS = ["portal.example.com"]
    settings.PORTAL_ALLOWED_REDIRECT_HOSTS = ["guest.example.com"]
    settings.SUCCESS_REDIRECT_URL = "/success/"

    assert (
        get_success_redirect_url("https://guest.example.com/welcome")
        == "https://guest.example.com/welcome"
    )
    assert (
        get_success_redirect_url("https://evil.example.com/phish")
        == "/success/"
    )


def test_bare_hostname_redirect_url_is_normalized_to_https(settings):
    settings.ALLOWED_HOSTS = ["portal.example.com"]
    settings.PORTAL_ALLOWED_REDIRECT_HOSTS = ["www.google.com"]
    settings.SUCCESS_REDIRECT_URL = "/success/"

    assert get_success_redirect_url("www.google.com") == "https://www.google.com"


def test_absolute_https_redirect_url_stays_unchanged(settings):
    settings.ALLOWED_HOSTS = ["portal.example.com"]
    settings.PORTAL_ALLOWED_REDIRECT_HOSTS = ["www.google.com"]
    settings.SUCCESS_REDIRECT_URL = "/success/"

    assert (
        get_success_redirect_url("https://www.google.com")
        == "https://www.google.com"
    )


def test_invalid_redirect_target_falls_back_to_success_page(settings):
    settings.ALLOWED_HOSTS = ["portal.example.com"]
    settings.PORTAL_ALLOWED_REDIRECT_HOSTS = ["www.google.com"]
    settings.SUCCESS_REDIRECT_URL = "/success/"

    assert get_success_redirect_url("javascript:alert(1)") == "/success/"


def test_bare_hostname_success_redirect_url_is_normalized_to_https(settings):
    settings.ALLOWED_HOSTS = ["portal.example.com"]
    settings.PORTAL_ALLOWED_REDIRECT_HOSTS = []
    settings.SUCCESS_REDIRECT_URL = "www.google.com"

    assert (
        get_success_redirect_url("https://evil.example.com/phish")
        == "https://www.google.com"
    )


@pytest.mark.django_db
def test_form_submission_logs_request_id(client, caplog, monkeypatch, settings):
    settings.OMADA_ENABLED = False
    settings.PORTAL_RATE_LIMIT_ENABLED = False
    caplog.set_level(logging.INFO)
    monkeypatch.setattr("portal.views.send_session_to_google_sheets", lambda session: None)

    response = client.post(
        "/portal/submit/",
        data={
            "full_name": "Logged Guest",
            "email": "logged@example.com",
            "room_number": "101",
            "terms_accepted": "on",
            "clientMac": "AA:BB:CC:DD:EE:10",
        },
    )

    assert response.status_code == 302
    assert "request_id=" in caplog.text
    assert "logged@example.com" not in caplog.text


@pytest.mark.django_db
@override_settings(
    PORTAL_RATE_LIMIT_ENABLED=True,
    PORTAL_RATE_LIMIT_ATTEMPTS=1,
    PORTAL_RATE_LIMIT_WINDOW_SECONDS=60,
)
def test_portal_submit_rate_limiter_returns_friendly_error(
    client,
    monkeypatch,
):
    cache.clear()
    monkeypatch.setattr(
        "portal.views.authorize_guest_session",
        lambda session, **kwargs: type("Result", (), {"success": False, "skipped": True})(),
    )
    monkeypatch.setattr("portal.views.send_session_to_google_sheets", lambda session: None)
    data = {
        "full_name": "Rate Limited Guest",
        "email": "rate@example.com",
        "room_number": "102",
        "terms_accepted": "on",
        "clientMac": "AA:BB:CC:DD:EE:11",
    }

    first_response = client.post("/portal/submit/", data=data, REMOTE_ADDR="198.51.100.1")
    second_response = client.post("/portal/submit/", data=data, REMOTE_ADDR="198.51.100.1")

    assert first_response.status_code == 302
    assert second_response.status_code == 429
    assert "Please wait a moment and try again." in second_response.content.decode()


def test_live_commissioning_checklist_exists_and_has_emergency_fallback():
    content = open("docs/live-commissioning-checklist.md", encoding="utf-8").read()

    assert "Pre-deployment" in content
    assert "OC200 reachable from Dokploy over VPN/tunnel." in content
    assert "Connect iPhone to guest Wi-Fi." in content
    assert "If the external portal fails during guest hours" in content
    assert "Use a temporary password at reception." in content
