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


def authorize_guest_session(
    session: GuestWifiSession,
    request_id: str | None = None,
) -> OmadaResult:
    if not settings.OMADA_ENABLED:
        logger.info(
            "Omada authorization skipped request_id=%s session_id=%s.",
            request_id,
            session.pk,
        )
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
        logger.warning(
            "Omada authorization failed request_id=%s session_id=%s reason=%s.",
            request_id,
            session.pk,
            str(exc),
        )
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

    logger.info(
        "Omada authorization succeeded request_id=%s session_id=%s.",
        request_id,
        session.pk,
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
    # Omada's hotspot API expects the authorization duration in milliseconds.
    return settings.DEFAULT_AUTH_MINUTES * 60 * 1000


def get_success_redirect_url(omada_redirect_url: str | None = None) -> str:
    redirect_url = _normalize_redirect_url(omada_redirect_url)
    if _is_safe_absolute_redirect_url(redirect_url, _allowed_redirect_hosts()):
        return redirect_url

    success_url = _normalize_redirect_url(settings.SUCCESS_REDIRECT_URL)
    if _is_safe_success_redirect_url(success_url):
        return success_url

    return reverse("success")


def _allowed_redirect_hosts() -> set[str]:
    hosts = set(settings.ALLOWED_HOSTS) | set(settings.PORTAL_ALLOWED_REDIRECT_HOSTS)
    success_host = urlparse(
        _normalize_redirect_url(settings.SUCCESS_REDIRECT_URL)
    ).netloc
    if success_host:
        hosts.add(success_host)
    return hosts


def _normalize_redirect_url(url: str | None) -> str:
    if not url:
        return ""

    redirect_url = url.strip()
    if not redirect_url:
        return ""
    if redirect_url.startswith("//"):
        return f"https:{redirect_url}"
    if redirect_url.startswith("/"):
        return redirect_url

    parsed_url = urlparse(redirect_url)
    if parsed_url.scheme:
        return redirect_url
    if _looks_like_bare_hostname(redirect_url):
        return f"https://{redirect_url}"
    return redirect_url


def _looks_like_bare_hostname(url: str) -> bool:
    if any(character.isspace() for character in url):
        return False

    hostname = url.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
    return "." in hostname


def _is_safe_absolute_redirect_url(url: str, allowed_hosts: set[str]) -> bool:
    parsed_url = urlparse(url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        return False

    return url_has_allowed_host_and_scheme(
        url,
        allowed_hosts=allowed_hosts,
        require_https=False,
    )


def _is_safe_success_redirect_url(url: str) -> bool:
    parsed_url = urlparse(url)
    if parsed_url.scheme or parsed_url.netloc:
        return _is_safe_absolute_redirect_url(url, _allowed_redirect_hosts())

    return url_has_allowed_host_and_scheme(
        url,
        allowed_hosts=set(settings.ALLOWED_HOSTS),
        require_https=False,
    )


def _is_success_response(response_body: dict) -> bool:
    if not isinstance(response_body, dict):
        return False
    if "errorCode" in response_body:
        return response_body["errorCode"] == 0
    if "success" in response_body:
        return response_body["success"] is True
    return bool(response_body.get("result"))
