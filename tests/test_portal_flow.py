from django.contrib import admin
from django.urls import reverse
from django.utils import timezone

import pytest

from portal.models import GuestWifiSession


@pytest.mark.django_db
def test_root_redirects_to_portal(client):
    response = client.get("/")

    assert response.status_code == 302
    assert response["Location"] == "/portal/"


def test_health_returns_simple_status(client):
    response = client.get("/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize(
    "path",
    ["/portal/", "/success/", "/terms/", "/privacy/"],
)
def test_public_pages_render_without_external_assets(client, settings, path):
    settings.PORTAL_BRAND_NAME = "Kingfield Hotel"

    response = client.get(path)

    assert response.status_code == 200
    content = response.content.decode()
    assert "Kingfield Hotel" in content
    assert "https://fonts.googleapis.com" not in content
    assert "cdn." not in content


@pytest.mark.django_db
def test_portal_form_saves_guest_session_with_omada_parameters(client, settings):
    settings.DEFAULT_AUTH_MINUTES = 720
    before_submit = timezone.now()

    response = client.post(
        "/portal/submit/",
        data={
            "full_name": "Ada Lovelace",
            "email": "ada@example.com",
            "room_number": "1204",
            "phone": "+44 7000 000000",
            "terms_accepted": "on",
            "clientMac": "AA:BB:CC:DD:EE:FF",
            "apMac": "11:22:33:44:55:66",
            "gatewayMac": "22:33:44:55:66:77",
            "vid": "42",
            "ssidName": "Kingfield Guest",
            "radioId": "1",
            "site": "main-site",
            "redirectUrl": "https://example.com/welcome",
            "t": "1710000000",
        },
        REMOTE_ADDR="203.0.113.10",
        HTTP_USER_AGENT="pytest browser",
    )

    assert response.status_code == 302
    assert response["Location"] == "/success/"

    session = GuestWifiSession.objects.get()
    assert session.full_name == "Ada Lovelace"
    assert session.email == "ada@example.com"
    assert session.room_number == "1204"
    assert session.phone == "+44 7000 000000"
    assert session.terms_accepted is True
    assert session.terms_accepted_at >= before_submit
    assert session.marketing_consent is False
    assert session.marketing_consent_at is None
    assert session.client_mac == "AA:BB:CC:DD:EE:FF"
    assert session.ap_mac == "11:22:33:44:55:66"
    assert session.gateway_mac == "22:33:44:55:66:77"
    assert session.vlan_id == "42"
    assert session.ssid_name == "Kingfield Guest"
    assert session.radio_id == "1"
    assert session.site_name == "main-site"
    assert session.redirect_url == "https://example.com/welcome"
    assert session.omada_timestamp == "1710000000"
    assert session.auth_status == GuestWifiSession.AuthStatus.PENDING
    assert session.authorized_at is None
    assert session.auth_duration_minutes == 720
    assert session.omada_response is None
    assert session.failure_reason == ""
    assert session.ip_address == "203.0.113.10"
    assert session.user_agent == "pytest browser"


@pytest.mark.django_db
def test_marketing_consent_is_optional_but_timestamped_when_checked(client):
    response = client.post(
        "/portal/submit/",
        data={
            "full_name": "Grace Hopper",
            "email": "grace@example.com",
            "room_number": "803",
            "terms_accepted": "on",
            "marketing_consent": "on",
            "clientMac": "AA:BB:CC:DD:EE:01",
        },
    )

    assert response.status_code == 302
    session = GuestWifiSession.objects.get()
    assert session.marketing_consent is True
    assert session.marketing_consent_at is not None


@pytest.mark.django_db
def test_terms_acceptance_is_required_for_internet_access(client):
    response = client.post(
        "/portal/submit/",
        data={
            "full_name": "No Terms",
            "email": "noterms@example.com",
            "room_number": "101",
            "marketing_consent": "on",
            "clientMac": "AA:BB:CC:DD:EE:02",
        },
    )

    assert response.status_code == 200
    assert GuestWifiSession.objects.count() == 0
    assert "You must accept the Wi-Fi terms" in response.content.decode()


@pytest.mark.django_db
def test_missing_optional_omada_parameters_are_handled_gracefully(client):
    response = client.post(
        "/portal/submit/",
        data={
            "full_name": "Minimal Guest",
            "email": "minimal@example.com",
            "room_number": "12",
            "terms_accepted": "on",
            "clientMac": "AA:BB:CC:DD:EE:03",
        },
    )

    assert response.status_code == 302
    session = GuestWifiSession.objects.get()
    assert session.client_mac == "AA:BB:CC:DD:EE:03"
    assert session.ap_mac is None
    assert session.redirect_url is None


def test_portal_get_preserves_omada_parameters_as_hidden_fields(client):
    response = client.get(
        "/portal/",
        {
            "clientMac": "AA:BB:CC:DD:EE:04",
            "ssidName": "Kingfield Guest",
            "redirectUrl": "https://example.com/start",
        },
    )

    content = response.content.decode()
    assert 'name="clientMac" value="AA:BB:CC:DD:EE:04"' in content
    assert 'name="ssidName" value="Kingfield Guest"' in content
    assert 'name="redirectUrl" value="https://example.com/start"' in content


def test_guest_wifi_session_is_registered_in_admin():
    assert GuestWifiSession in admin.site._registry
