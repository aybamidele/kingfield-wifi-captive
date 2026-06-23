from django.conf import settings

from .models import PortalCustomization


def portal_branding(_request):
    customization = PortalCustomization.objects.first() or PortalCustomization()

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
