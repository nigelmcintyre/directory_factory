from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.db.models import Count
from django.utils.text import slugify
from .models import Listing


class LandingPageSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        # Get all counties that have at least 2 listings
        pages = (
            Listing.objects.filter(is_active=True)
            .exclude(county="")
            .values("county")
            .annotate(count=Count("id"))
            .filter(count__gte=2)
            .order_by("county")
        )
        
        # Add homepage
        return [{"county": None}] + list(pages)

    def location(self, item):
        if item["county"] is None:
            return reverse("home")
        return reverse(
            "pseo_landing",
            kwargs={
                "county": slugify(item["county"]),
            },
        )


class ListingSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Listing.objects.filter(is_active=True).order_by("-updated_at")

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse("listing_detail", kwargs={"slug": obj.slug})
