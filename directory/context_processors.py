from django.conf import settings


def analytics_settings(request):
    return {
        "google_tag_id": getattr(settings, "GOOGLE_TAG_ID", ""),
        "google_ads_id": getattr(settings, "GOOGLE_ADS_ID", ""),
        "google_adsense_client": getattr(settings, "GOOGLE_ADSENSE_CLIENT", ""),
    }