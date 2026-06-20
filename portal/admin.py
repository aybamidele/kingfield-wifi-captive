import csv

from django.contrib import admin
from django.http import HttpResponse
from django.urls import path
from django.utils.dateparse import parse_date

from .models import GuestWifiSession
from .services import google_sheets

CSV_EXPORT_FIELDS = (
    "created_at",
    "full_name",
    "email",
    "phone",
    "room_number",
    "marketing_consent",
    "terms_accepted_at",
    "client_mac",
    "ssid_name",
    "auth_status",
    "authorized_at",
)


@admin.register(GuestWifiSession)
class GuestWifiSessionAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "full_name",
        "email",
        "room_number",
        "marketing_consent",
        "auth_status",
        "ssid_name",
        "client_mac",
    )
    list_filter = (
        "auth_status",
        "marketing_consent",
        "ssid_name",
        "created_at",
    )
    search_fields = (
        "full_name",
        "email",
        "room_number",
        "client_mac",
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
        "client_mac",
        "ap_mac",
        "gateway_mac",
        "vlan_id",
        "ssid_name",
        "radio_id",
        "site_name",
        "redirect_url",
        "omada_timestamp",
        "omada_response",
        "google_sheets_status",
        "google_sheets_sent_at",
        "google_sheets_response",
        "google_sheets_error",
    )
    actions = ("export_selected_sessions_csv", "retry_google_sheets")
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

    def get_urls(self):
        custom_urls = [
            path(
                "export/",
                self.admin_site.admin_view(self.export_csv_view),
                name="portal_guestwifisession_export",
            ),
        ]
        return custom_urls + super().get_urls()

    def export_csv_view(self, request):
        queryset = self._filtered_export_queryset(request.GET)
        return self._csv_response(queryset, "guest-wifi-sessions.csv")

    @admin.action(description="Export selected sessions as CSV")
    def export_selected_sessions_csv(self, request, queryset):
        return self._csv_response(queryset, "selected-guest-wifi-sessions.csv")

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

    def _filtered_export_queryset(self, params):
        queryset = GuestWifiSession.objects.all().order_by("created_at")
        start = parse_date(params.get("start", ""))
        end = parse_date(params.get("end", ""))
        if start:
            queryset = queryset.filter(created_at__date__gte=start)
        if end:
            queryset = queryset.filter(created_at__date__lte=end)
        if params.get("marketing_consent") in {"1", "true", "True", "yes"}:
            queryset = queryset.filter(marketing_consent=True)
        return queryset

    def _csv_response(self, queryset, filename):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        writer = csv.writer(response)
        writer.writerow(CSV_EXPORT_FIELDS)
        for session in queryset.order_by("created_at"):
            writer.writerow(
                [self._csv_value(session, field) for field in CSV_EXPORT_FIELDS]
            )
        return response

    def _csv_value(self, session, field):
        value = getattr(session, field)
        if value is None:
            return ""
        if field.endswith("_at") or field == "created_at":
            return value.isoformat()
        return value
