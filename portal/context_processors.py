from django.conf import settings

from .models import PortalCustomization


def portal_branding(_request):
    customization = PortalCustomization.objects.first()
    if customization:
        return {
            "portal_background_url": customization.background_url,
            "portal_brand_name": customization.brand_name,
            "portal_logo_url": customization.logo_url,
            "portal_primary_color": customization.primary_color,
            "portal_success_message": customization.success_message,
            "portal_support_text": customization.support_text,
            "portal_tagline": customization.tagline,
            "data_retention_days": settings.DATA_RETENTION_DAYS,
        }

    return {
        "portal_background_url": settings.PORTAL_BACKGROUND_URL,
        "portal_brand_name": settings.PORTAL_BRAND_NAME,
        "portal_logo_url": settings.PORTAL_LOGO_URL,
        "portal_primary_color": settings.PORTAL_PRIMARY_COLOR,
        "portal_success_message": settings.PORTAL_SUCCESS_MESSAGE,
        "portal_support_text": settings.PORTAL_SUPPORT_TEXT,
        "portal_tagline": settings.PORTAL_TAGLINE,
        "data_retention_days": settings.DATA_RETENTION_DAYS,
    }
