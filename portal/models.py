import uuid

from django.conf import settings
from django.db import models


def default_auth_duration_minutes():
    return settings.DEFAULT_AUTH_MINUTES


class GuestWifiSession(models.Model):
    class AuthStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        AUTHORIZED = "authorized", "Authorized"
        FAILED = "failed", "Failed"

    class GoogleSheetsStatus(models.TextChoices):
        NOT_CONFIGURED = "not_configured", "Not configured"
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=64, blank=True)
    room_number = models.CharField(max_length=64)

    terms_accepted = models.BooleanField(default=False)
    terms_accepted_at = models.DateTimeField()
    marketing_consent = models.BooleanField(default=False)
    marketing_consent_at = models.DateTimeField(null=True, blank=True)

    client_mac = models.CharField(max_length=64, blank=True)
    ap_mac = models.CharField(max_length=64, null=True, blank=True)
    gateway_mac = models.CharField(max_length=64, null=True, blank=True)
    vlan_id = models.CharField(max_length=32, null=True, blank=True)
    ssid_name = models.CharField(max_length=255, null=True, blank=True)
    radio_id = models.CharField(max_length=32, null=True, blank=True)
    site_name = models.CharField(max_length=255, null=True, blank=True)
    redirect_url = models.URLField(max_length=2048, null=True, blank=True)
    omada_timestamp = models.CharField(max_length=64, null=True, blank=True)

    auth_status = models.CharField(
        max_length=20,
        choices=AuthStatus.choices,
        default=AuthStatus.PENDING,
    )
    authorized_at = models.DateTimeField(null=True, blank=True)
    auth_duration_minutes = models.PositiveIntegerField(
        default=default_auth_duration_minutes
    )
    omada_response = models.JSONField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    google_sheets_status = models.CharField(
        max_length=20,
        choices=GoogleSheetsStatus.choices,
        default=GoogleSheetsStatus.NOT_CONFIGURED,
    )
    google_sheets_sent_at = models.DateTimeField(null=True, blank=True)
    google_sheets_response = models.JSONField(null=True, blank=True)
    google_sheets_error = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} ({self.room_number})"


def default_portal_brand_name():
    return settings.PORTAL_BRAND_NAME


def default_portal_tagline():
    return settings.PORTAL_TAGLINE


def default_portal_logo_url():
    return settings.PORTAL_LOGO_URL


def default_portal_background_url():
    return settings.PORTAL_BACKGROUND_URL


def default_portal_primary_color():
    return settings.PORTAL_PRIMARY_COLOR


def default_portal_support_text():
    return settings.PORTAL_SUPPORT_TEXT


def default_portal_success_message():
    return settings.PORTAL_SUCCESS_MESSAGE


class PortalCustomization(models.Model):
    singleton_key = models.PositiveSmallIntegerField(
        default=1,
        editable=False,
        unique=True,
    )
    brand_name = models.CharField(
        max_length=255,
        default=default_portal_brand_name,
    )
    tagline = models.CharField(
        max_length=255,
        default=default_portal_tagline,
    )
    logo_url = models.CharField(
        max_length=2048,
        blank=True,
        default=default_portal_logo_url,
        help_text="Optional local static path or absolute URL.",
    )
    background_url = models.CharField(
        max_length=2048,
        blank=True,
        default=default_portal_background_url,
        help_text="Optional local static path or absolute URL.",
    )
    primary_color = models.CharField(
        max_length=32,
        default=default_portal_primary_color,
        help_text="CSS colour used for primary buttons and brand accents.",
    )
    support_text = models.TextField(
        blank=True,
        default=default_portal_support_text,
    )
    success_message = models.TextField(
        default=default_portal_success_message,
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "portal customization"
        verbose_name_plural = "portal customization"

    def __str__(self):
        return self.brand_name

    def save(self, *args, **kwargs):
        self.singleton_key = 1
        return super().save(*args, **kwargs)
