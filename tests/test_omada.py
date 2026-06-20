from django.utils import timezone

import pytest
import requests

from portal.models import GuestWifiSession
from portal.services.omada import (
    OmadaError,
    OmadaHotspotService,
    authorize_guest_session,
    build_authorization_payload,
    get_success_redirect_url,
)


def make_session(**overrides):
    defaults = {
        "full_name": "Ada Lovelace",
        "email": "ada@example.com",
        "room_number": "1204",
        "terms_accepted": True,
        "terms_accepted_at": timezone.now(),
        "client_mac": "AA:BB:CC:DD:EE:FF",
        "auth_duration_minutes": 1440,
    }
    defaults.update(overrides)
    return GuestWifiSession.objects.create(**defaults)


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload


class FakeRequestsSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.mounted = []

    def mount(self, prefix, adapter):
        self.mounted.append((prefix, adapter))

    def post(self, url, json, headers=None, timeout=None, verify=None):
        self.calls.append(
            {
                "url": url,
                "json": json,
                "headers": headers or {},
                "timeout": timeout,
                "verify": verify,
            }
        )
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


@pytest.fixture
def omada_settings(settings):
    settings.OMADA_ENABLED = True
    settings.OMADA_CONTROLLER_URL = "https://omada.example.test/"
    settings.OMADA_CONTROLLER_ID = "controller-id"
    settings.OMADA_OPERATOR_USERNAME = "hotspot-operator"
    settings.OMADA_OPERATOR_PASSWORD = "operator-password"
    settings.OMADA_VERIFY_SSL = False
    settings.OMADA_DEFAULT_SITE = "default-site"
    settings.OMADA_TIMEOUT_SECONDS = 3
    settings.DEFAULT_AUTH_MINUTES = 90
    return settings


def test_omada_login_success(monkeypatch, omada_settings):
    fake_session = FakeRequestsSession(
        [FakeResponse({"errorCode": 0, "result": {"token": "csrf-token"}})]
    )
    monkeypatch.setattr(
        "portal.services.omada.requests.Session",
        lambda: fake_session,
    )

    service = OmadaHotspotService()
    token = service.login()

    assert token == "csrf-token"
    assert fake_session.calls == [
        {
            "url": "https://omada.example.test/controller-id/api/v2/hotspot/login",
            "json": {"name": "hotspot-operator", "password": "operator-password"},
            "headers": {},
            "timeout": 3,
            "verify": False,
        }
    ]


def test_omada_login_failure_does_not_log_password(
    caplog,
    monkeypatch,
    omada_settings,
):
    fake_session = FakeRequestsSession(
        [FakeResponse({"errorCode": 1, "msg": "invalid credentials"})]
    )
    monkeypatch.setattr(
        "portal.services.omada.requests.Session",
        lambda: fake_session,
    )

    service = OmadaHotspotService()

    with pytest.raises(OmadaError, match="Omada login failed"):
        service.login()

    assert "operator-password" not in caplog.text


@pytest.mark.django_db
def test_eap_payload_construction(omada_settings):
    session = make_session(
        ap_mac="11:22:33:44:55:66",
        ssid_name="Kingfield Guest",
        radio_id="1",
        site_name="main-site",
    )

    payload = build_authorization_payload(session)

    assert payload == {
        "clientMac": "AA:BB:CC:DD:EE:FF",
        "apMac": "11:22:33:44:55:66",
        "ssidName": "Kingfield Guest",
        "radioId": "1",
        "site": "main-site",
        "time": 90,
        "authType": 4,
    }


@pytest.mark.django_db
def test_gateway_payload_construction(omada_settings):
    session = make_session(
        gateway_mac="22:33:44:55:66:77",
        vlan_id="42",
    )

    payload = build_authorization_payload(session)

    assert payload == {
        "clientMac": "AA:BB:CC:DD:EE:FF",
        "gatewayMac": "22:33:44:55:66:77",
        "vid": "42",
        "site": "default-site",
        "time": 90,
        "authType": 4,
    }


@pytest.mark.django_db
def test_successful_authorization_updates_session(monkeypatch, omada_settings):
    session = make_session(
        ap_mac="11:22:33:44:55:66",
        ssid_name="Kingfield Guest",
        radio_id="1",
    )
    fake_session = FakeRequestsSession(
        [
            FakeResponse({"errorCode": 0, "result": {"token": "csrf-token"}}),
            FakeResponse({"errorCode": 0, "result": {"authorized": True}}),
        ]
    )
    monkeypatch.setattr(
        "portal.services.omada.requests.Session",
        lambda: fake_session,
    )

    result = authorize_guest_session(session)

    session.refresh_from_db()
    assert result.success is True
    assert session.auth_status == GuestWifiSession.AuthStatus.AUTHORIZED
    assert session.authorized_at is not None
    assert session.omada_response == {"errorCode": 0, "result": {"authorized": True}}
    assert session.failure_reason == ""
    assert fake_session.calls[1]["url"] == (
        "https://omada.example.test/controller-id/api/v2/hotspot/extPortal/auth"
    )
    assert fake_session.calls[1]["headers"] == {"Csrf-Token": "csrf-token"}


@pytest.mark.django_db
def test_failed_authorization_updates_session(monkeypatch, omada_settings):
    session = make_session(
        gateway_mac="22:33:44:55:66:77",
        vlan_id="42",
    )
    fake_session = FakeRequestsSession(
        [
            FakeResponse({"errorCode": 0, "result": {"token": "csrf-token"}}),
            FakeResponse({"errorCode": 101, "msg": "client not found"}),
        ]
    )
    monkeypatch.setattr(
        "portal.services.omada.requests.Session",
        lambda: fake_session,
    )

    result = authorize_guest_session(session)

    session.refresh_from_db()
    assert result.success is False
    assert session.auth_status == GuestWifiSession.AuthStatus.FAILED
    assert session.authorized_at is None
    assert session.omada_response == {"errorCode": 101, "msg": "client not found"}
    assert session.failure_reason == "Omada authorization failed"


@pytest.mark.django_db
def test_form_submit_with_omada_disabled_keeps_session_pending(client, settings):
    settings.OMADA_ENABLED = False

    response = client.post(
        "/portal/submit/",
        data={
            "full_name": "Local Guest",
            "email": "local@example.com",
            "room_number": "101",
            "terms_accepted": "on",
            "clientMac": "AA:BB:CC:DD:EE:01",
        },
    )

    assert response.status_code == 302
    assert response["Location"] == "/success/"
    session = GuestWifiSession.objects.get()
    assert session.auth_status == GuestWifiSession.AuthStatus.PENDING
    assert session.failure_reason == ""


@pytest.mark.django_db
def test_form_submit_with_successful_omada_uses_safe_redirect(
    client,
    monkeypatch,
    settings,
):
    settings.OMADA_ENABLED = True
    settings.ALLOWED_HOSTS = ["testserver", "guest.example.com"]

    def fake_authorize(session):
        session.auth_status = GuestWifiSession.AuthStatus.AUTHORIZED
        session.authorized_at = timezone.now()
        session.save(update_fields=["auth_status", "authorized_at", "updated_at"])
        return type("Result", (), {"success": True, "skipped": False})()

    monkeypatch.setattr("portal.views.authorize_guest_session", fake_authorize)

    response = client.post(
        "/portal/submit/",
        data={
            "full_name": "Redirect Guest",
            "email": "redirect@example.com",
            "room_number": "202",
            "terms_accepted": "on",
            "clientMac": "AA:BB:CC:DD:EE:02",
            "apMac": "11:22:33:44:55:66",
            "ssidName": "Kingfield Guest",
            "radioId": "1",
            "redirectUrl": "https://guest.example.com/welcome",
        },
    )

    assert response.status_code == 302
    assert response["Location"] == "https://guest.example.com/welcome"


@pytest.mark.django_db
def test_form_submit_with_failed_omada_shows_friendly_error(
    client,
    monkeypatch,
    settings,
):
    settings.OMADA_ENABLED = True

    def fake_authorize(session):
        session.auth_status = GuestWifiSession.AuthStatus.FAILED
        session.failure_reason = "secret controller detail"
        session.save(update_fields=["auth_status", "failure_reason", "updated_at"])
        return type("Result", (), {"success": False, "skipped": False})()

    monkeypatch.setattr("portal.views.authorize_guest_session", fake_authorize)

    response = client.post(
        "/portal/submit/",
        data={
            "full_name": "Failed Guest",
            "email": "failed@example.com",
            "room_number": "303",
            "terms_accepted": "on",
            "clientMac": "AA:BB:CC:DD:EE:03",
            "apMac": "11:22:33:44:55:66",
            "ssidName": "Kingfield Guest",
            "radioId": "1",
        },
    )

    content = response.content.decode()
    assert response.status_code == 200
    assert "Connection issue" in content
    assert "secret controller detail" not in content


def test_unsafe_redirect_url_falls_back(settings):
    settings.ALLOWED_HOSTS = ["portal.example.com"]
    settings.SUCCESS_REDIRECT_URL = "/success/"

    assert (
        get_success_redirect_url("https://evil.example.com/phish")
        == "/success/"
    )
