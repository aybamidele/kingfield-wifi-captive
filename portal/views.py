import logging
import uuid

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .forms import GuestWifiSessionForm, OMADA_FIELD_MAP
from .services.google_sheets import send_session_to_google_sheets
from .services.omada import authorize_guest_session, get_success_redirect_url

logger = logging.getLogger(__name__)


@require_GET
def index(_request):
    return redirect("portal")


@require_http_methods(["GET"])
def portal_form(request):
    initial = {field: request.GET.get(field, "") for field in OMADA_FIELD_MAP}
    form = GuestWifiSessionForm(initial=initial)
    return render(request, "portal/portal.html", {"form": form})


@require_POST
def portal_submit(request):
    request_id = uuid.uuid4().hex
    if _is_rate_limited(request):
        logger.warning(
            "Portal submit rate limited request_id=%s ip=%s.",
            request_id,
            _client_ip(request),
        )
        return render(
            request,
            "portal/error.html",
            {"error_message": "Please wait a moment and try again."},
            status=429,
        )

    form = GuestWifiSessionForm(request.POST)
    if form.is_valid():
        session = form.save(request)
        logger.info(
            "Portal form accepted request_id=%s session_id=%s.",
            request_id,
            session.pk,
        )
        omada_result = authorize_guest_session(session, request_id=request_id)
        send_session_to_google_sheets(session)
        if settings.OMADA_ENABLED and not omada_result.success:
            logger.warning(
                "Portal authorization failed request_id=%s session_id=%s.",
                request_id,
                session.pk,
            )
            return render(request, "portal/error.html", status=200)

        return redirect(get_success_redirect_url(session.redirect_url))

    logger.info("Portal form invalid request_id=%s.", request_id)
    return render(request, "portal/portal.html", {"form": form}, status=200)


@require_GET
def success(request):
    return render(request, "portal/success.html")


@require_GET
def terms(request):
    return render(request, "portal/terms.html")


@require_GET
def privacy(request):
    return render(request, "portal/privacy.html")


@require_GET
def health(_request):
    return JsonResponse({"status": "ok"})


def _is_rate_limited(request):
    if not settings.PORTAL_RATE_LIMIT_ENABLED:
        return False

    cache_key = f"portal-submit:{_client_ip(request)}"
    attempts = cache.get(cache_key, 0) + 1
    cache.set(cache_key, attempts, settings.PORTAL_RATE_LIMIT_WINDOW_SECONDS)
    return attempts > settings.PORTAL_RATE_LIMIT_ATTEMPTS


def _client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")
