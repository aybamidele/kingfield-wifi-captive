import logging
from dataclasses import dataclass

import requests
from django.conf import settings
from django.utils import timezone

from portal.models import GuestWifiSession

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GoogleSheetsResult:
    outcome: str
    response: dict | None = None
    error: str = ""


def send_session_to_google_sheets(session: GuestWifiSession) -> GoogleSheetsResult:
    if not settings.GOOGLE_SHEETS_ENABLED:
        result = GoogleSheetsResult(outcome="skipped")
        _apply_result(session, result)
        return result

    webhook_url = settings.GOOGLE_SHEETS_WEBHOOK_URL
    if not webhook_url:
        result = GoogleSheetsResult(
            outcome="failed",
            error="Webhook URL not configured",
        )
        _log_failure(session, result.error)
        _apply_result(session, result)
        return result

    _mark_pending(session)
    try:
        response = requests.post(
            webhook_url,
            json=build_payload(session),
            timeout=settings.GOOGLE_SHEETS_TIMEOUT_SECONDS,
        )
    except requests.Timeout:
        result = GoogleSheetsResult(outcome="failed", error="Timeout")
        _log_failure(session, result.error)
        _apply_result(session, result)
        return result
    except requests.RequestException as exc:
        result = GoogleSheetsResult(outcome="failed", error=exc.__class__.__name__)
        _log_failure(session, result.error)
        _apply_result(session, result)
        return result
    except Exception as exc:
        result = GoogleSheetsResult(outcome="failed", error=exc.__class__.__name__)
        _log_failure(session, result.error)
        _apply_result(session, result)
        return result

    response_body = _safe_response_body(response)
    response_data = {
        "status_code": response.status_code,
        "body": response_body,
    }
    if 200 <= response.status_code < 300:
        result = GoogleSheetsResult(outcome="success", response=response_data)
    else:
        result = GoogleSheetsResult(
            outcome="failed",
            response=response_data,
            error=f"HTTP {response.status_code}",
        )
        _log_failure(session, result.error)

    _apply_result(session, result)
    return result


def build_payload(session: GuestWifiSession) -> dict:
    return {
        "secret": settings.GOOGLE_SHEETS_WEBHOOK_SECRET,
        "session_id": str(session.id),
        "created_at": _datetime_value(session.created_at),
        "full_name": session.full_name,
        "email": session.email,
        "phone": session.phone,
        "room_number": session.room_number,
        "terms_accepted": session.terms_accepted,
        "terms_accepted_at": _datetime_value(session.terms_accepted_at),
        "marketing_consent": session.marketing_consent,
        "marketing_consent_at": _datetime_value(session.marketing_consent_at),
        "client_mac": session.client_mac,
        "ap_mac": session.ap_mac,
        "gateway_mac": session.gateway_mac,
        "vlan_id": session.vlan_id,
        "ssid_name": session.ssid_name,
        "radio_id": session.radio_id,
        "site_name": session.site_name,
        "redirect_url": session.redirect_url,
        "auth_status": session.auth_status,
        "ip_address": session.ip_address,
        "user_agent": session.user_agent,
    }


def _datetime_value(value):
    if value is None:
        return None
    return value.isoformat()


def _mark_pending(session: GuestWifiSession):
    session.google_sheets_status = GuestWifiSession.GoogleSheetsStatus.PENDING
    session.google_sheets_sent_at = None
    session.google_sheets_response = None
    session.google_sheets_error = ""
    session.save(
        update_fields=[
            "google_sheets_status",
            "google_sheets_sent_at",
            "google_sheets_response",
            "google_sheets_error",
            "updated_at",
        ]
    )


def _apply_result(session: GuestWifiSession, result: GoogleSheetsResult):
    if result.outcome == "success":
        session.google_sheets_status = GuestWifiSession.GoogleSheetsStatus.SENT
        session.google_sheets_sent_at = timezone.now()
        session.google_sheets_response = result.response
        session.google_sheets_error = ""
    elif result.outcome == "skipped":
        session.google_sheets_status = (
            GuestWifiSession.GoogleSheetsStatus.NOT_CONFIGURED
        )
        session.google_sheets_sent_at = None
        session.google_sheets_response = result.response
        session.google_sheets_error = ""
    else:
        session.google_sheets_status = GuestWifiSession.GoogleSheetsStatus.FAILED
        session.google_sheets_sent_at = None
        session.google_sheets_response = result.response
        session.google_sheets_error = result.error

    session.save(
        update_fields=[
            "google_sheets_status",
            "google_sheets_sent_at",
            "google_sheets_response",
            "google_sheets_error",
            "updated_at",
        ]
    )


def _safe_response_body(response):
    try:
        return response.json()
    except ValueError:
        return None


def _log_failure(session: GuestWifiSession, reason: str):
    logger.warning(
        "Google Sheets webhook post failed for session %s (%s).",
        session.pk,
        reason,
    )
