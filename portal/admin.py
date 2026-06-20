from django.contrib import admin

from .models import GuestWifiSession
from .services import google_sheets


@admin.register(GuestWifiSession)
class GuestWifiSessionAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "full_name",
        "email",
        "room_number",
        "ssid_name",
        "auth_status",
        "google_sheets_status",
        "google_sheets_sent_at",
        "terms_accepted",
        "marketing_consent",
    )
    list_filter = (
        "auth_status",
        "google_sheets_status",
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
        "google_sheets_status",
        "google_sheets_sent_at",
        "google_sheets_response",
        "google_sheets_error",
    )
    actions = ("retry_google_sheets",)
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
        (
            "Google Sheets",
            {
                "fields": (
                    "google_sheets_status",
                    "google_sheets_sent_at",
                    "google_sheets_response",
                    "google_sheets_error",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    @admin.action(description="Retry sending selected sessions to Google Sheets")
    def retry_google_sheets(self, request, queryset):
        outcomes = {"success": 0, "skipped": 0, "failed": 0, "unknown": 0}
        for session in queryset.order_by("created_at"):
            result = google_sheets.send_session_to_google_sheets(session)
            outcome = getattr(result, "outcome", "unknown")
            outcomes[outcome if outcome in outcomes else "unknown"] += 1

        self.message_user(
            request,
            (
                "Google Sheets retry complete: "
                f"{outcomes['success']} sent, "
                f"{outcomes['failed']} failed, "
                f"{outcomes['skipped']} skipped."
            ),
        )
