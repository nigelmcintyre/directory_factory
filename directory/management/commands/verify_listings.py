from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Disabled command kept for backward compatibility"

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING(
                "verify_listings is disabled to prevent Google API charges."
            )
        )
