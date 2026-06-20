from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .forms import GuestWifiSessionForm, OMADA_FIELD_MAP
from .services.google_sheets import send_session_to_google_sheets
from .services.omada import authorize_guest_session, get_success_redirect_url


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
    form = GuestWifiSessionForm(request.POST)
    if form.is_valid():
        session = form.save(request)
        omada_result = authorize_guest_session(session)
        send_session_to_google_sheets(session)
        if settings.OMADA_ENABLED and not omada_result.success:
            return render(request, "portal/error.html", status=200)

        return redirect(get_success_redirect_url(session.redirect_url))

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
