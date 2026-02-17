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

        def parse_float(value):
            if value is None:
                return None
            value = str(value).strip()
            if not value or value.lower() in {"nan", "none"}:
                return None
            try:
                return float(value)
            except ValueError:
                return None

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
                
                place_id = (row.get("place_id") or "").strip()
                city = (row.get("city") or "").strip()
                county = (row.get("county") or "").strip()
                address = (row.get("address") or "").strip()
                website = (row.get("website") or "").strip()
                phone = (row.get("phone") or "").strip()
                photo_ref = (row.get("photo_ref") or "").strip()
                latitude = parse_float(row.get("lat"))
                longitude = parse_float(row.get("lng"))
                
                # Handle rating (convert to decimal or None)
                rating_str = (row.get("rating") or "").strip()
                rating = None
                if rating_str and rating_str.lower() not in ['', 'nan', 'none']:
                    try:
                        rating = float(rating_str)
                    except ValueError:
                        rating = None
                
                # Handle reviews_count (convert to int or None)
                reviews_str = (row.get("reviews_count") or "").strip()
                reviews_count = None
                if reviews_str and reviews_str.lower() not in ['', 'nan', 'none']:
                    try:
                        reviews_count = int(float(reviews_str))
                    except ValueError:
                        reviews_count = None
                
                # Build attributes dict with new fields
                attributes = {}
                
                # Heat source
                heat_source = (row.get("heat_source") or "").strip()
                if heat_source:
                    attributes["heat_source"] = heat_source
                
                # All attribute filters now use "yes"/"no"/"not listed" strings
                cold_plunge = (row.get("cold_plunge") or "").strip().lower()
                if cold_plunge in ["yes", "no", "not listed"]:
                    attributes["cold_plunge"] = cold_plunge
                elif cold_plunge in ["true", "false"]:  # backward compatibility
                    attributes["cold_plunge"] = "yes" if cold_plunge == "true" else "no"
                else:
                    attributes["cold_plunge"] = "not listed"
                
                dog_friendly = (row.get("dog_friendly") or "").strip().lower()
                if dog_friendly in ["yes", "no", "not listed"]:
                    attributes["dog_friendly"] = dog_friendly
                elif dog_friendly in ["true", "false"]:
                    attributes["dog_friendly"] = "yes" if dog_friendly == "true" else "no"
                else:
                    attributes["dog_friendly"] = "not listed"
                
                showers = (row.get("showers") or "").strip().lower()
                if showers in ["yes", "no", "not listed"]:
                    attributes["showers"] = showers
                elif showers in ["true", "false"]:
                    attributes["showers"] = "yes" if showers == "true" else "no"
                else:
                    attributes["showers"] = "not listed"
                
                changing_facilities = (row.get("changing_facilities") or "").strip().lower()
                if changing_facilities in ["yes", "no", "not listed"]:
                    attributes["changing_facilities"] = changing_facilities
                elif changing_facilities in ["true", "false"]:
                    attributes["changing_facilities"] = "yes" if changing_facilities == "true" else "no"
                else:
                    attributes["changing_facilities"] = "not listed"
                
                sea_view = (row.get("sea_view") or "").strip().lower()
                if sea_view in ["yes", "no", "not listed"]:
                    attributes["sea_view"] = sea_view
                elif sea_view in ["true", "false"]:
                    attributes["sea_view"] = "yes" if sea_view == "true" else "no"
                else:
                    attributes["sea_view"] = "not listed"
                
                # Opening hours (stored as pipe-separated string)
                opening_hours = (row.get("opening_hours") or "").strip()
                if opening_hours and opening_hours.lower() != "not listed":
                    attributes["opening_hours"] = opening_hours
                
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
                            "latitude": latitude,
                            "longitude": longitude,
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
                            "latitude": latitude,
                            "longitude": longitude,
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
