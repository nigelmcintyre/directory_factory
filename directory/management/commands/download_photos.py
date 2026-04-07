"""
Django management command to download and store Google Places photos locally as WebP.
Usage: python manage.py download_photos [--limit 10] [--overwrite]
"""

import base64
import io
import time
from urllib.parse import urlencode

import requests
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from PIL import Image
from directory.models import Listing


class Command(BaseCommand):
    help = 'Download Google Places photos and store as WebP in database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit the number of photos to download',
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Overwrite existing photo_data even if already present',
        )
        parser.add_argument(
            '--max-width',
            type=int,
            default=800,
            help='Maximum width for downloaded images (default: 800px)',
        )
        parser.add_argument(
            '--quality',
            type=int,
            default=85,
            help='WebP quality (1-100, default: 85)',
        )

    def handle(self, *args, **options):
        limit = options.get('limit')
        overwrite = options.get('overwrite')
        max_width = options.get('max_width')
        quality = options.get('quality')

        api_key = settings.GOOGLE_MAPS_API_KEY
        if not api_key:
            raise CommandError("GOOGLE_MAPS_API_KEY is not set")

        # Query listings with photo_ref but no photo_data (or all if overwrite)
        queryset = Listing.objects.filter(
            is_active=True,
            photo_ref__isnull=False
        ).exclude(photo_ref='')

        if not overwrite:
            queryset = queryset.filter(photo_data='')

        if limit:
            queryset = queryset[:limit]

        total = queryset.count()
        if total == 0:
            self.stdout.write(self.style.WARNING("No photos to download"))
            return

        self.stdout.write(f"Downloading {total} photos...")

        success_count = 0
        error_count = 0

        for listing in queryset:
            try:
                # Build Google Places Photo API URL
                params = {
                    'maxwidth': max_width,
                    'photoreference': listing.photo_ref,
                    'key': api_key
                }
                url = f"https://maps.googleapis.com/maps/api/place/photo?{urlencode(params)}"

                # Download the image
                self.stdout.write(f"Downloading photo for: {listing.name}")
                response = requests.get(url, timeout=30)
                response.raise_for_status()

                # Process the image
                image = Image.open(io.BytesIO(response.content))

                # Convert to RGB if necessary (WebP doesn't support some modes)
                if image.mode not in ('RGB', 'RGBA'):
                    image = image.convert('RGB')

                # Resize if too large (maintain aspect ratio)
                if image.width > max_width:
                    ratio = max_width / image.width
                    new_height = int(image.height * ratio)
                    image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)

                # Convert to WebP
                webp_buffer = io.BytesIO()
                image.save(webp_buffer, format='WebP', quality=quality, optimize=True)
                webp_data = webp_buffer.getvalue()

                # Encode as base64
                encoded_data = base64.b64encode(webp_data).decode('utf-8')

                # Store in database
                listing.photo_data = encoded_data
                listing.save(update_fields=['photo_data'])

                success_count += 1

                # Rate limiting - Google Places API has limits
                time.sleep(0.1)

            except Exception as e:
                self.stderr.write(f"Error downloading photo for {listing.name}: {str(e)}")
                error_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Completed: {success_count} successful, {error_count} errors"
            )
        )