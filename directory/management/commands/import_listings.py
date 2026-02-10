import csv
from django.core.management.base import BaseCommand
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

            for row in reader:
                # Extract base fields
                name = row.pop("name")
                slug = row.pop("slug")
                city = row.pop("city")
                category = row.pop("category")
                description = row.pop("description", "")

                # Remaining fields go into attributes
                attributes = {}
                for key, value in row.items():
                    if value.strip():
                        # Convert boolean strings
                        if value.lower() in ["true", "false"]:
                            attributes[key] = value.lower() == "true"
                        else:
                            attributes[key] = value

                # Create or update listing
                listing, created = Listing.objects.update_or_create(
                    slug=slug,
                    defaults={
                        "name": name,
                        "city": city,
                        "category": category,
                        "description": description,
                        "attributes": attributes,
                        "is_active": True,
                    },
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Import complete: {created_count} created, {updated_count} updated"
            )
        )
