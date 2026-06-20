from django.conf import settings


def portal_branding(_request):
    return {
        "portal_background_url": settings.PORTAL_BACKGROUND_URL,
        "portal_brand_name": settings.PORTAL_BRAND_NAME,
        "portal_logo_url": settings.PORTAL_LOGO_URL,
    }
