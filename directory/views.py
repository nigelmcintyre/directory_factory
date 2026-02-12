import json
from django.conf import settings
from django.shortcuts import get_object_or_404, render
from django.http import HttpRequest, HttpResponse
from django.utils.safestring import mark_safe
from .models import Listing
from .niche_config import SITE_NAME, DOMAIN, FILTERS
from .utils import get_filtered_listings
from .schema import generate_breadcrumb_schema, generate_listing_schema


def _is_htmx(request: HttpRequest) -> bool:
    return request.headers.get("HX-Request", "false").lower() == "true"


def robots_txt(request: HttpRequest) -> HttpResponse:
    lines = [
        "User-agent: *",
        "Allow: /",
        f"Sitemap: https://{DOMAIN}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def home(request: HttpRequest) -> HttpResponse:
    listings = get_filtered_listings(request)
    context = {
        "site_name": SITE_NAME,
        "domain": DOMAIN,
        "filters": FILTERS,
        "listings": listings,
        "google_maps_api_key": settings.GOOGLE_MAPS_API_KEY,
        "page_title": SITE_NAME,
        "meta_description": "Find the best saunas in Ireland with Sauna Guide. Filter by county, rating, and amenities.",
    }

    if _is_htmx(request):
        return render(request, "partials/listing_results.html", context)

    return render(request, "home.html", context)


def pseo_landing(request: HttpRequest, city: str, category: str) -> HttpResponse:
    listings = get_filtered_listings(request).filter(
        city__iexact=city,
        category__iexact=category,
    )

    page_title = f"{category.title()} in {city.title()} | {SITE_NAME}"
    meta_description = (
        f"Sauna Guide lists {listings.count()} {category.lower()} options in {city.title()}. "
        "Compare amenities, ratings, and locations to find the best fit."
    )
    
    # Generate Schema.org structured data
    breadcrumb_schema = generate_breadcrumb_schema(city, category, SITE_NAME)
    listing_schemas = [generate_listing_schema(listing) for listing in listings[:5]]  # Top 5 listings
    
    context = {
        "site_name": SITE_NAME,
        "domain": DOMAIN,
        "filters": FILTERS,
        "listings": listings,
        "google_maps_api_key": settings.GOOGLE_MAPS_API_KEY,
        "page_title": page_title,
        "meta_description": meta_description,
        "city": city,
        "category": category,
        "schema_breadcrumb": mark_safe(json.dumps(breadcrumb_schema)),
        "schema_listings": mark_safe(json.dumps(listing_schemas)),
    }

    if _is_htmx(request):
        return render(request, "partials/listing_results.html", context)

    return render(request, "pseo_landing.html", context)


def listing_detail(request: HttpRequest, slug: str) -> HttpResponse:
    listing = get_object_or_404(Listing, slug=slug, is_active=True)
    page_title = f"{listing.name} | {SITE_NAME}"
    meta_description = (
        listing.description
        or f"Sauna Guide listing for {listing.name} in {listing.city}. View details, amenities, and contact info."
    )

    context = {
        "site_name": SITE_NAME,
        "domain": DOMAIN,
        "filters": FILTERS,
        "listing": listing,
        "google_maps_api_key": settings.GOOGLE_MAPS_API_KEY,
        "page_title": page_title,
        "meta_description": meta_description,
    }

    return render(request, "listing_detail.html", context)
