import re

from django.utils.text import slugify

from directory.niche_config import SITE_NAME, DOMAIN


def _normalize_time_token(token: str) -> str | None:
    token = token.strip().lower()
    match = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)$", token)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2) or "00")
    meridiem = match.group(3)

    if hour < 1 or hour > 12 or minute > 59:
        return None

    if meridiem == "am":
        hour = 0 if hour == 12 else hour
    else:
        hour = 12 if hour == 12 else hour + 12

    return f"{hour:02d}:{minute:02d}"


def _normalize_time_range(range_text: str) -> tuple[str, str] | None:
    if "-" not in range_text:
        return None
    start_raw, end_raw = [part.strip() for part in range_text.split("-", 1)]
    start = _normalize_time_token(start_raw)
    end = _normalize_time_token(end_raw)
    if not start or not end:
        return None
    return start, end


def generate_listing_schema(listing):
    """Generate Schema.org LocalBusiness JSON-LD for a listing."""
    schema = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": listing.name,
        "description": listing.description,
        "url": f"https://{DOMAIN}/listing/{listing.slug}/",
    }

    # Add address if we have city info
    if listing.city:
        schema["address"] = {
            "@type": "PostalAddress",
            "addressLocality": listing.city,
            "addressCountry": "IE",
        }
        if listing.county:
            schema["address"]["addressRegion"] = listing.county
        if listing.address:
            schema["address"]["streetAddress"] = listing.address
    
    # Add geo coordinates if available
    if listing.latitude and listing.longitude:
        schema["geo"] = {
            "@type": "GeoCoordinates",
            "latitude": listing.latitude,
            "longitude": listing.longitude
        }
    
    # Add contact information
    if listing.phone:
        schema["telephone"] = listing.phone
    if listing.website:
        schema["url"] = listing.website
    
    # Add rating with required reviewCount
    if listing.rating:
        schema["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": str(listing.rating),
            "bestRating": "5",
            "reviewCount": str(listing.reviews_count or 1)
        }
    
    # Add opening hours if available
    if opening_hours := listing.attributes.get("opening_hours"):
        # Parse opening_hours format (e.g., "Monday: 9am-5pm|Tuesday: 9am-5pm")
        hours_list = []
        days_map = {
            "monday": "Monday",
            "tuesday": "Tuesday", 
            "wednesday": "Wednesday",
            "thursday": "Thursday",
            "friday": "Friday",
            "saturday": "Saturday",
            "sunday": "Sunday"
        }
        
        for day_hours in opening_hours.split("|"):
            if ":" in day_hours:
                day_part, hours_part = day_hours.split(":", 1)
                day_clean = day_part.strip().lower()
                hours_clean = hours_part.strip()
                
                if day_clean in days_map and hours_clean.lower() != "closed":
                    normalized = _normalize_time_range(hours_clean)
                    if not normalized:
                        continue
                    opens, closes = normalized
                    hours_list.append({
                        "@type": "OpeningHoursSpecification",
                        "dayOfWeek": days_map[day_clean],
                        "opens": opens,
                        "closes": closes,
                    })
        
        if hours_list:
            schema["openingHoursSpecification"] = hours_list

    return schema


def generate_breadcrumb_schema(county, site_name, county_slug=None):
    """Generate Schema.org BreadcrumbList for county pSEO pages."""
    slug = county_slug or slugify(county)
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": site_name,
                "item": f"https://{DOMAIN}/",
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": county.title(),
                "item": f"https://{DOMAIN}/{slug}/",
            },
            {
                "@type": "ListItem",
                "position": 3,
                "name": f"Saunas in {county.title()}",
            },
        ],
    }
