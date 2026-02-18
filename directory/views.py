import json
from urllib.parse import urlencode
from django.utils.text import slugify
from django.conf import settings
from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpRequest, HttpResponse
from django.utils.safestring import mark_safe
from django.contrib import messages
from .models import Listing
from .forms import SaunaSubmissionForm
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
    listings, near_me_context = get_filtered_listings(request)
    listings_count = len(listings) if isinstance(listings, list) else listings.count()
    
    # Check if filters are applied for dynamic meta (prefer county)
    county = request.GET.get('county', '')
    city = request.GET.get('city', '')
    
    if county or city:
        location = county or city
        page_title = f"Saunas in {location.title()} | {SITE_NAME}"
        meta_description = f"Find the best saunas in {location.title()}, Ireland. Browse {listings_count} listings with ratings, reviews, amenities, and contact details."
    else:
        page_title = f"{SITE_NAME} - Find the Best Saunas in Ireland"
        meta_description = f"Discover {listings_count}+ saunas across Ireland. Filter by county, rating, and amenities to find your perfect sauna experience. Verified listings with photos, reviews, and contact info."

    map_listings = []
    for listing in listings:
        if listing.latitude is None or listing.longitude is None:
            continue
        map_listings.append(
            {
                "name": listing.name,
                "lat": listing.latitude,
                "lng": listing.longitude,
                "location": listing.county or listing.city,
                "address": listing.address,
                "url": f"/listing/{listing.slug}/",
                "distance_km": getattr(listing, "distance_km", None),
            }
        )
    
    context = {
        "site_name": SITE_NAME,
        "domain": DOMAIN,
        "filters": FILTERS,
        "listings": listings,
        "listings_count": listings_count,
        "google_maps_api_key": settings.GOOGLE_MAPS_API_KEY,
        "map_provider": getattr(settings, "MAP_PROVIDER", "leaflet"),
        "map_tiles_url": getattr(
            settings,
            "MAP_TILES_URL",
            "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        ),
        "map_tiles_attribution": getattr(
            settings,
            "MAP_TILES_ATTRIBUTION",
            "&copy; OpenStreetMap contributors",
        ),
        "map_center_lat": getattr(settings, "MAP_DEFAULT_CENTER_LAT", 53.1424),
        "map_center_lng": getattr(settings, "MAP_DEFAULT_CENTER_LNG", -7.6921),
        "map_default_zoom": getattr(settings, "MAP_DEFAULT_ZOOM", 7),
        "map_listings_json": mark_safe(json.dumps(map_listings)),
        "map_enabled": True,
        "page_title": page_title,
        "meta_description": meta_description,
        "near_me_active": near_me_context.get("near_me"),
        "near_me_distance_km": near_me_context.get("distance_km", 50),
        "user_lat": near_me_context.get("user_lat"),
        "user_lng": near_me_context.get("user_lng"),
    }

    if _is_htmx(request):
        return render(request, "partials/listing_results.html", context)

    return render(request, "home.html", context)


def pseo_landing(request: HttpRequest, county: str) -> HttpResponse:
    county_slug = county
    county_display = county.replace("-", " ").title()
    selected_county = request.GET.get("county", "").strip()
    if selected_county and slugify(selected_county) != county_slug:
        redirect_params = request.GET.copy()
        redirect_params.pop("county", None)
        query_pairs = [(key, value) for key, values in redirect_params.lists() for value in values if value]
        query_string = urlencode(query_pairs, doseq=True)
        path = f"/{slugify(selected_county)}/"
        if query_string:
            path = f"{path}?{query_string}"
        return redirect(path)

    query_params = request.GET.copy()
    query_params["county"] = county_display
    request.GET = query_params
    listings, near_me_context = get_filtered_listings(request)
    if isinstance(listings, list):
        listings = [
            listing
            for listing in listings
            if listing.county and slugify(listing.county) == county_slug
        ]
        listings_count = len(listings)
    else:
        listings = (
            listings.filter(county__iexact=county_display)
            | listings.filter(county__in=[county.replace("-", " ")])
        ).distinct().order_by("-is_featured", "name")
        if listings.exists():
            county_display = listings.first().county or county_display
        listings_count = listings.count()

    page_title = f"Saunas in {county_display} | {SITE_NAME}"
    meta_description = (
        f"Sauna Guide lists {listings_count} sauna options in {county_display}. "
        "Compare amenities, ratings, and locations to find the best fit."
    )
    
    # Generate Schema.org structured data
    breadcrumb_schema = generate_breadcrumb_schema(county_display, SITE_NAME, county_slug)
    listing_schemas = [generate_listing_schema(listing) for listing in listings[:5]]  # Top 5 listings
    
    context = {
        "site_name": SITE_NAME,
        "domain": DOMAIN,
        "filters": FILTERS,
        "listings": listings,
        "listings_count": listings_count,
        "google_maps_api_key": settings.GOOGLE_MAPS_API_KEY,
        "page_title": page_title,
        "meta_description": meta_description,
        "county": county_display,
        "county_slug": county_slug,
        "schema_breadcrumb": mark_safe(json.dumps(breadcrumb_schema)),
        "schema_listings": mark_safe(json.dumps(listing_schemas)),
        "map_enabled": False,
    }

    if _is_htmx(request):
        return render(request, "partials/listing_results.html", context)

    return render(request, "pseo_landing.html", context)


def listing_detail(request: HttpRequest, slug: str) -> HttpResponse:
    listing = get_object_or_404(Listing, slug=slug, is_active=True)
    county_slug = slugify(listing.county) if listing.county else ""
    
    # Get Google reviews from structured_data
    google_reviews = listing.structured_data.get('google_reviews', []) if listing.structured_data else []
    
    # Get related listings (prefer same county, fallback to city)
    if listing.county:
        related_queryset = (
            Listing.objects
            .filter(is_active=True, county=listing.county)
            .exclude(id=listing.id)
        )
    else:
        related_queryset = (
            Listing.objects
            .filter(is_active=True, city=listing.city)
            .exclude(id=listing.id)
        )
    related_listings = list(related_queryset[:4])

    # If not enough in county, try city as a fallback
    if len(related_listings) < 4 and listing.city:
        additional = (
            Listing.objects
            .filter(is_active=True, city=listing.city)
            .exclude(id=listing.id)
            .exclude(id__in=[l.id for l in related_listings])[:4 - len(related_listings)]
        )
        related_listings = related_listings + list(additional)
    
    # Enhanced SEO title with location and rating
    title_parts = [listing.name]
    if listing.county:
        title_parts.append(f"in {listing.county}")
    if listing.city:
        title_parts.append(listing.city)
    if listing.rating:
        title_parts.append(f"★{listing.rating}")
    page_title = " ".join(title_parts) + f" | {SITE_NAME}"
    
    # Enhanced meta description with key details
    if listing.description:
        meta_description = listing.description[:155] + "..." if len(listing.description) > 155 else listing.description
    else:
        desc_parts = [f"Visit {listing.name}"]
        if listing.county:
            desc_parts.append(f"in {listing.county}")
        elif listing.city:
            desc_parts.append(f"in {listing.city}")
        if listing.rating:
            desc_parts.append(f"- Rated {listing.rating}★")

        desc_parts.append("View amenities, contact info, and location details.")
        meta_description = " ".join(desc_parts)
    
    # Generate keywords from listing attributes
    meta_keywords = [
        f"{listing.name}",
        f"sauna {listing.county}" if listing.county else f"sauna {listing.city}",
        listing.county or listing.city,
    ]
    if listing.city and listing.county:
        meta_keywords.append(f"sauna {listing.city}")
    
    context = {
        "site_name": SITE_NAME,
        "domain": DOMAIN,
        "filters": FILTERS,
        "listing": listing,
        "related_listings": related_listings,
        "google_reviews": google_reviews,
        "google_maps_api_key": settings.GOOGLE_MAPS_API_KEY,
        "page_title": page_title,
        "meta_description": meta_description,
        "meta_keywords": ", ".join(meta_keywords),
        "county_slug": county_slug,
    }

    return render(request, "listing_detail.html", context)


def submit_sauna(request: HttpRequest) -> HttpResponse:
    """Handle sauna submission form"""
    if request.method == 'POST':
        form = SaunaSubmissionForm(request.POST)
        if form.is_valid():
            submission = form.save()
            messages.success(
                request,
                "Thank you! Your sauna submission has been received and will be reviewed shortly."
            )
            return redirect('submit_success')
    else:
        # Allow pre-filling form via GET parameters (e.g., from "Claim this listing")
        initial_data = request.GET.dict()
        form = SaunaSubmissionForm(initial=initial_data)
    
    page_title = f"Submit a Sauna | {SITE_NAME}"
    meta_description = "Know a sauna that's not listed? Help us grow Ireland's most comprehensive sauna directory by submitting details."
    
    context = {
        "site_name": SITE_NAME,
        "domain": DOMAIN,
        "form": form,
        "page_title": page_title,
        "meta_description": meta_description,
    }
    
    return render(request, "submit_sauna.html", context)


def submit_success(request: HttpRequest) -> HttpResponse:
    """Thank you page after successful submission"""
    page_title = f"Submission Received | {SITE_NAME}"
    meta_description = "Thank you for your sauna submission!"
    
    context = {
        "site_name": SITE_NAME,
        "domain": DOMAIN,
        "page_title": page_title,
        "meta_description": meta_description,
    }
    
    return render(request, "submit_success.html", context)
