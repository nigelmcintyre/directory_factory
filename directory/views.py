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


def home(request: HttpRequest) -> HttpResponse:
    listings = get_filtered_listings(request)
    context = {
        "site_name": SITE_NAME,
        "domain": DOMAIN,
        "filters": FILTERS,
        "listings": listings,
        "google_maps_api_key": settings.GOOGLE_MAPS_API_KEY,
        "page_title": SITE_NAME,
        "meta_description": f"Discover the best {SITE_NAME.lower()} options. Filter by your preferences and find exactly what you're looking for.",
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
    meta_description = f"Find the best {category.lower()} options in {city.title()}. Browse {listings.count()} verified listings with detailed filters and information."
    
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
    meta_description = listing.description or f"Details for {listing.name} in {listing.city}."

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
