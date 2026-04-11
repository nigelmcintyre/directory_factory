from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Disabled command kept for backward compatibility"

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING(
                "add_sauna is disabled to prevent Google API charges."
            )
        )
