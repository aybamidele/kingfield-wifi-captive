from io import StringIO

import pytest
import requests
from django.contrib import admin
from django.core.management import call_command
from django.test import RequestFactory
from django.utils import timezone

from portal.admin import GuestWifiSessionAdmin
from portal.models import GuestWifiSession
from portal.services.google_sheets import send_session_to_google_sheets


def make_session(**overrides):
    defaults = {
        "full_name": "Ada Lovelace",
        "email": "ada@example.com",
        "phone": "+44 7000 000000",
        "room_number": "1204",
        "terms_accepted": True,
        "terms_accepted_at": timezone.now(),
        "marketing_consent": False,
        "client_mac": "AA:BB:CC:DD:EE:FF",
        "auth_duration_minutes": 1440,
        "ip_address": "203.0.113.10",
        "user_agent": "pytest browser",
    }
    defaults.update(overrides)
    return GuestWifiSession.objects.create(**defaults)


@pytest.mark.django_db
def test_google_sheets_disabled_returns_skipped_and_marks_not_configured(
    monkeypatch,
    settings,
):
    settings.GOOGLE_SHEETS_ENABLED = False
    session = make_session()

    def fail_if_called(*args, **kwargs):
        raise AssertionError("Google Sheets webhook should not be called")

    monkeypatch.setattr("portal.services.google_sheets.requests.post", fail_if_called)

    result = send_session_to_google_sheets(session)

    session.refresh_from_db()
    assert result.outcome == "skipped"
    assert (
        session.google_sheets_status
        == GuestWifiSession.GoogleSheetsStatus.NOT_CONFIGURED
    )
    assert session.google_sheets_sent_at is None
    assert session.google_sheets_error == ""


@pytest.mark.django_db
def test_successful_webhook_post_sends_payload_and_marks_sent(monkeypatch, settings):
    settings.GOOGLE_SHEETS_ENABLED = True
    settings.GOOGLE_SHEETS_WEBHOOK_URL = "https://script.google.com/example"
    settings.GOOGLE_SHEETS_WEBHOOK_SECRET = "shared-secret"
    settings.GOOGLE_SHEETS_TIMEOUT_SECONDS = 2
    session = make_session(
        ap_mac="11:22:33:44:55:66",
        gateway_mac="22:33:44:55:66:77",
        vlan_id="42",
        ssid_name="Kingfield Guest",
        radio_id="1",
        site_name="main-site",
        redirect_url="https://example.com/welcome",
    )
    calls = []

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"ok": True}

        def raise_for_status(self):
            return None

    def fake_post(url, json, timeout):
        calls.append({"url": url, "json": json, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr("portal.services.google_sheets.requests.post", fake_post)

    result = send_session_to_google_sheets(session)

    session.refresh_from_db()
    assert result.outcome == "success"
    assert calls == [
        {
            "url": "https://script.google.com/example",
            "json": {
                "secret": "shared-secret",
                "session_id": str(session.id),
                "created_at": session.created_at.isoformat(),
                "full_name": "Ada Lovelace",
                "email": "ada@example.com",
                "phone": "+44 7000 000000",
                "room_number": "1204",
                "terms_accepted": True,
                "terms_accepted_at": session.terms_accepted_at.isoformat(),
                "marketing_consent": False,
                "marketing_consent_at": None,
                "client_mac": "AA:BB:CC:DD:EE:FF",
                "ap_mac": "11:22:33:44:55:66",
                "gateway_mac": "22:33:44:55:66:77",
                "vlan_id": "42",
                "ssid_name": "Kingfield Guest",
                "radio_id": "1",
                "site_name": "main-site",
                "redirect_url": "https://example.com/welcome",
                "auth_status": "pending",
                "ip_address": "203.0.113.10",
                "user_agent": "pytest browser",
            },
            "timeout": 2,
        }
    ]
    assert session.google_sheets_status == GuestWifiSession.GoogleSheetsStatus.SENT
    assert session.google_sheets_sent_at is not None
    assert session.google_sheets_response == {
        "status_code": 200,
        "body": {"ok": True},
    }
    assert session.google_sheets_error == ""


@pytest.mark.django_db
def test_webhook_timeout_marks_failed_without_logging_secret(
    caplog,
    monkeypatch,
    settings,
):
    settings.GOOGLE_SHEETS_ENABLED = True
    settings.GOOGLE_SHEETS_WEBHOOK_URL = "https://script.google.com/example"
    settings.GOOGLE_SHEETS_WEBHOOK_SECRET = "super-secret"
    settings.GOOGLE_SHEETS_TIMEOUT_SECONDS = 1
    session = make_session()

    def fake_post(*args, **kwargs):
        raise requests.Timeout("super-secret appeared in exception text")

    monkeypatch.setattr("portal.services.google_sheets.requests.post", fake_post)

    result = send_session_to_google_sheets(session)

    session.refresh_from_db()
    assert result.outcome == "failed"
    assert session.google_sheets_status == GuestWifiSession.GoogleSheetsStatus.FAILED
    assert session.google_sheets_sent_at is None
    assert session.google_sheets_response is None
    assert session.google_sheets_error == "Timeout"
    assert "super-secret" not in caplog.text


@pytest.mark.django_db
def test_form_submission_still_succeeds_when_google_sheets_fails(
    client,
    monkeypatch,
    settings,
):
    settings.GOOGLE_SHEETS_ENABLED = True
    settings.GOOGLE_SHEETS_WEBHOOK_URL = "https://script.google.com/example"
    settings.GOOGLE_SHEETS_WEBHOOK_SECRET = "shared-secret"

    def fake_post(*args, **kwargs):
        raise requests.Timeout("network timeout")

    monkeypatch.setattr("portal.services.google_sheets.requests.post", fake_post)

    response = client.post(
        "/portal/submit/",
        data={
            "full_name": "Grace Hopper",
            "email": "grace@example.com",
            "confirm_email": "grace@example.com",
            "room_number": "803",
            "terms_accepted": "on",
            "clientMac": "AA:BB:CC:DD:EE:01",
            "apMac": "11:22:33:44:55:66",
            "ssidName": "Kingfield Guest",
            "radioId": "1",
            "site": "site-id",
        },
    )

    assert response.status_code == 302
    assert response["Location"] == "/success/"
    session = GuestWifiSession.objects.get()
    assert session.email == "grace@example.com"
    assert session.google_sheets_status == GuestWifiSession.GoogleSheetsStatus.FAILED
    assert session.google_sheets_error == "Timeout"


@pytest.mark.django_db
def test_admin_retry_action_calls_google_sheets_service(monkeypatch):
    sessions = [
        make_session(email="one@example.com"),
        make_session(email="two@example.com"),
    ]
    calls = []

    def fake_send(session):
        calls.append(session.id)

    monkeypatch.setattr(
        "portal.admin.google_sheets.send_session_to_google_sheets",
        fake_send,
    )
    model_admin = GuestWifiSessionAdmin(GuestWifiSession, admin.site)
    monkeypatch.setattr(model_admin, "message_user", lambda *args, **kwargs: None)
    request = RequestFactory().post("/admin/portal/guestwifisession/")

    model_admin.retry_google_sheets(
        request,
        GuestWifiSession.objects.filter(id__in=[session.id for session in sessions]),
    )

    assert calls == [session.id for session in sessions]


@pytest.mark.django_db
def test_management_command_dry_run_does_not_call_service(monkeypatch):
    failed_session = make_session(
        email="failed@example.com",
        google_sheets_status=GuestWifiSession.GoogleSheetsStatus.FAILED,
    )
    make_session(
        email="sent@example.com",
        google_sheets_status=GuestWifiSession.GoogleSheetsStatus.SENT,
    )

    def fail_if_called(*args, **kwargs):
        raise AssertionError("Dry run must not send to Google Sheets")

    monkeypatch.setattr(
        "portal.management.commands.resend_google_sheets_failed."
        "google_sheets.send_session_to_google_sheets",
        fail_if_called,
    )
    out = StringIO()

    call_command("resend_google_sheets_failed", "--dry-run", stdout=out)

    failed_session.refresh_from_db()
    assert "1 failed Google Sheets session would be retried." in out.getvalue()
    assert (
        failed_session.google_sheets_status
        == GuestWifiSession.GoogleSheetsStatus.FAILED
    )


@pytest.mark.django_db
def test_management_command_retries_failed_sessions_with_limit(monkeypatch):
    sessions = [
        make_session(
            email=f"failed-{index}@example.com",
            google_sheets_status=GuestWifiSession.GoogleSheetsStatus.FAILED,
        )
        for index in range(3)
    ]
    make_session(
        email="sent@example.com",
        google_sheets_status=GuestWifiSession.GoogleSheetsStatus.SENT,
    )
    calls = []

    def fake_send(session):
        calls.append(session.id)

    monkeypatch.setattr(
        "portal.management.commands.resend_google_sheets_failed."
        "google_sheets.send_session_to_google_sheets",
        fake_send,
    )
    out = StringIO()

    call_command("resend_google_sheets_failed", "--limit", "2", stdout=out)

    assert calls == [session.id for session in sessions[:2]]
    assert "Retried 2 failed Google Sheets session(s)." in out.getvalue()
