"""
Django management command to verify and fix listing details using Google Maps API
Usage: 
  docker-compose exec web python manage.py verify_listings
  docker-compose exec web python manage.py verify_listings --fix
  docker-compose exec web python manage.py verify_listings --county-only
"""

import googlemaps
from django.core.management.base import BaseCommand
from django.conf import settings
from directory.models import Listing


class Command(BaseCommand):
    help = 'Verify listing details against Google Maps API and optionally fix issues'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Automatically fix detected issues',
        )
        parser.add_argument(
            '--county-only',
            action='store_true',
            help='Only verify county information',
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit number of listings to check (useful for testing)',
        )
        parser.add_argument(
            '--place-id',
            type=str,
            help='Check only a specific place_id',
        )

    def verify_county(self, listing, place_details):
        """Verify county information"""
        address_components = place_details.get('address_components', [])
        correct_county = None
        
        for component in address_components:
            types = component.get('types', [])
            if 'administrative_area_level_1' in types:
                correct_county = component.get('long_name', '').replace('County', '').strip()
                break
        
        if correct_county and listing.county != correct_county:
            return {
                'field': 'county',
                'current': listing.county,
                'correct': correct_county,
                'severity': 'high'
            }
        return None

    def verify_city(self, listing, place_details):
        """Verify city information"""
        address_components = place_details.get('address_components', [])
        correct_city = None
        
        for component in address_components:
            types = component.get('types', [])
            if 'locality' in types or 'postal_town' in types:
                correct_city = component.get('long_name', '')
                break
        
        if correct_city and listing.city != correct_city:
            return {
                'field': 'city',
                'current': listing.city,
                'correct': correct_city,
                'severity': 'medium'
            }
        return None

    def verify_phone(self, listing, place_details):
        """Verify phone number"""
        correct_phone = place_details.get('formatted_phone_number', '')
        
        if correct_phone and not listing.phone:
            return {
                'field': 'phone',
                'current': 'missing',
                'correct': correct_phone,
                'severity': 'low'
            }
        elif correct_phone and listing.phone != correct_phone:
            return {
                'field': 'phone',
                'current': listing.phone,
                'correct': correct_phone,
                'severity': 'low'
            }
        return None

    def verify_website(self, listing, place_details):
        """Verify website"""
        correct_website = place_details.get('website', '')
        
        if correct_website and not listing.website:
            return {
                'field': 'website',
                'current': 'missing',
                'correct': correct_website,
                'severity': 'low'
            }
        return None

    def handle(self, *args, **options):
        fix_issues = options['fix']
        county_only = options['county_only']
        limit = options.get('limit')
        place_id_filter = options.get('place_id')
        
        # Initialize Google Maps client
        api_key = settings.GOOGLE_MAPS_API_KEY
        gmaps = googlemaps.Client(key=api_key)
        
        # Get listings to check
        if place_id_filter:
            listings = Listing.objects.filter(place_id=place_id_filter)
        else:
            listings = Listing.objects.filter(is_active=True).exclude(place_id='')
        
        if limit:
            listings = listings[:limit]
        
        total = listings.count()
        self.stdout.write(f"🔍 Checking {total} listing(s)...\n")
        
        issues_found = 0
        issues_fixed = 0
        checked = 0
        errors = 0
        
        for listing in listings:
            checked += 1
            
            if checked % 10 == 0:
                self.stdout.write(f"   Progress: {checked}/{total}")
            
            try:
                # Get fresh data from Google Maps
                place_details = gmaps.place(place_id=listing.place_id, language='en')
                result = place_details.get('result', {})
                
                if not result:
                    self.stdout.write(self.style.WARNING(f"⚠️  {listing.name}: No data from API"))
                    errors += 1
                    continue
                
                # Check for issues
                listing_issues = []
                
                # Always check county
                county_issue = self.verify_county(listing, result)
                if county_issue:
                    listing_issues.append(county_issue)
                
                # Check other fields unless county_only flag is set
                if not county_only:
                    city_issue = self.verify_city(listing, result)
                    if city_issue:
                        listing_issues.append(city_issue)
                    
                    phone_issue = self.verify_phone(listing, result)
                    if phone_issue:
                        listing_issues.append(phone_issue)
                    
                    website_issue = self.verify_website(listing, result)
                    if website_issue:
                        listing_issues.append(website_issue)
                
                # Report and optionally fix issues
                if listing_issues:
                    issues_found += len(listing_issues)
                    self.stdout.write(self.style.WARNING(f"\n❌ {listing.name} (ID: {listing.id})"))
                    
                    for issue in listing_issues:
                        severity_icon = '🔴' if issue['severity'] == 'high' else '🟡' if issue['severity'] == 'medium' else '🟢'
                        self.stdout.write(f"   {severity_icon} {issue['field'].upper()}: '{issue['current']}' → '{issue['correct']}'")
                        
                        if fix_issues:
                            setattr(listing, issue['field'], issue['correct'])
                            issues_fixed += 1
                    
                    if fix_issues:
                        listing.save()
                        self.stdout.write(self.style.SUCCESS(f"   ✅ Fixed {len(listing_issues)} issue(s)"))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error checking {listing.name}: {str(e)}"))
                errors += 1
                continue
        
        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS(f"\n📊 Verification Summary:"))
        self.stdout.write(f"   Listings checked: {checked}")
        self.stdout.write(f"   Issues found: {issues_found}")
        if fix_issues:
            self.stdout.write(self.style.SUCCESS(f"   Issues fixed: {issues_fixed}"))
        self.stdout.write(f"   Errors: {errors}")
        
        if issues_found > 0 and not fix_issues:
            self.stdout.write(self.style.WARNING(f"\n💡 Run with --fix flag to automatically correct these issues"))
        elif issues_found == 0:
            self.stdout.write(self.style.SUCCESS(f"\n✅ All listings verified - no issues found!"))
