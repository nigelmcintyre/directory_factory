import time
from urllib.parse import urlencode

import requests
from django.core.management.base import BaseCommand

from directory.models import Listing


class Command(BaseCommand):
    help = "Populate listing latitude/longitude from address data using OpenStreetMap Nominatim"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Optional limit for number of listings to update",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Update all listings even if coordinates already exist",
        )
        parser.add_argument(
            "--sleep",
            type=float,
            default=1.0,
            help="Seconds to sleep between requests (default: 1.0)",
        )

    def _build_query(self, listing):
        parts = []
        if listing.address:
            parts.append(listing.address.strip())
        if listing.city:
            parts.append(listing.city.strip())
        if listing.county:
            parts.append(listing.county.strip())
        parts.append("Ireland")
        return ", ".join(part for part in parts if part)

    def _geocode(self, session, query):
        params = {
            "q": query,
            "format": "jsonv2",
            "addressdetails": 0,
            "limit": 1,
            "countrycodes": "ie",
        }
        url = f"https://nominatim.openstreetmap.org/search?{urlencode(params)}"
        response = session.get(url, timeout=15)
        response.raise_for_status()
        payload = response.json()
        if not payload:
            return None, None
        first = payload[0]
        lat = first.get("lat")
        lon = first.get("lon")
        if lat is None or lon is None:
            return None, None
        return float(lat), float(lon)

    def handle(self, *args, **options):
        force = options.get("force", False)
        limit = options.get("limit", 0)
        sleep_seconds = options.get("sleep", 1.0)

        queryset = Listing.objects.filter(is_active=True)
        if not force:
            queryset = queryset.filter(latitude__isnull=True, longitude__isnull=True)

        if limit:
            queryset = queryset[:limit]

        total = queryset.count()
        if total == 0:
            self.stdout.write(self.style.WARNING("No listings to geocode"))
            return

        self.stdout.write(f"Geocoding {total} listings with OSM Nominatim...")

        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": "directory-factory/1.0 (contact: admin@saunaguide.ie)",
                "Accept": "application/json",
            }
        )

        updated = 0
        skipped = 0
        failed = 0

        for listing in queryset:
            query = self._build_query(listing)
            if not query.strip():
                skipped += 1
                self.stdout.write(self.style.WARNING(f"Skipped (no address): {listing.name}"))
                continue

            try:
                lat, lng = self._geocode(session, query)
                if lat is None or lng is None:
                    skipped += 1
                    self.stdout.write(self.style.WARNING(f"Skipped (no match): {listing.name}"))
                else:
                    listing.latitude = lat
                    listing.longitude = lng
                    listing.save(update_fields=["latitude", "longitude"])
                    updated += 1
                    self.stdout.write(self.style.SUCCESS(f"Updated: {listing.name}"))
            except Exception as exc:
                failed += 1
                self.stdout.write(self.style.ERROR(f"Failed: {listing.name} ({exc})"))

            if sleep_seconds:
                time.sleep(sleep_seconds)

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Updated={updated} skipped={skipped} failed={failed}"
            )
        )
