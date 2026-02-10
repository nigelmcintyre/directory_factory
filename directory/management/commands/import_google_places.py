import csv
import re
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from directory.models import Listing


class Command(BaseCommand):
    help = "Import Google Places sauna data from CSV"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Path to the Google Places CSV file")
        parser.add_argument("--clear", action="store_true", help="Clear existing listings")

    def extract_city(self, address):
        """Extract city from address string."""
        if not address:
            return "Dublin"
        
        # Common Irish cities/towns
        cities = [
            "Dublin", "Cork", "Galway", "Limerick", "Waterford", "Drogheda", "Dundalk",
            "Swords", "Bray", "Navan", "Ennis", "Kilkenny", "Carlow", "Tralee",
            "Newbridge", "Naas", "Athlone", "Portlaoise", "Mullingar", "Wexford",
            "Letterkenny", "Sligo", "Clonmel", "Killarney", "Wicklow", "Arklow",
            "Cobh", "Castlebar", "Midleton", "Mallow", "Greystones", "Malahide",
            "Rush", "Kinsale", "Dalkey", "Howth", "Dingle", "Westport", "Kildare",
            "Athy", "Shannon", "Dundrum", "Blackrock", "Ranelagh", "Rathgar"
        ]
        
        for city in cities:
            if city.lower() in address.lower():
                return city
        
        # Try to extract from "Co. County" pattern
        match = re.search(r'Co\.\s+([A-Za-z]+)', address)
        if match:
            return match.group(1)
        
        return "Dublin"  # Default

    def extract_county(self, address):
        """Extract county from address string."""
        if not address:
            return ""
        
        # Look for "Co. County" pattern
        match = re.search(r'Co\.\s+([A-Za-z]+)', address)
        if match:
            county = match.group(1)
            # Map common variations
            county_map = {
                "Dublin": "Dublin",
                "Cork": "Cork", 
                "Galway": "Galway",
                "Kerry": "Kerry",
                "Limerick": "Limerick",
                "Donegal": "Donegal",
                "Mayo": "Mayo",
                "Wicklow": "Wicklow",
                "Wexford": "Wexford",
                "Sligo": "Sligo",
                "Clare": "Clare",
                "Tipperary": "Tipperary",
                "Waterford": "Waterford",
                "Kilkenny": "Kilkenny",
                "Kildare": "Kildare",
                "Meath": "Meath",
                "Louth": "Louth",
                "Roscommon": "Roscommon",
            }
            return county_map.get(county, county)
        
        # If no "Co." pattern, try to infer from city
        city_to_county = {
            "Dublin": "Dublin",
            "Cork": "Cork",
            "Galway": "Galway",
            "Limerick": "Limerick",
            "Waterford": "Waterford",
            "Killarney": "Kerry",
            "Tralee": "Kerry",
            "Dingle": "Kerry",
            "Sligo": "Sligo",
            "Ennis": "Clare",
            "Westport": "Mayo",
            "Letterkenny": "Donegal",
            "Dundalk": "Louth",
            "Drogheda": "Louth",
            "Naas": "Kildare",
            "Mullingar": "Westmeath",
            "Athlone": "Westmeath",
            "Wexford": "Wexford",
            "Wicklow": "Wicklow",
            "Greystones": "Wicklow",
            "Bray": "Wicklow",
        }
        
        for city, county in city_to_county.items():
            if city.lower() in address.lower():
                return county
        
        return ""

    def determine_attributes(self, name, summary, reviews, types):
        """Determine sauna attributes from text data."""
        combined_text = f"{name} {summary} {reviews}".lower()
        types_text = (types or "").lower()
        
        attributes = {}

        # Venue type
        if any(term in combined_text for term in ["hotel", "resort", "lodging"]) or "lodging" in types_text:
            attributes["venue_type"] = "Hotel/Resort"
        elif "leisure" in combined_text or "leisure centre" in combined_text or "leisure center" in combined_text:
            attributes["venue_type"] = "Leisure Centre"
        elif any(term in combined_text for term in ["gym", "fitness", "health club", "healthclub"]) or "gym" in types_text:
            attributes["venue_type"] = "Gym/Health Club"
        elif any(term in combined_text for term in ["spa", "wellness"]):
            attributes["venue_type"] = "Spa/Wellness"
        else:
            attributes["venue_type"] = "Dedicated Sauna"
        
        # Heat source
        if "wood" in combined_text or "wood-fired" in combined_text or "wood fired" in combined_text:
            attributes["heat_source"] = "Wood"
        elif "electric" in combined_text:
            attributes["heat_source"] = "Electric"
        elif "infrared" in combined_text:
            attributes["heat_source"] = "Infrared"
        else:
            attributes["heat_source"] = "Not Listed"
        
        def tri_state(positive_phrases, negative_phrases):
            if any(phrase in combined_text for phrase in negative_phrases):
                return "No"
            if any(phrase in combined_text for phrase in positive_phrases):
                return "Yes"
            return "Not Listed"

        # Cold plunge
        attributes["cold_plunge"] = tri_state(
            ["plunge", "cold plunge", "ice bath", "cold bath", "cold water", "ice tub"],
            ["no plunge", "no cold plunge", "no ice bath", "no cold bath", "no cold tub"],
        )
        
        # Sea view
        attributes["sea_view"] = tri_state(
            ["sea view", "seaside", "ocean", "beach", "coast", "coastal", "bay", "harbour", "harbor"],
            ["no sea view", "no ocean view", "not seaside", "no beach view"],
        )
        
        # Dog friendly
        attributes["dog_friendly"] = tri_state(
            ["dog friendly", "dogs welcome", "pet friendly", "pets welcome"],
            ["no dogs", "not dog friendly", "dogs not allowed", "no pets", "pets not allowed"],
        )

        # Changing facilities
        attributes["changing_facilities"] = tri_state(
            [
                "changing room", "changing rooms", "changing facility", "changing facilities",
                "changing area", "locker", "lockers", "locker room", "locker rooms"
            ],
            ["no changing", "no changing room", "no changing facilities", "no lockers", "no locker"],
        )

        # Showers
        attributes["showers"] = tri_state(
            ["shower", "showers", "shower room", "shower rooms", "outdoor shower", "hot shower", "cold shower"],
            ["no shower", "no showers", "no shower room"],
        )
        
        # Private hire
        attributes["private_hire"] = any(word in combined_text for word in [
            "private", "exclusive", "hire", "booking"
        ])
        
        # Price range (estimate from context)
        if "luxury" in combined_text or "premium" in combined_text:
            attributes["price_range"] = "€€€"
        elif "affordable" in combined_text or "budget" in combined_text:
            attributes["price_range"] = "€"
        else:
            attributes["price_range"] = "€€"
        
        return attributes

    def handle(self, *args, **options):
        csv_file = options["csv_file"]
        clear = options.get("clear", False)

        if clear:
            count = Listing.objects.count()
            Listing.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {count} existing listings"))

        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            created_count = 0
            updated_count = 0

            for row in reader:
                name = row.get("name", "").strip()
                if not name:
                    continue

                address = row.get("address", "")
                city = self.extract_city(address)
                county = self.extract_county(address)
                
                # Extract description from summary or first part of reviews
                summary = row.get("summary", "").strip()
                reviews_text = row.get("reviews_text", "").strip()
                
                if summary:
                    description = summary[:500]  # Limit length
                elif reviews_text:
                    # Take first review snippet
                    first_review = reviews_text.split("||")[0].strip()
                    description = first_review[:500] if first_review else ""
                else:
                    description = f"A sauna experience in {city}."

                # Determine attributes
                attributes = self.determine_attributes(
                    name, summary, reviews_text, row.get("types", "")
                )

                # Create slug
                slug = slugify(name)
                
                # Ensure unique slug
                base_slug = slug
                counter = 1
                while Listing.objects.filter(slug=slug).exclude(name=name).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1

                # Extract additional fields
                website = row.get("website", "").strip()
                phone = row.get("phone", "").strip()
                place_id = row.get("place_id", "").strip()
                photo_ref = row.get("photo_ref", "").strip()
                rating = row.get("rating", "").strip()
                reviews_count = row.get("reviews_count", "").strip()
                
                # Convert rating and reviews_count to proper types
                try:
                    rating_decimal = float(rating) if rating else None
                except (ValueError, TypeError):
                    rating_decimal = None
                
                try:
                    reviews_int = int(float(reviews_count)) if reviews_count else None
                except (ValueError, TypeError):
                    reviews_int = None

                # Create or update listing
                listing, created = Listing.objects.update_or_create(
                    slug=slug,
                    defaults={
                        "name": name,
                        "city": city,
                        "county": county,
                        "category": "Sauna",
                        "description": description,
                        "address": address,
                        "website": website,
                        "phone": phone,
                        "place_id": place_id,
                        "photo_ref": photo_ref,
                        "rating": rating_decimal,
                        "reviews_count": reviews_int,
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
