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
