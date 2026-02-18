import googlemaps
import time
from django.core.management.base import BaseCommand
from django.conf import settings
from directory.models import Listing


class Command(BaseCommand):
    help = "Fetch Google reviews for listings with place_id"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit number of listings to process"
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force refresh even if reviews already exist"
        )

    def handle(self, *args, **options):
        api_key = settings.GOOGLE_MAPS_API_KEY
        
        if not api_key:
            self.stderr.write(self.style.ERROR("GOOGLE_MAPS_API_KEY is not set"))
            return

        # Initialize Google Maps client
        gmaps = googlemaps.Client(key=api_key)

        # Get listings with place_id
        queryset = Listing.objects.filter(is_active=True).exclude(place_id="")
        
        if not options["force"]:
            # Skip listings that already have reviews
            queryset = queryset.filter(structured_data__google_reviews__isnull=True)
        
        if options["limit"]:
            queryset = queryset[:options["limit"]]

        total = queryset.count()
        self.stdout.write(f"Processing {total} listings...")

        success_count = 0
        error_count = 0

        for listing in queryset:
            try:
                # Fetch place details with reviews
                result = gmaps.place(
                    place_id=listing.place_id,
                    fields=["reviews", "rating", "user_ratings_total"]
                )
                
                if result.get("status") == "OK":
                    place_data = result.get("result", {})
                    reviews = place_data.get("reviews", [])
                    
                    # Store reviews in structured_data
                    if not listing.structured_data:
                        listing.structured_data = {}
                    
                    listing.structured_data["google_reviews"] = reviews
                    
                    # Also update rating and reviews_count if available
                    if "rating" in place_data:
                        listing.rating = place_data["rating"]
                    if "user_ratings_total" in place_data:
                        listing.reviews_count = place_data["user_ratings_total"]
                    
                    listing.save()
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ {listing.name}: Fetched {len(reviews)} reviews"
                        )
                    )
                    success_count += 1
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"⚠ {listing.name}: API returned {result.get('status')}"
                        )
                    )
                    error_count += 1
                
                # Rate limiting - sleep briefly between requests
                time.sleep(0.1)
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"✗ {listing.name}: {str(e)}")
                )
                error_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\nComplete: {success_count} successful, {error_count} errors"
            )
        )
