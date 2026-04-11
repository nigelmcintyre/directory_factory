from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Disabled command kept for backward compatibility"

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING(
                "geocode_place_ids is disabled. Use geocode_listings_osm instead."
            )
        )
