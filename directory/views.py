import json
import os
from urllib.parse import urlencode
from datetime import datetime, timezone as dt_timezone, timedelta
from django.utils.text import slugify
from django.conf import settings
from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.safestring import mark_safe
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from .models import Listing, FeaturedListingSubscription, StripeWebhookEvent
from .forms import SaunaSubmissionForm, PartnerInquiryForm
from .niche_config import SITE_NAME, DOMAIN, FILTERS
from .utils import get_filtered_listings, paginate_listings
from .schema import generate_breadcrumb_schema, generate_listing_schema


def _is_htmx(request: HttpRequest) -> bool:
    return request.headers.get("HX-Request", "false").lower() == "true"


def _to_datetime(timestamp):
    if not timestamp:
        return None
    return datetime.fromtimestamp(timestamp, tz=dt_timezone.utc)


def _sync_featured_flag(subscription: FeaturedListingSubscription) -> None:
    if not subscription.auto_manage_featured:
        return
    should_be_featured = subscription.should_be_featured(timezone.now())
    if subscription.listing.is_featured != should_be_featured:
        subscription.listing.is_featured = should_be_featured
        subscription.listing.save(update_fields=["is_featured", "updated_at"])


def _upsert_subscription_from_stripe(subscription_payload: dict) -> None:
    subscription_id = subscription_payload.get("id")
    if not subscription_id:
        return

    record = FeaturedListingSubscription.objects.filter(
        stripe_subscription_id=subscription_id
    ).select_related("listing").first()
    if not record:
        # Manual onboarding flow: create this link in admin first.
        return

    items = subscription_payload.get("items", {}).get("data", [])
    first_item = items[0] if items else {}
    price_id = (first_item.get("price") or {}).get("id", "")

    record.stripe_customer_id = subscription_payload.get("customer", "") or ""
    record.stripe_price_id = price_id
    record.subscription_status = subscription_payload.get("status", record.subscription_status)
    # Stripe API >=2025-03 moved current_period_end onto subscription items.
    period_end = subscription_payload.get("current_period_end")
    if not period_end and first_item:
        period_end = first_item.get("current_period_end")
    record.current_period_end = _to_datetime(period_end)
    record.cancel_at_period_end = bool(subscription_payload.get("cancel_at_period_end", False))
    if record.subscription_status in {"active", "trialing"}:
        record.grace_until = None
    record.save()
    _sync_featured_flag(record)


@csrf_exempt
def stripe_webhook(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return HttpResponse(status=405)

    if not getattr(settings, "STRIPE_ENABLED", False):
        return JsonResponse({"ok": False, "message": "Stripe disabled"}, status=503)

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    endpoint_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "")
    if not endpoint_secret:
        return JsonResponse(
            {"ok": False, "message": "STRIPE_WEBHOOK_SECRET not configured"},
            status=503,
        )

    try:
        import stripe
    except ImportError:
        return JsonResponse(
            {"ok": False, "message": "stripe package not installed"},
            status=503,
        )

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        return HttpResponse(status=400)
    except stripe.SignatureVerificationError:
        return HttpResponse(status=400)

    event_type = event.get("type", "")
    event_data = event.get("data", {}).get("object", {})
    event_id = event.get("id", "")

    # Idempotency: Stripe retries deliveries. Skip if we've already processed this event.
    if event_id:
        _, created = StripeWebhookEvent.objects.get_or_create(
            stripe_event_id=event_id,
            defaults={"event_type": event_type},
        )
        if not created:
            return JsonResponse({"ok": True, "duplicate": True})

    if event_type in {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }:
        _upsert_subscription_from_stripe(event_data)

    elif event_type in {"invoice.paid", "invoice.payment_failed"}:
        subscription_id = event_data.get("subscription")
        if subscription_id:
            record = FeaturedListingSubscription.objects.filter(
                stripe_subscription_id=subscription_id
            ).select_related("listing").first()
            if record:
                record.last_invoice_status = event_data.get("status", "") or ""
                if event_type == "invoice.payment_failed":
                    grace_days = getattr(settings, "FEATURED_GRACE_DAYS", 7)
                    record.grace_until = timezone.now() + timedelta(days=grace_days)
                elif event_type == "invoice.paid":
                    record.grace_until = None
                record.save(update_fields=["last_invoice_status", "grace_until", "updated_at"])
                _sync_featured_flag(record)

    return JsonResponse({"ok": True})


def robots_txt(request: HttpRequest) -> HttpResponse:
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /submit/",
        f"Sitemap: https://{DOMAIN}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def ads_txt(request: HttpRequest) -> HttpResponse:
    content = "google.com, pub-1872557624162625, DIRECT, f08c47fec0942fa0\n"
    return HttpResponse(content, content_type="text/plain")


def home(request: HttpRequest) -> HttpResponse:
    listings, near_me_context = get_filtered_listings(request)
    page_obj, listings_count, next_page_url = paginate_listings(request, listings)
    page_listings = list(page_obj.object_list)

    # For HTMX paginated requests (page > 1), return only the next page of cards.
    if _is_htmx(request) and page_obj.number > 1:
        return render(
            request,
            "partials/listing_page.html",
            {
                "filters": FILTERS,
                "listings": page_listings,
                "page_obj": page_obj,
                "next_page_url": next_page_url,
            },
        )

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

    # Map markers should reflect ALL filtered listings, not just the current page.
    # Use .values() to avoid loading the heavy photo_data column for every listing.
    map_listings = []
    if isinstance(listings, list):
        # near_me path returns a Python list with distance_km annotations
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
    else:
        rows = (
            listings
            .exclude(latitude__isnull=True)
            .exclude(longitude__isnull=True)
            .values("name", "latitude", "longitude", "county", "city", "address", "slug")
        )
        for row in rows:
            map_listings.append(
                {
                    "name": row["name"],
                    "lat": row["latitude"],
                    "lng": row["longitude"],
                    "location": row["county"] or row["city"],
                    "address": row["address"],
                    "url": f"/listing/{row['slug']}/",
                    "distance_km": None,
                }
            )
    
    context = {
        "site_name": SITE_NAME,
        "domain": DOMAIN,
        "filters": FILTERS,
        "listings": page_listings,
        "listings_count": listings_count,
        "page_obj": page_obj,
        "next_page_url": next_page_url,
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

    # Paginate the listings (10 per page)
    page_obj, _, next_page_url = paginate_listings(request, listings)
    page_listings = list(page_obj.object_list)

    # For HTMX paginated requests (page > 1), return only the next page of cards.
    if _is_htmx(request) and page_obj.number > 1:
        return render(
            request,
            "partials/listing_page.html",
            {
                "filters": FILTERS,
                "listings": page_listings,
                "page_obj": page_obj,
                "next_page_url": next_page_url,
            },
        )

    context = {
        "site_name": SITE_NAME,
        "domain": DOMAIN,
        "filters": FILTERS,
        "listings": page_listings,
        "listings_count": listings_count,
        "page_obj": page_obj,
        "next_page_url": next_page_url,
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
        form = SaunaSubmissionForm()
    
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


def get_featured(request: HttpRequest) -> HttpResponse:
    """Partner program page - featured listing inquiry form"""
    import urllib.request
    import urllib.parse
    import json

    def send_telegram(text: str) -> None:
        token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        if not token or not chat_id:
            return
        payload = urllib.parse.urlencode({"chat_id": chat_id, "text": text, "parse_mode": "HTML"}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=payload,
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10)

    if request.method == 'POST':
        form = PartnerInquiryForm(request.POST)
        if form.is_valid():
            tier_label = dict(form.fields['tier_interest'].choices).get(
                form.cleaned_data['tier_interest'], form.cleaned_data['tier_interest']
            )
            telegram_message = (
                f"<b>New Partner Inquiry</b>\n\n"
                f"<b>Sauna:</b> {form.cleaned_data['sauna_name']}\n"
                f"<b>Contact:</b> {form.cleaned_data['contact_name']}\n"
                f"<b>Email:</b> {form.cleaned_data['contact_email']}\n"
                f"<b>Phone:</b> {form.cleaned_data.get('phone') or 'Not provided'}\n"
                f"<b>Tier:</b> {tier_label}\n\n"
                f"<b>Message:</b>\n{form.cleaned_data.get('message') or 'None'}\n\n"
                f"<a href=\"https://{DOMAIN}{request.path}\">Get Featured page</a>"
            )

            try:
                send_telegram(telegram_message)
                messages.success(
                    request,
                    "Thank you! We've received your inquiry and will be in touch as soon as possible."
                )
            except Exception as e:
                messages.error(
                    request,
                    "We received your inquiry, but there was an issue sending our confirmation. We'll still follow up shortly."
                )
            
            # Reset form after successful submission
            form = PartnerInquiryForm()
    else:
        form = PartnerInquiryForm()
    
    page_title = f"Get Featured | Partner Program | {SITE_NAME}"
    meta_description = "Grow your bookings with a featured listing on the sauna directory. Featured placement, booking integration, and more starting at €39/month."
    
    context = {
        "site_name": SITE_NAME,
        "domain": DOMAIN,
        "form": form,
        "page_title": page_title,
        "meta_description": meta_description,
        "tier_prices": {
            "tier1": 39,
            "tier2": 49,
            "setup_fee": 350,
        }
    }
    
    return render(request, "get_featured.html", context)
