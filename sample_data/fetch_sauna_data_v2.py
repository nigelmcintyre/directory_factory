#!/usr/bin/env python3
"""
Enhanced Sauna Data Scraper v2 - Local Version with Quality Filtering
Fetches high-quality sauna listings from Google Maps API for Ireland
"""

import googlemaps
import pandas as pd
import time
import os
import sys
from datetime import datetime
from pathlib import Path

# Get API key from environment or Django settings
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Try to get from environment first
API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')

# If not in env, try to load from Django settings
if not API_KEY:
    sys.path.insert(0, str(PROJECT_ROOT))
    try:
        from directory_factory.settings import GOOGLE_MAPS_API_KEY
        API_KEY = GOOGLE_MAPS_API_KEY
    except:
        pass

if not API_KEY:
    print("❌ ERROR: GOOGLE_MAPS_API_KEY not found!")
    print("Set it in one of these ways:")
    print("  1. Environment: export GOOGLE_MAPS_API_KEY='your-key'")
    print("  2. Django settings.py already has it")
    sys.exit(1)

# Initialize client
gmaps = googlemaps.Client(key=API_KEY)

# County/City mapping for better location extraction
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


def generate_queries():
    """Generate focused search queries"""
    queries = []
    for county in COUNTIES.keys():
        queries.extend([
            f"Sauna in Co. {county}, Ireland",
            f"Sea Swimming Sauna Co. {county}",
            f"Mobile Sauna {county}",
            f"Outdoor Sauna {county}"
        ])
    
    queries.extend([
        "Barrel sauna Ireland",
        "Sea sauna Ireland",
        "Cold plunge sauna Ireland",
        "Wood fired sauna Ireland",
        "Finnish sauna Ireland",
        "Sauna Dublin City",
        "Sauna Cork City",
        "Sauna Galway City"
    ])
    
    return queries


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


def fetch_places_enhanced(queries):
    """Main fetch function with quality filtering"""
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
                        fields=[
                            'name', 'formatted_address', 'geometry', 'website',
                            'formatted_phone_number', 'rating', 'user_ratings_total',
                            'reviews', 'type', 'editorial_summary', 'photo',
                            'business_status'
                        ]
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
                        'reviews_text': reviews_text,
                        'fetched_at': datetime.now().isoformat()
                    }
                    
                    all_results.append(flat_data)
                    results_count += 1
                    print(f"   ✅ {flat_data['name']} ({city}, {county})")
                    
                except Exception as e:
                    print(f"   ❌ Error for {name}: {e}")
                    continue
            
            # Handle pagination
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


def main():
    """Main execution"""
    print("🚀 Starting Enhanced Ireland-Wide Sauna Extraction v2...")
    print(f"📍 API Key found: {API_KEY[:10]}...{API_KEY[-4:]}")
    
    # Generate queries
    queries = generate_queries()
    print(f"📝 Total queries: {len(queries)}")
    
    # Fetch data
    df = fetch_places_enhanced(queries)
    
    if df.empty:
        print("\n⚠️ No results found.")
        return
    
    # Remove duplicates and sort
    df = df.drop_duplicates(subset=['place_id'], keep='first')
    df = df.sort_values(['rating', 'reviews_count'], ascending=[False, False], na_position='last')
    
    # Save files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = SCRIPT_DIR
    
    # Full dataset
    csv_full = output_dir / f"sauna_data_enhanced_v2_{timestamp}.csv"
    df.to_csv(csv_full, index=False)
    print(f"\n✅ Full dataset saved: {csv_full}")
    
    # Django import-ready format
    df_import = df[[
        'name', 'place_id', 'city', 'county', 'address',
        'website', 'phone', 'rating', 'reviews_count', 'photo_ref',
        'heat_source', 'cold_plunge', 'outdoor', 'private_rooms'
    ]].copy()
    csv_import = output_dir / f"sauna_import_ready_v2_{timestamp}.csv"
    df_import.to_csv(csv_import, index=False)
    print(f"✅ Import-ready dataset: {csv_import}")
    
    # Summary
    print(f"\n🎉 SUCCESS!")
    print(f"   Total listings: {len(df)}")
    print(f"   Counties covered: {df['county'].nunique()}")
    print(f"   Categories: {dict(df['category'].value_counts())}")
    
    # Data quality stats
    missing_phone = df[df['phone'].isna() | (df['phone'] == '')].shape[0]
    missing_website = df[df['website'].isna() | (df['website'] == '')].shape[0]
    avg_rating = df['rating'].mean()
    print(f"\n📊 Quality Stats:")
    print(f"   Missing phone: {missing_phone}")
    print(f"   Missing website: {missing_website}")
    print(f"   Average rating: {avg_rating:.2f}")
    
    print(f"\n📦 Next step: Import with:")
    print(f"   python manage.py import_google_places {csv_import.name}")


if __name__ == "__main__":
    main()
