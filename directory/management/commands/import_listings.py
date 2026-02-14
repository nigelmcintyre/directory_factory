import csv
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from directory.models import Listing


class Command(BaseCommand):
    help = "Import listings from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Path to the CSV file")
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing listings before import",
        )

    def handle(self, *args, **options):
        csv_file = options["csv_file"]
        clear = options.get("clear", False)

        if clear:
            count = Listing.objects.count()
            Listing.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(f"Deleted {count} existing listings")
            )

        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            created_count = 0
            updated_count = 0
            skipped_count = 0

            for row in reader:
                # Extract base fields
                name = row.get("name", "").strip()
                if not name:
                    skipped_count += 1
                    continue
                
                place_id = row.get("place_id", "").strip()
                city = row.get("city", "").strip()
                county = row.get("county", "").strip()
                address = row.get("address", "").strip()
                website = row.get("website", "").strip()
                phone = row.get("phone", "").strip()
                photo_ref = row.get("photo_ref", "").strip()
                
                # Handle rating (convert to decimal or None)
                rating_str = row.get("rating", "").strip()
                rating = None
                if rating_str and rating_str.lower() not in ['', 'nan', 'none']:
                    try:
                        rating = float(rating_str)
                    except ValueError:
                        rating = None
                
                # Handle reviews_count (convert to int or None)
                reviews_str = row.get("reviews_count", "").strip()
                reviews_count = None
                if reviews_str and reviews_str.lower() not in ['', 'nan', 'none']:
                    try:
                        reviews_count = int(float(reviews_str))
                    except ValueError:
                        reviews_count = None
                
                # Build attributes dict with new fields
                attributes = {}
                
                # Heat source
                heat_source = row.get("heat_source", "").strip()
                if heat_source:
                    attributes["heat_source"] = heat_source
                
                # Boolean attributes
                cold_plunge = row.get("cold_plunge", "").strip().lower()
                if cold_plunge in ["true", "false"]:
                    attributes["cold_plunge"] = cold_plunge == "true"
                
                outdoor = row.get("outdoor", "").strip().lower()
                if outdoor in ["true", "false"]:
                    attributes["outdoor"] = outdoor == "true"
                
                private_rooms = row.get("private_rooms", "").strip().lower()
                if private_rooms in ["true", "false"]:
                    attributes["private_rooms"] = private_rooms == "true"
                
                # Generate slug from place_id or name
                if place_id:
                    slug = slugify(f"{name}-{place_id[:10]}")
                else:
                    slug = slugify(f"{name}-{city}")
                
                # Ensure unique slug
                base_slug = slug
                counter = 1
                while Listing.objects.filter(slug=slug).exclude(place_id=place_id).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1
                
                # Create or update listing (match by place_id if available)
                if place_id:
                    listing, created = Listing.objects.update_or_create(
                        place_id=place_id,
                        defaults={
                            "name": name,
                            "slug": slug,
                            "city": city,
                            "county": county,
                            "address": address,
                            "website": website,
                            "phone": phone,
                            "photo_ref": photo_ref,
                            "rating": rating,
                            "reviews_count": reviews_count,
                            "attributes": attributes,
                            "is_active": True,
                        },
                    )
                else:
                    listing, created = Listing.objects.update_or_create(
                        slug=slug,
                        defaults={
                            "name": name,
                            "city": city,
                            "county": county,
                            "address": address,
                            "website": website,
                            "phone": phone,
                            "photo_ref": photo_ref,
                            "rating": rating,
                            "reviews_count": reviews_count,
                            "attributes": attributes,
                            "is_active": True,
                        },
                    )

                if created:
                    created_count += 1
                    self.stdout.write(f"  ✅ Created: {name}")
                else:
                    updated_count += 1
                    self.stdout.write(f"  🔄 Updated: {name}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Import complete: {created_count} created, {updated_count} updated, {skipped_count} skipped"
            )
        )
