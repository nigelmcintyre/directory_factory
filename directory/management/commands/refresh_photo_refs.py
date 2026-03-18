"""
Django management command to refresh photo_references from Google Places API.
Usage: python manage.py refresh_photo_refs [--limit 10] [--dry-run] [--verbose]
"""

import googlemaps
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from directory.models import Listing


class Command(BaseCommand):
    help = 'Refresh photo references for all active listings with a place_id'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit the number of listings to process (useful for testing)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output for each listing',
        )

    def handle(self, *args, **options):
        limit = options.get('limit')
        dry_run = options.get('dry_run')
        verbose = options.get('verbose')

        # Initialize Google Maps client
        api_key = settings.GOOGLE_MAPS_API_KEY
        gmaps = googlemaps.Client(key=api_key)

        # Query all active listings with a place_id
        queryset = Listing.objects.filter(is_active=True, place_id__isnull=False).exclude(place_id='')
        
        if limit:
            queryset = queryset[:limit]

        total = queryset.count()
        updated = 0
        unchanged = 0
        errors = 0

        if total == 0:
            self.stdout.write(self.style.WARNING("No active listings with place_id found"))
            return

        self.stdout.write(f"\n🔄 Starting to refresh photo references...")
        if dry_run:
            self.stdout.write(self.style.WARNING("   DRY RUN MODE - No changes will be made"))
        self.stdout.write(f"   Processing {total} listings\n")

        for listing in queryset:
            try:
                if verbose:
                    self.stdout.write(f"🔍 {listing.name} ({listing.place_id})")

                # Get fresh data from Google Places
                place_details = gmaps.place(place_id=listing.place_id, language='en')
                result = place_details.get('result', {})

                if not result:
                    raise ValueError("No result returned from API")

                # Extract photo_reference from the first photo
                photos = result.get('photos', [])
                
                if not photos:
                    if verbose:
                        self.stdout.write(self.style.WARNING(f"   ⊘ No photos available"))
                    unchanged += 1
                    continue

                new_photo_ref = photos[0].get('photo_reference', '')

                if not new_photo_ref:
                    if verbose:
                        self.stdout.write(self.style.WARNING(f"   ⊘ Photo reference not available"))
                    unchanged += 1
                    continue

                # Check if photo_ref is different
                if listing.photo_ref == new_photo_ref:
                    if verbose:
                        self.stdout.write(f"   ✓ Photo reference unchanged")
                    unchanged += 1
                else:
                    if dry_run:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"   [DRY RUN] Would update photo_ref "
                                f"(old: {listing.photo_ref[:20]}... → new: {new_photo_ref[:20]}...)"
                            )
                        )
                    else:
                        listing.photo_ref = new_photo_ref
                        listing.save(update_fields=['photo_ref'])
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"   ✓ Updated photo_ref"
                            )
                        )
                    updated += 1

            except Exception as e:
                errors += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"   ✗ Error: {str(e)}"
                    )
                )

        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("📊 Summary")
        self.stdout.write("=" * 60)
        self.stdout.write(f"Total processed:      {total}")
        self.stdout.write(self.style.SUCCESS(f"Updated:              {updated}"))
        self.stdout.write(f"Unchanged (no photos): {unchanged}")
        self.stdout.write(self.style.ERROR(f"Errors:               {errors}"))
        self.stdout.write("=" * 60)

        if dry_run:
            self.stdout.write("\n" + self.style.WARNING("✓ DRY RUN COMPLETED - No changes were made"))
        else:
            self.stdout.write(self.style.SUCCESS(f"\n✓ Refresh completed!"))
