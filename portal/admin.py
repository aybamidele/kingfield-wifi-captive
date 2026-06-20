from django.contrib import admin

from .models import GuestWifiSession


@admin.register(GuestWifiSession)
class GuestWifiSessionAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "full_name",
        "email",
        "room_number",
        "ssid_name",
        "auth_status",
        "terms_accepted",
        "marketing_consent",
    )
    list_filter = (
        "auth_status",
        "terms_accepted",
        "marketing_consent",
        "ssid_name",
        "site_name",
        "created_at",
    )
    search_fields = (
        "full_name",
        "email",
        "room_number",
        "client_mac",
        "ap_mac",
        "gateway_mac",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "terms_accepted_at",
        "marketing_consent_at",
        "authorized_at",
        "ip_address",
        "user_agent",
        "omada_response",
    )
    fieldsets = (
        (
            "Guest",
            {
                "fields": (
                    "id",
                    "full_name",
                    "email",
                    "phone",
                    "room_number",
                    "ip_address",
                    "user_agent",
                )
            },
        ),
        (
            "Consent",
            {
                "fields": (
                    "terms_accepted",
                    "terms_accepted_at",
                    "marketing_consent",
                    "marketing_consent_at",
                )
            },
        ),
        (
            "Omada",
            {
                "fields": (
                    "client_mac",
                    "ap_mac",
                    "gateway_mac",
                    "vlan_id",
                    "ssid_name",
                    "radio_id",
                    "site_name",
                    "redirect_url",
                    "omada_timestamp",
                )
            },
        ),
        (
            "Authorization",
            {
                "fields": (
                    "auth_status",
                    "authorized_at",
                    "auth_duration_minutes",
                    "omada_response",
                    "failure_reason",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
