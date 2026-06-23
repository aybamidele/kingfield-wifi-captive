import csv
from datetime import timedelta
from io import StringIO

from django.contrib import admin
from django.core.management import call_command
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

import pytest

from portal.admin import GuestWifiSessionAdmin
from portal.models import GuestWifiSession, PortalCustomization


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
        "ssid_name": "Hotel_Guest",
        "auth_status": GuestWifiSession.AuthStatus.PENDING,
        "auth_duration_minutes": 1440,
    }
    defaults.update(overrides)
    return GuestWifiSession.objects.create(**defaults)


@pytest.mark.django_db
def test_admin_csv_export_view_filters_and_exports_selected_columns(admin_client):
    included = make_session(
        full_name="Marketing Guest",
        email="marketing@example.com",
        marketing_consent=True,
        auth_status=GuestWifiSession.AuthStatus.AUTHORIZED,
        authorized_at=timezone.now(),
    )
    excluded = make_session(
        full_name="No Marketing Guest",
        email="nomarketing@example.com",
        marketing_consent=False,
    )
    export_date = timezone.localtime(included.created_at).date().isoformat()

    response = admin_client.get(
        reverse("admin:portal_guestwifisession_export"),
        {
            "start": export_date,
            "end": export_date,
            "marketing_consent": "1",
        },
    )

    assert response.status_code == 200
    assert response["Content-Type"] == "text/csv"
    rows = list(csv.DictReader(StringIO(response.content.decode())))
    assert rows == [
        {
            "created_at": included.created_at.isoformat(),
            "full_name": "Marketing Guest",
            "email": "marketing@example.com",
            "phone": "+44 7000 000000",
            "room_number": "1204",
            "marketing_consent": "True",
            "terms_accepted_at": included.terms_accepted_at.isoformat(),
            "client_mac": "AA:BB:CC:DD:EE:FF",
            "ssid_name": "Hotel_Guest",
            "auth_status": "authorized",
            "authorized_at": included.authorized_at.isoformat(),
        }
    ]
    assert excluded.email not in response.content.decode()


@pytest.mark.django_db
def test_admin_export_selected_action_returns_csv():
    first = make_session(email="first@example.com")
    second = make_session(email="second@example.com")
    model_admin = GuestWifiSessionAdmin(GuestWifiSession, admin.site)
    request = RequestFactory().post("/admin/portal/guestwifisession/")

    response = model_admin.export_selected_sessions_csv(
        request,
        GuestWifiSession.objects.filter(id__in=[first.id, second.id]),
    )

    assert response.status_code == 200
    assert response["Content-Type"] == "text/csv"
    content = response.content.decode()
    assert "first@example.com" in content
    assert "second@example.com" in content


@pytest.mark.django_db
def test_purge_old_sessions_dry_run_keeps_records(settings):
    settings.DATA_RETENTION_DAYS = 365
    old_session = make_session(email="old@example.com")
    recent_session = make_session(email="recent@example.com")
    GuestWifiSession.objects.filter(id=old_session.id).update(
        created_at=timezone.now() - timedelta(days=400)
    )
    out = StringIO()

    call_command("purge_old_sessions", "--dry-run", stdout=out)

    assert GuestWifiSession.objects.filter(id=old_session.id).exists()
    assert GuestWifiSession.objects.filter(id=recent_session.id).exists()
    assert "1 session(s) would be deleted." in out.getvalue()


@pytest.mark.django_db
def test_purge_old_sessions_deletes_records_older_than_days():
    old_session = make_session(email="old@example.com")
    recent_session = make_session(email="recent@example.com")
    GuestWifiSession.objects.filter(id=old_session.id).update(
        created_at=timezone.now() - timedelta(days=10)
    )

    call_command("purge_old_sessions", "--days", "7")

    assert not GuestWifiSession.objects.filter(id=old_session.id).exists()
    assert GuestWifiSession.objects.filter(id=recent_session.id).exists()


@pytest.mark.django_db
def test_privacy_and_terms_pages_include_hotel_ready_content(client, settings):
    settings.PORTAL_BRAND_NAME = "Kingfield Hotel"
    settings.DATA_RETENTION_DAYS = 365

    privacy = client.get("/privacy/").content.decode()
    terms = client.get("/terms/").content.decode()

    assert "what data we collect" in privacy.lower()
    assert "365 days" in privacy
    assert "marketing consent is optional" in privacy.lower()
    assert "deletion" in privacy.lower()
    assert "acceptable use" in terms.lower()
    assert "illegal activity" in terms.lower()
    assert "guest devices remain your responsibility" in terms.lower()


@pytest.mark.django_db
def test_portal_uses_branding_context_and_hotel_copy(client, settings):
    settings.PORTAL_BRAND_NAME = "Kingfield Hotel"
    settings.PORTAL_TAGLINE = "Fast guest Wi-Fi"
    settings.PORTAL_PRIMARY_COLOR = "#123456"
    settings.PORTAL_SUPPORT_TEXT = "Need help? Contact reception."

    response = client.get(
        "/portal/",
        {
            "clientMac": "AA:BB:CC:DD:EE:01",
            "apMac": "11:22:33:44:55:66",
            "ssidName": "Kingfield Guest",
            "radioId": "1",
            "site": "site-id",
        },
    )
    content = response.content.decode()

    assert "Welcome to Kingfield Hotel Wi-Fi" in content
    assert "Fast guest Wi-Fi" in content
    assert "--color-primary: #123456" in content
    assert "Please complete the short form below to access the guest Wi-Fi." in content
    assert "I agree to the Wi-Fi terms of use." in content
    assert "I would like to receive offers and updates from Kingfield Hotel by email." in content
    assert "Connect to Wi-Fi" in content
    assert "Need help? Contact reception." in content


@pytest.mark.django_db
def test_success_page_uses_configured_message(client, settings):
    settings.PORTAL_SUCCESS_MESSAGE = "You are online. Enjoy your stay."

    response = client.get("/success/")

    assert "You are online. Enjoy your stay." in response.content.decode()


@pytest.mark.django_db
def test_admin_portal_customization_overrides_env_branding(client, settings):
    settings.PORTAL_BRAND_NAME = "Env Hotel"
    settings.PORTAL_TAGLINE = "Env Wi-Fi"
    settings.PORTAL_LOGO_URL = "/static/env-logo.svg"
    settings.PORTAL_BACKGROUND_URL = "/static/env-background.jpg"
    settings.PORTAL_PRIMARY_COLOR = "#111111"
    settings.PORTAL_SUPPORT_TEXT = "Env support."
    settings.PORTAL_SUCCESS_MESSAGE = "Env success."
    PortalCustomization.objects.create(
        brand_name="Admin Hotel",
        tagline="Admin Wi-Fi",
        logo_url="/static/admin-logo.svg",
        background_url="/static/admin-background.jpg",
        primary_color="#abcdef",
        support_text="Admin support.",
        success_message="Admin success.",
    )

    portal_response = client.get(
        "/portal/",
        {
            "clientMac": "AA:BB:CC:DD:EE:02",
            "apMac": "11:22:33:44:55:66",
            "ssidName": "Kingfield Guest",
            "radioId": "1",
            "site": "site-id",
        },
    )
    success_response = client.get("/success/")

    portal_content = portal_response.content.decode()
    assert "Welcome to Admin Hotel Wi-Fi" in portal_content
    assert "Admin Wi-Fi" in portal_content
    assert 'src="/static/admin-logo.svg"' in portal_content
    assert "--portal-bg-image: url('/static/admin-background.jpg')" in portal_content
    assert "--color-primary: #abcdef" in portal_content
    assert "Admin support." in portal_content
    assert "Env Hotel" not in portal_content
    assert "Admin success." in success_response.content.decode()


def test_production_settings_smoke(settings):
    assert settings.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")
    assert "whitenoise.middleware.WhiteNoiseMiddleware" in settings.MIDDLEWARE
    assert settings.STATIC_ROOT.name == "staticfiles"
    assert hasattr(settings, "CSRF_TRUSTED_ORIGINS")
    assert hasattr(settings, "ALLOWED_HOSTS")
