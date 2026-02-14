from django.core.management.base import BaseCommand
from django.db.models import Count
from directory.models import Listing


class Command(BaseCommand):
    help = "Analyze listings and show which city pages can be generated"

    def add_arguments(self, parser):
        parser.add_argument(
            "--min-listings",
            type=int,
            default=2,
            help="Minimum number of listings required to generate a page (default: 2)",
        )

    def handle(self, *args, **options):
        min_listings = options["min_listings"]

        # Get all active listings grouped by city
        pages = (
            Listing.objects.filter(is_active=True)
            .values("city")
            .annotate(count=Count("id"))
            .filter(count__gte=min_listings)
            .order_by("-count", "city")
        )

        if not pages:
            self.stdout.write(
                self.style.WARNING(
                    f"No pages found with at least {min_listings} listings"
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"\nFound {len(pages)} potential landing pages:\n"
            )
        )

        total_listings = 0
        for page in pages:
            city = page["city"]
            count = page["count"]
            total_listings += count

            url = f"/{city.lower()}/"
            self.stdout.write(
                f"  {self.style.HTTP_INFO(url)} - {count} listing{'s' if count != 1 else ''}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✓ Total: {len(pages)} pages covering {total_listings} listings"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"✓ These URLs are automatically routed by /<city>/"
            )
        )
