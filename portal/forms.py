from django import forms
from django.conf import settings
from django.utils import timezone

from .models import GuestWifiSession

OMADA_FIELD_MAP = {
    "clientMac": "client_mac",
    "apMac": "ap_mac",
    "gatewayMac": "gateway_mac",
    "vid": "vlan_id",
    "ssidName": "ssid_name",
    "radioId": "radio_id",
    "site": "site_name",
    "redirectUrl": "redirect_url",
    "t": "omada_timestamp",
}
OMADA_EXTRA_FIELDS = ("ssid", "originUrl")
OMADA_FORM_FIELDS = (*OMADA_FIELD_MAP, *OMADA_EXTRA_FIELDS)


def has_required_omada_session(data):
    client_mac = _field_value(data, "clientMac")
    site = _field_value(data, "site") or settings.OMADA_DEFAULT_SITE
    ssid_name = _field_value(data, "ssidName") or _field_value(data, "ssid")
    ap_params = _field_value(data, "apMac") and ssid_name and _field_value(
        data,
        "radioId",
    )
    gateway_params = _field_value(data, "gatewayMac") and _field_value(data, "vid")

    return bool(client_mac and site and (ap_params or gateway_params))


def _field_value(data, field):
    return (data.get(field) or "").strip()


class GuestWifiSessionForm(forms.Form):
    full_name = forms.CharField(
        label="Full name",
        max_length=255,
        widget=forms.TextInput(attrs={"autocomplete": "name"}),
    )
    email = forms.EmailField(
        label="Email address",
        max_length=254,
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    room_number = forms.CharField(
        label="Room number",
        max_length=64,
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )
    phone = forms.CharField(
        label="Phone number",
        max_length=64,
        required=False,
        widget=forms.TextInput(attrs={"autocomplete": "tel"}),
    )
    terms_accepted = forms.BooleanField(
        label="I accept the Wi-Fi terms of use",
        required=True,
        error_messages={"required": "You must accept the Wi-Fi terms to continue."},
    )
    marketing_consent = forms.BooleanField(
        label="I agree to receive optional hotel news and offers",
        required=False,
    )

    clientMac = forms.CharField(required=False, widget=forms.HiddenInput())
    apMac = forms.CharField(required=False, widget=forms.HiddenInput())
    gatewayMac = forms.CharField(required=False, widget=forms.HiddenInput())
    vid = forms.CharField(required=False, widget=forms.HiddenInput())
    ssidName = forms.CharField(required=False, widget=forms.HiddenInput())
    ssid = forms.CharField(required=False, widget=forms.HiddenInput())
    radioId = forms.CharField(required=False, widget=forms.HiddenInput())
    site = forms.CharField(required=False, widget=forms.HiddenInput())
    redirectUrl = forms.CharField(required=False, widget=forms.HiddenInput())
    originUrl = forms.CharField(required=False, widget=forms.HiddenInput())
    t = forms.CharField(required=False, widget=forms.HiddenInput())

    @property
    def omada_fields(self):
        return [self[field_name] for field_name in OMADA_FORM_FIELDS]

    def save(self, request):
        now = timezone.now()
        omada_values = {}
        for form_field, model_field in OMADA_FIELD_MAP.items():
            value = self.cleaned_data.get(form_field, "").strip()
            if form_field == "ssidName":
                value = value or self.cleaned_data.get("ssid", "").strip()
            if form_field == "redirectUrl":
                value = value or self.cleaned_data.get("originUrl", "").strip()
            if model_field == "client_mac":
                omada_values[model_field] = value
            else:
                omada_values[model_field] = value or None

        marketing_consent = self.cleaned_data["marketing_consent"]
        return GuestWifiSession.objects.create(
            full_name=self.cleaned_data["full_name"].strip(),
            email=self.cleaned_data["email"].strip(),
            phone=self.cleaned_data.get("phone", "").strip(),
            room_number=self.cleaned_data["room_number"].strip(),
            terms_accepted=True,
            terms_accepted_at=now,
            marketing_consent=marketing_consent,
            marketing_consent_at=now if marketing_consent else None,
            auth_duration_minutes=settings.DEFAULT_AUTH_MINUTES,
            ip_address=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            **omada_values,
        )


def get_client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.META.get("REMOTE_ADDR") or None
