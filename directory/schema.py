from directory.niche_config import SITE_NAME, DOMAIN


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

    return schema


def generate_breadcrumb_schema(city, site_name):
    """Generate Schema.org BreadcrumbList for pSEO pages."""
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
                "name": city.title(),
                "item": f"https://{DOMAIN}/{city.lower()}/",
            },
            {
                "@type": "ListItem",
                "position": 3,
                "name": f"Saunas in {city.title()}",
            },
        ],
    }
