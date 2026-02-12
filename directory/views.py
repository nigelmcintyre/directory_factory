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
    
    # Check if filters are applied for dynamic meta
    city = request.GET.get('city', '')
    county = request.GET.get('county', '')
    
    if city or county:
        location = city or county
        page_title = f"Saunas in {location.title()} | {SITE_NAME}"
        meta_description = f"Find the best saunas in {location.title()}, Ireland. Browse {listings.count()} listings with ratings, reviews, amenities, and contact details."
    else:
        page_title = f"{SITE_NAME} - Find the Best Saunas in Ireland"
        meta_description = f"Discover {listings.count()}+ saunas across Ireland. Filter by county, rating, and amenities to find your perfect sauna experience. Verified listings with photos, reviews, and contact info."
    
    context = {
        "site_name": SITE_NAME,
        "domain": DOMAIN,
        "filters": FILTERS,
        "listings": listings,
        "google_maps_api_key": settings.GOOGLE_MAPS_API_KEY,
        "page_title": page_title,
        "meta_description": meta_description,
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
    
    # Get related listings (same city or county, excluding current)
    related_listings = (
        Listing.objects
        .filter(is_active=True)
        .exclude(id=listing.id)
        .filter(city=listing.city)[:4]
    )
    
    # If not enough in same city, try county
    if related_listings.count() < 4 and listing.county:
        additional = (
            Listing.objects
            .filter(is_active=True, county=listing.county)
            .exclude(id=listing.id)
            .exclude(id__in=[l.id for l in related_listings])[:4 - related_listings.count()]
        )
        related_listings = list(related_listings) + list(additional)
    
    # Enhanced SEO title with location and rating
    title_parts = [listing.name]
    if listing.city:
        title_parts.append(f"in {listing.city}")
    if listing.county:
        title_parts.append(listing.county)
    if listing.rating:
        title_parts.append(f"★{listing.rating}")
    page_title = " ".join(title_parts) + f" | {SITE_NAME}"
    
    # Enhanced meta description with key details
    if listing.description:
        meta_description = listing.description[:155] + "..." if len(listing.description) > 155 else listing.description
    else:
        desc_parts = [f"Visit {listing.name}"]
        if listing.city:
            desc_parts.append(f"in {listing.city}")
        if listing.rating:
            desc_parts.append(f"- Rated {listing.rating}★")
        if listing.category:
            desc_parts.append(f"- {listing.category}")
        desc_parts.append("View amenities, contact info, and location details.")
        meta_description = " ".join(desc_parts)
    
    # Generate keywords from listing attributes
    meta_keywords = [
        f"{listing.name}",
        f"sauna {listing.city}",
        listing.city,
        listing.category,
    ]
    if listing.county:
        meta_keywords.append(f"sauna {listing.county}")
    
    context = {
        "site_name": SITE_NAME,
        "domain": DOMAIN,
        "filters": FILTERS,
        "listing": listing,
        "related_listings": related_listings,
        "google_maps_api_key": settings.GOOGLE_MAPS_API_KEY,
        "page_title": page_title,
        "meta_description": meta_description,
        "meta_keywords": ", ".join(meta_keywords),
    }

    return render(request, "listing_detail.html", context)
