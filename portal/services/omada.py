import logging
from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from portal.models import GuestWifiSession

logger = logging.getLogger(__name__)


class OmadaError(Exception):
    def __init__(self, message, response=None):
        super().__init__(message)
        self.response = response


@dataclass(frozen=True)
class OmadaResult:
    success: bool
    skipped: bool = False
    response: dict | None = None
    error: str = ""


class OmadaHotspotService:
    def __init__(self):
        self.session = requests.Session()
        self._configure_retries()
        self.csrf_token = None

    def login(self) -> str:
        response_body = self._post(
            "login",
            {
                "name": settings.OMADA_OPERATOR_USERNAME,
                "password": settings.OMADA_OPERATOR_PASSWORD,
            },
        )
        if not _is_success_response(response_body):
            logger.warning("Omada hotspot login failed.")
            raise OmadaError("Omada login failed", response=response_body)

        token = (response_body.get("result") or {}).get("token")
        if not token:
            logger.warning("Omada hotspot login response did not include CSRF token.")
            raise OmadaError("Omada login failed", response=response_body)

        self.csrf_token = token
        return token

    def authorize_session(self, session: GuestWifiSession) -> dict:
        token = self.login()
        response_body = self._post(
            "extPortal/auth",
            build_authorization_payload(session),
            headers={"Csrf-Token": token},
        )
        if not _is_success_response(response_body):
            logger.warning(
                "Omada hotspot authorization failed for session %s.",
                session.pk,
            )
            raise OmadaError("Omada authorization failed", response=response_body)

        return response_body

    def _post(self, endpoint: str, payload: dict, headers=None) -> dict:
        try:
            response = self.session.post(
                self._url(endpoint),
                json=payload,
                headers=headers,
                timeout=settings.OMADA_TIMEOUT_SECONDS,
                verify=settings.OMADA_VERIFY_SSL,
            )
            return response.json()
        except requests.Timeout as exc:
            logger.warning("Omada hotspot API request timed out.")
            raise OmadaError("Timeout") from exc
        except requests.RequestException as exc:
            logger.warning(
                "Omada hotspot API request failed: %s.",
                exc.__class__.__name__,
            )
            raise OmadaError(exc.__class__.__name__) from exc
        except ValueError as exc:
            logger.warning("Omada hotspot API returned non-JSON response.")
            raise OmadaError("Invalid JSON response") from exc

    def _url(self, endpoint: str) -> str:
        controller_url = settings.OMADA_CONTROLLER_URL.rstrip("/")
        controller_id = settings.OMADA_CONTROLLER_ID.strip("/")
        return f"{controller_url}/{controller_id}/api/v2/hotspot/{endpoint}"

    def _configure_retries(self):
        # Avoid retrying the POST authorization call after controller responses.
        # This adapter only allows urllib3's safe-method retry path.
        retry = Retry(
            total=1,
            connect=1,
            read=0,
            status=0,
            backoff_factor=0.2,
            allowed_methods=frozenset({"GET", "HEAD", "OPTIONS"}),
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)


def authorize_guest_session(session: GuestWifiSession) -> OmadaResult:
    if not settings.OMADA_ENABLED:
        session.auth_status = GuestWifiSession.AuthStatus.PENDING
        session.authorized_at = None
        session.failure_reason = ""
        session.save(
            update_fields=[
                "auth_status",
                "authorized_at",
                "failure_reason",
                "updated_at",
            ]
        )
        return OmadaResult(success=False, skipped=True)

    try:
        response = OmadaHotspotService().authorize_session(session)
    except OmadaError as exc:
        session.auth_status = GuestWifiSession.AuthStatus.FAILED
        session.authorized_at = None
        session.omada_response = exc.response
        session.failure_reason = str(exc)
        session.save(
            update_fields=[
                "auth_status",
                "authorized_at",
                "omada_response",
                "failure_reason",
                "updated_at",
            ]
        )
        return OmadaResult(
            success=False,
            response=exc.response,
            error=str(exc),
        )

    session.auth_status = GuestWifiSession.AuthStatus.AUTHORIZED
    session.authorized_at = timezone.now()
    session.omada_response = response
    session.failure_reason = ""
    session.save(
        update_fields=[
            "auth_status",
            "authorized_at",
            "omada_response",
            "failure_reason",
            "updated_at",
        ]
    )
    return OmadaResult(success=True, response=response)


def build_authorization_payload(session: GuestWifiSession) -> dict:
    common = {
        "clientMac": session.client_mac,
        "site": session.site_name or settings.OMADA_DEFAULT_SITE,
        "time": omada_authorization_time(),
        "authType": 4,
    }

    if session.ap_mac and session.ssid_name and session.radio_id:
        return {
            **common,
            "apMac": session.ap_mac,
            "ssidName": session.ssid_name,
            "radioId": session.radio_id,
        }

    if session.gateway_mac and session.vlan_id:
        return {
            **common,
            "gatewayMac": session.gateway_mac,
            "vid": session.vlan_id,
        }

    raise OmadaError("Missing Omada redirect parameters")


def omada_authorization_time() -> int:
    # Omada controller versions differ in how hotspot duration is documented.
    # The current payload keeps DEFAULT_AUTH_MINUTES as minutes, matching the
    # value captured by the app. Keep this isolated for adjustment after live
    # testing against the target controller firmware.
    return settings.DEFAULT_AUTH_MINUTES


def get_success_redirect_url(omada_redirect_url: str | None = None) -> str:
    if omada_redirect_url and url_has_allowed_host_and_scheme(
        omada_redirect_url,
        allowed_hosts=_allowed_redirect_hosts(),
        require_https=False,
    ):
        return omada_redirect_url

    return settings.SUCCESS_REDIRECT_URL or reverse("success")


def _allowed_redirect_hosts() -> set[str]:
    hosts = set(settings.ALLOWED_HOSTS)
    success_host = urlparse(settings.SUCCESS_REDIRECT_URL).netloc
    if success_host:
        hosts.add(success_host)
    return hosts


def _is_success_response(response_body: dict) -> bool:
    if not isinstance(response_body, dict):
        return False
    if "errorCode" in response_body:
        return response_body["errorCode"] == 0
    if "success" in response_body:
        return response_body["success"] is True
    return bool(response_body.get("result"))
