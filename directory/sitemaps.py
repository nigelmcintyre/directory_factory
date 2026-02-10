from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.db.models import Count
from .models import Listing


class LandingPageSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        # Get all city/category combinations that have at least 2 listings
        pages = (
            Listing.objects.filter(is_active=True)
            .values("city", "category")
            .annotate(count=Count("id"))
            .filter(count__gte=2)
            .order_by("city", "category")
        )
        
        # Add homepage
        return [{"city": None, "category": None}] + list(pages)

    def location(self, item):
        if item["city"] is None:
            return reverse("home")
        return reverse(
            "pseo_landing",
            kwargs={
                "city": item["city"].lower(),
                "category": item["category"].lower(),
            },
        )
