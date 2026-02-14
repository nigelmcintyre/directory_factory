"""
Django management command to add a single sauna from Google Maps URL or place_id
Usage: docker-compose exec web python manage.py add_sauna <url_or_place_id>
"""

import re
import googlemaps
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils.text import slugify
from directory.models import Listing


class Command(BaseCommand):
    help = 'Add a single sauna from Google Maps URL or place_id'

    def add_arguments(self, parser):
        parser.add_argument(
            'url_or_place_id',
            type=str,
            help='Google Maps URL, place_id, or place name'
        )
        parser.add_argument(
            '--inactive',
            action='store_true',
            help='Add sauna as inactive (not visible on site)',
        )
        parser.add_argument(
            '--search',
            action='store_true',
            help='Search by place name instead of place_id',
        )

    def extract_place_id(self, url_or_id):
        """Extract place_id from Google Maps URL or return as-is if already a place_id"""
        if url_or_id.startswith('http'):
            # Extract from URL - look for ftid parameter
            match = re.search(r'ftid=([^&]+)', url_or_id)
            if match:
                return match.group(1)
        return url_or_id

    def analyze_reviews_for_attributes(self, reviews):
        """Extract attributes from review text"""
        review_text = " ".join([r.get("text", "").lower() for r in reviews])
        
        attributes = {
            "heat_source": "not listed",
            "cold_plunge": "not listed",
            "dog_friendly": "not listed",
            "showers": "not listed",
            "changing_facilities": "not listed",
            "sea_view": "not listed",
        }
        
        # Heat source detection
        if any(word in review_text for word in ["wood fired", "wood-fired", "wood burning"]):
            attributes["heat_source"] = "wood"
        elif any(word in review_text for word in ["electric heater", "electric sauna"]):
            attributes["heat_source"] = "electric"
        elif "infrared" in review_text:
            attributes["heat_source"] = "infrared"
        
        # Cold plunge detection
        if any(word in review_text for word in ["cold plunge", "ice bath", "cold water", "dip pool"]):
            attributes["cold_plunge"] = "yes"
        elif any(phrase in review_text for phrase in ["no cold plunge", "no ice bath"]):
            attributes["cold_plunge"] = "no"
        
        # Dog friendly detection
        if any(word in review_text for word in ["dog friendly", "dogs welcome", "bring your dog", "dog-friendly"]):
            attributes["dog_friendly"] = "yes"
        elif any(phrase in review_text for phrase in ["no dogs", "dogs not allowed"]):
            attributes["dog_friendly"] = "no"
        
        # Showers detection
        if any(word in review_text for word in ["shower", "showers"]):
            attributes["showers"] = "yes"
        
        # Changing facilities detection
        if any(word in review_text for word in ["changing room", "changing facilities", "changing area"]):
            attributes["changing_facilities"] = "yes"
        
        # Sea view detection
        if any(word in review_text for word in ["sea view", "ocean view", "coastal", "beach", "seaside"]):
            attributes["sea_view"] = "yes"
        
        return attributes

    def handle(self, *args, **options):
        url_or_place_id = options['url_or_place_id']
        is_active = not options['inactive']
        search_by_name = options['search']
        
        # Initialize Google Maps client
        api_key = settings.GOOGLE_MAPS_API_KEY
        gmaps = googlemaps.Client(key=api_key)
        
        # If search flag is set, do a text search
        if search_by_name:
            self.stdout.write(f"🔍 Searching for: {url_or_place_id}")
            try:
                search = gmaps.places(query=url_or_place_id + " Ireland", language='en')
                if not search.get('results'):
                    raise CommandError(f"No results found for '{url_or_place_id}'")
                
                # Show results and use first one
                results = search['results']
                self.stdout.write(f"   Found {len(results)} result(s):")
                for i, r in enumerate(results[:5], 1):
                    self.stdout.write(f"   {i}. {r.get('name')} - {r.get('formatted_address', 'No address')}")
                
                result = results[0]
                place_id = result['place_id']
                self.stdout.write(self.style.SUCCESS(f"\n   Using: {result.get('name')}"))
                
                # Get full details
                place_details = gmaps.place(place_id=place_id, language='en')
                result = place_details.get('result', {})
                
            except Exception as e:
                raise CommandError(f"Search failed: {str(e)}")
        else:
            place_id = self.extract_place_id(url_or_place_id)
            self.stdout.write(f"🔍 Looking up place: {place_id}")
        
            try:
                # Try to get place details by place_id first
                result = None
                try:
                    place_details = gmaps.place(place_id=place_id, language='en')
                    result = place_details.get('result', {})
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"   Direct lookup failed: {e}"))
                    self.stdout.write("   Trying text search...")
                    
                    # Try text search with the URL
                    search = gmaps.places(query=url_or_place_id, language='en')
                    if search.get('results'):
                        result = search['results'][0]
                        place_id = result['place_id']
                        # Get full details
                        place_details = gmaps.place(place_id=place_id, language='en')
                        result = place_details.get('result', {})
                    else:
                        raise CommandError("Could not find place in Google Maps")
                
                if not result:
                    raise CommandError("No place details found")
                
            except Exception as e:
                raise CommandError(f"Error looking up place: {str(e)}")
        
        try:
            
            name = result.get('name', '')
            self.stdout.write(self.style.SUCCESS(f"📍 Found: {name}"))
            
            # Extract location info
            address_components = result.get('address_components', [])
            city = ""
            county = ""
            
            for component in address_components:
                types = component.get('types', [])
                if 'locality' in types or 'postal_town' in types:
                    city = component.get('long_name', '')
                elif 'administrative_area_level_1' in types:
                    county = component.get('long_name', '').replace('County', '').strip()
            
            # Get reviews for attribute extraction
            reviews = result.get('reviews', [])
            attributes = self.analyze_reviews_for_attributes(reviews)
            
            # Check for opening hours
            opening_hours_text = ""
            if 'opening_hours' in result and 'weekday_text' in result['opening_hours']:
                opening_hours_text = "|".join(result['opening_hours']['weekday_text'])
            else:
                opening_hours_text = "not listed"
            
            attributes['opening_hours'] = opening_hours_text
            
            # Create slug
            base_slug = slugify(name)
            slug = base_slug
            counter = 1
            
            # Handle duplicate slugs
            while Listing.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            # Check if already exists by place_id
            if Listing.objects.filter(place_id=place_id).exists():
                existing = Listing.objects.get(place_id=place_id)
                self.stdout.write(self.style.WARNING(
                    f"⚠️  Sauna already exists: {existing.name} (id: {existing.id})"
                ))
                return
            
            # Create listing
            listing = Listing.objects.create(
                name=name,
                slug=slug,
                city=city or "Unknown",
                county=county,
                address=result.get('formatted_address', ''),
                website=result.get('website', ''),
                phone=result.get('formatted_phone_number', ''),
                place_id=place_id,
                photo_ref=result.get('photos', [{}])[0].get('photo_reference', '') if result.get('photos') else '',
                rating=result.get('rating'),
                reviews_count=result.get('user_ratings_total'),
                attributes=attributes,
                description=f"Located in {city or county or 'Ireland'}, {name} offers a unique sauna experience.",
                is_active=is_active
            )
            
            self.stdout.write(self.style.SUCCESS(f"\n✅ Successfully added: {name}"))
            self.stdout.write(f"   ID: {listing.id}")
            self.stdout.write(f"   Slug: {slug}")
            self.stdout.write(f"   City: {city or 'N/A'}")
            self.stdout.write(f"   County: {county or 'N/A'}")
            self.stdout.write(f"   Rating: {result.get('rating', 'N/A')} ({result.get('user_ratings_total', 0)} reviews)")
            self.stdout.write(f"   Address: {result.get('formatted_address', 'N/A')}")
            self.stdout.write(f"   Website: {result.get('website', 'N/A')}")
            self.stdout.write(f"   Phone: {result.get('formatted_phone_number', 'N/A')}")
            self.stdout.write(f"   Heat Source: {attributes['heat_source']}")
            self.stdout.write(f"   Cold Plunge: {attributes['cold_plunge']}")
            self.stdout.write(f"   Opening Hours: {'✓' if opening_hours_text != 'not listed' else '✗'}")
            self.stdout.write(f"   Active: {'✓' if is_active else '✗'}")
            self.stdout.write(f"\n   View at: http://localhost:8000/listing/{slug}/")
            
            # Show total count
            total = Listing.objects.filter(is_active=True).count()
            self.stdout.write(self.style.SUCCESS(f"\n📊 Total active listings: {total}"))
            
        except Exception as e:
            raise CommandError(f"Error adding sauna: {str(e)}")
