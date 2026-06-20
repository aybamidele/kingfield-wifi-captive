from django.conf import settings


def portal_branding(_request):
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
