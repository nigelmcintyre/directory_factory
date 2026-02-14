# =============================================================================
# ENHANCED SAUNA SCRAPER - High Quality Results
# =============================================================================

# 1. INSTALLATION
!pip install -q googlemaps pandas

# 2. IMPORTS
import googlemaps
import pandas as pd
import time
from datetime import datetime
from google.colab import userdata
from google.colab import files

# 3. API CONFIGURATION
try:
    API_KEY = userdata.get('GOOGLE_MAPS_KEY')
except:
    API_KEY = "YOUR_ACTUAL_API_KEY_HERE"

if API_KEY == "YOUR_ACTUAL_API_KEY_HERE":
    print("⚠️ CRITICAL: Replace 'YOUR_ACTUAL_API_KEY_HERE' with your real key.")
else:
    # Initialize Client
    gmaps = googlemaps.Client(key=API_KEY)

    # 4. COUNTY/CITY MAPPING
    COUNTIES = {
        "Carlow": ["Carlow"],
        "Cavan": ["Cavan"],
        "Clare": ["Ennis", "Shannon"],
        "Cork": ["Cork City", "Kinsale", "Cobh", "Bandon"],
        "Donegal": ["Letterkenny", "Donegal Town"],
        "Dublin": ["Dublin City", "Dún Laoghaire", "Swords", "Malahide"],
        "Galway": ["Galway City", "Salthill"],
        "Kerry": ["Killarney", "Tralee", "Dingle"],
        "Kildare": ["Naas", "Maynooth", "Newbridge"],
        "Kilkenny": ["Kilkenny"],
        "Laois": ["Portlaoise"],
        "Leitrim": ["Carrick-on-Shannon"],
        "Limerick": ["Limerick City"],
        "Longford": ["Longford"],
        "Louth": ["Drogheda", "Dundalk"],
        "Mayo": ["Castlebar", "Westport"],
        "Meath": ["Navan", "Trim"],
        "Monaghan": ["Monaghan"],
        "Offaly": ["Tullamore"],
        "Roscommon": ["Roscommon"],
        "Sligo": ["Sligo"],
        "Tipperary": ["Clonmel", "Nenagh"],
        "Waterford": ["Waterford City"],
        "Westmeath": ["Mullingar", "Athlone"],
        "Wexford": ["Wexford"],
        "Wicklow": ["Wicklow", "Bray", "Greystones"]
    }

    # 5. GENERATE QUERIES
    QUERIES = []
    for county in COUNTIES.keys():
        QUERIES.extend([
            f"Sauna in Co. {county}, Ireland",
            f"Sea Swimming Sauna Co. {county}",
            f"Mobile Sauna {county}",
            f"Outdoor Sauna {county}"
        ])

    QUERIES.extend([
        "Barrel sauna Ireland",
        "Sea sauna Ireland",
        "Cold plunge sauna Ireland",
        "Wood fired sauna Ireland",
        "Finnish sauna Ireland",
        "Sauna Dublin City",
        "Sauna Cork City",
        "Sauna Galway City"
    ])

    # 6. UTILITY FUNCTIONS
    def extract_county_from_address(address, query=""):
        """Extract county from Irish address"""
        if not address:
            return "Unknown"
        
        # Try from query first
        if "Co. " in query:
            county = query.split("Co. ")[1].split(",")[0].strip()
            if county in COUNTIES:
                return county
        
        # Check address for county
        for county in COUNTIES.keys():
            if f"Co. {county}" in address or f", {county}" in address:
                return county
        
        # Check by city
        for county, cities in COUNTIES.items():
            for city in cities:
                if city in address:
                    return county
        
        return "Unknown"

    def extract_city_from_address(address):
        """Extract city/town from Irish address"""
        if not address:
            return "Unknown"
        
        for county, cities in COUNTIES.items():
            for city in cities:
                if city in address:
                    return city
        
        parts = [p.strip() for p in address.split(',')]
        if len(parts) >= 2:
            return parts[-3] if len(parts) > 2 else parts[0]
        
        return "Unknown"

    def extract_attributes(name, summary, reviews):
        """Extract sauna attributes from text"""
        full_text = f"{name} {summary} {reviews}".lower()
        
        attributes = {}
        if any(word in full_text for word in ["wood", "wood-fired", "timber"]):
            attributes['heat_source'] = "Wood"
        elif "infrared" in full_text:
            attributes['heat_source'] = "Infrared"
        elif "electric" in full_text:
            attributes['heat_source'] = "Electric"
        else:
            attributes['heat_source'] = ""
        
        attributes['cold_plunge'] = any(word in full_text for word in ["cold plunge", "ice bath", "cold water"])
        attributes['outdoor'] = any(word in full_text for word in ["outdoor", "outside", "garden"])
        attributes['private_rooms'] = any(word in full_text for word in ["private", "individual room", "exclusive"])
        
        return attributes

    def is_valid_sauna(data, place_types):
        """Filter out non-sauna businesses"""
        name = data.get('name', '').lower()
        summary = data.get('editorial_summary', {}).get('overview', '').lower()
        website = data.get('website', '').lower()
        types_str = " ".join(place_types).lower()
        combined = f"{name} {summary} {website} {types_str}"
        
        # STRICT EXCLUSIONS
        strict_exclude = [
            "builder", "construction", "supplier", "manufacturer", "manufacturing",
            "sales", "sell", "buy", "shop", "store", "hut", "huts",
            "aesthetic", "aesthetics", "beauty bar", "beauty salon",
            "nails", "lashes", "botox", "filler", "laser", "waxing",
            "massage therapist", "chiropractor", "physiotherap",
            "dealer", "distributor", "installer", "installation",
            "for sale", "rent a sauna", "hire a sauna"
        ]
        
        if any(keyword in combined for keyword in strict_exclude):
            return False
        
        # Exclude beauty/spa places without sauna in name
        beauty_types = ["beauty_salon", "hair_care", "spa"]
        if any(t in types_str for t in beauty_types):
            if "sauna" not in name and "sauna" not in summary:
                return False
        
        # Must have sauna as core business
        sauna_keywords = ["sauna", "barrel sauna", "mobile sauna", "sea swimming", "cold plunge"]
        has_sauna = any(keyword in name or keyword in summary for keyword in sauna_keywords)
        
        # Exclude restaurants unless "sauna" in name
        general_exclude = ["restaurant", "grocery", "repair"]
        is_excluded = any(keyword in name for keyword in general_exclude)
        
        if "cafe" in name and "sauna" in name:
            is_excluded = False
        
        return has_sauna and not is_excluded

    # 7. MAIN FETCH FUNCTION
    def fetch_places(queries):
        all_results = []
        seen_place_ids = set()
        skipped = 0

        for idx, query in enumerate(queries):
            print(f"\n🔍 [{idx+1}/{len(queries)}] Searching: {query}...")

            try:
                places_result = gmaps.places(query=query)
            except Exception as e:
                print(f"   ❌ Search Error: {e}")
                time.sleep(2)
                continue

            results_count = 0
            while True:
                for place in places_result.get('results', []):
                    place_id = place['place_id']
                    name = place['name']

                    if place_id in seen_place_ids:
                        continue
                    seen_place_ids.add(place_id)

                    try:
                        details = gmaps.place(
                            place_id=place_id,
                            fields=['name', 'formatted_address', 'geometry', 'website', 
                                  'formatted_phone_number', 'rating', 'user_ratings_total', 
                                  'reviews', 'type', 'editorial_summary', 'photo', 
                                  'business_status']
                        )

                        data = details['result']
                        place_types = data.get('types', []) or data.get('type', [])
                        address = data.get('formatted_address', '')

                        # Filter: Only Ireland/UK
                        if 'Ireland' not in address and 'UK' not in address:
                            continue

                        # Filter: Only operational businesses
                        business_status = data.get('business_status', 'OPERATIONAL')
                        if business_status not in ['OPERATIONAL', 'OPERATIONAL_OPEN']:
                            print(f"   ⏭️  Skipped (closed): {name}")
                            skipped += 1
                            continue

                        # Filter: Validate it's a real sauna
                        if not is_valid_sauna(data, place_types):
                            print(f"   ⏭️  Skipped (not sauna): {name}")
                            skipped += 1
                            continue

                        # Extract location data
                        county = extract_county_from_address(address, query)
                        city = extract_city_from_address(address)

                        # Photo references
                        photo_ref = ""
                        if 'photos' in data and len(data['photos']) > 0:
                            photo_ref = data['photos'][0].get('photo_reference', '')

                        # Extract attributes
                        summary = data.get('editorial_summary', {}).get('overview', '')
                        reviews_text = " || ".join([r.get('text', '') for r in data.get('reviews', [])[:5]])
                        attributes = extract_attributes(name, summary, reviews_text)

                        flat_data = {
                            'name': data.get('name'),
                            'place_id': place_id,
                            'address': address,
                            'city': city,
                            'county': county,
                            'lat': data['geometry']['location']['lat'],
                            'lng': data['geometry']['location']['lng'],
                            'website': data.get('website', ''),
                            'phone': data.get('formatted_phone_number', ''),
                            'rating': data.get('rating'),
                            'reviews_count': data.get('user_ratings_total'),
                            'photo_ref': photo_ref,
                            'heat_source': attributes['heat_source'],
                            'cold_plunge': attributes['cold_plunge'],
                            'outdoor': attributes['outdoor'],
                            'private_rooms': attributes['private_rooms'],
                            'business_status': business_status,
                            'types': ", ".join(place_types),
                            'summary': summary,
                            'reviews_text': reviews_text
                        }

                        all_results.append(flat_data)
                        results_count += 1
                        print(f"   ✅ {flat_data['name']} ({city}, {county})")

                    except Exception as e:
                        print(f"   ❌ Error for {name}: {e}")

                if 'next_page_token' in places_result:
                    print(f"   📖 Loading next page...")
                    time.sleep(2)
                    try:
                        places_result = gmaps.places(query=query, page_token=places_result['next_page_token'])
                    except:
                        break
                else:
                    break

            print(f"   📊 Found {results_count} new from this query")
            time.sleep(1)

        print(f"\n📊 Total: {len(all_results)} listings | {skipped} skipped")
        return pd.DataFrame(all_results)

    # 8. EXECUTE
    print("🚀 Starting Enhanced Ireland-Wide Sauna Extraction...")
    print(f"📝 Total queries: {len(QUERIES)}")
    df = fetch_places(QUERIES)

    # 9. SAVE & DOWNLOAD
    if not df.empty:
        # Remove duplicates and sort
        df = df.drop_duplicates(subset=['place_id'], keep='first')
        df = df.sort_values(['rating', 'reviews_count'], ascending=[False, False], na_position='last')
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Full dataset
        csv_full = f"sauna_data_enhanced_{timestamp}.csv"
        df.to_csv(csv_full, index=False)
        print(f"\n✅ Full dataset: {csv_full}")
        
        # Import-ready
        df_import = df[[
            'name', 'place_id', 'city', 'county', 'address',
            'website', 'phone', 'rating', 'reviews_count', 'photo_ref',
            'heat_source', 'cold_plunge', 'outdoor', 'private_rooms'
        ]].copy()
        csv_import = f"sauna_import_ready_{timestamp}.csv"
        df_import.to_csv(csv_import, index=False)
        print(f"✅ Import-ready: {csv_import}")
        
        print(f"\n🎉 SUCCESS!")
        print(f"   Total listings: {len(df)}")
        print(f"   Counties: {df['county'].nunique()}")
        
        files.download(csv_full)
        files.download(csv_import)
    else:
        print("\n⚠️ No results found.")