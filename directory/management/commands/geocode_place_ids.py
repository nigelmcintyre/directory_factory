import time
from django.conf import settings
from django.core.management.base import BaseCommand
import googlemaps
from directory.models import Listing


class Command(BaseCommand):
    help = "Populate listing latitude/longitude using Google Places place_id"

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
            default=0.1,
            help="Seconds to sleep between API calls",
        )

    def handle(self, *args, **options):
        api_key = settings.GOOGLE_MAPS_API_KEY
        if not api_key:
            self.stderr.write(self.style.ERROR("GOOGLE_MAPS_API_KEY is not set"))
            return

        gmaps = googlemaps.Client(key=api_key)
        force = options.get("force", False)
        limit = options.get("limit", 0)
        sleep_seconds = options.get("sleep", 0.1)

        queryset = Listing.objects.exclude(place_id="").exclude(place_id__isnull=True)
        if not force:
            queryset = queryset.filter(latitude__isnull=True, longitude__isnull=True)

        if limit:
            queryset = queryset[:limit]

        total = queryset.count()
        if total == 0:
            self.stdout.write(self.style.WARNING("No listings to geocode"))
            return

        self.stdout.write(f"Geocoding {total} listings...")
        updated = 0
        skipped = 0
        failed = 0

        for listing in queryset:
            try:
                details = gmaps.place(place_id=listing.place_id, fields=["geometry"])
                geometry = details.get("result", {}).get("geometry", {})
                location = geometry.get("location", {})
                lat = location.get("lat")
                lng = location.get("lng")
                if lat is None or lng is None:
                    skipped += 1
                    self.stdout.write(self.style.WARNING(f"Skipped (no coords): {listing.name}"))
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
