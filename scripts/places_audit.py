"""Compare listings with Google Places and look for saunas that aren't listed yet.

Read-only: writes CSVs to --out and never touches the database.
GOOGLE_MAPS_API_KEY and DATABASE_URL come from the environment or .env.local.
Responses are cached in <out>/cache.json so a re-run isn't billed again; delete it to refetch.

.venv/bin/python scripts/places_audit.py [verify|discover] [--limit N] [--out DIR]
"""
import argparse
import collections
import csv
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

import psycopg2
import psycopg2.extras
import requests

ROOT = Path(__file__).resolve().parent.parent
API = "https://places.googleapis.com/v1"

# Phone, website, rating and hours put both calls in the Enterprise SKU.
FIELDS = [
    "id", "displayName", "formattedAddress", "businessStatus", "location", "types", "primaryType",
    "googleMapsUri", "nationalPhoneNumber", "websiteUri", "rating", "userRatingCount",
    "regularOpeningHours.weekdayDescriptions",
]

ISLAND_OF_IRELAND = {
    "rectangle": {
        "low": {"latitude": 51.35, "longitude": -10.7},
        "high": {"latitude": 55.45, "longitude": -5.35},
    }
}

COUNTIES = [
    "Antrim", "Armagh", "Carlow", "Cavan", "Clare", "Cork", "Derry", "Donegal", "Down", "Dublin",
    "Fermanagh", "Galway", "Kerry", "Kildare", "Kilkenny", "Laois", "Leitrim", "Limerick",
    "Longford", "Louth", "Mayo", "Meath", "Monaghan", "Offaly", "Roscommon", "Sligo", "Tipperary",
    "Tyrone", "Waterford", "Westmeath", "Wexford", "Wicklow",
]
NATIONAL_QUERIES = [
    "Barrel sauna Ireland", "Sea sauna Ireland", "Cold plunge sauna Ireland",
    "Wood fired sauna Ireland", "Finnish sauna Ireland",
    "Sauna Dublin City", "Sauna Cork City", "Sauna Galway City",
]

SAUNA_KEYWORDS = ["sauna", "saunos", "sweathouse", "sweat house", "sea swimming", "cold plunge"]
EXCLUDE_KEYWORDS = [
    "builder", "construction", "supplier", "manufactur", "sauna shop", "sauna store", "aesthetic",
    "beauty bar", "beauty salon", "beauty_salon", "hair_care", "nails", "lashes", "botox", "filler",
    "laser", "waxing", "massage therapist", "chiropractor", "physiotherap", "dealer", "distributor",
    "installer", "installation", "for sale", "restaurant", "grocery", "repair",
]

FIELD_ORDER = [
    "not_found", "business_status", "place_id", "name", "address", "location", "phone", "website",
    "opening_hours", "rating", "reviews_count",
]
MOVED_THRESHOLD_DEGREES = 0.003  # roughly 300 m


def load_env_local():
    path = ROOT / ".env.local"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        key, sep, value = line.partition("=")
        if sep and not key.startswith("#"):
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def fetch_listings():
    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, slug, name, address, phone, website, rating, reviews_count, place_id,
                       latitude, longitude, is_active, attributes->>'opening_hours' AS opening_hours
                FROM directory_listing
                ORDER BY id
                """
            )
            return cur.fetchall()


class Places:
    def __init__(self, key, cache_path):
        self.session = requests.Session()
        self.session.headers["X-Goog-Api-Key"] = key
        self.cache_path = cache_path
        self.cache = json.loads(cache_path.read_text()) if cache_path.exists() else {"details": {}, "search": {}}
        self.billed = collections.Counter()

    def save(self):
        self.cache_path.write_text(json.dumps(self.cache))

    def _json(self, response):
        if not response.ok:
            raise RuntimeError(f"{response.status_code} from {response.url}: {response.text}")
        return response.json()

    def details(self, place_id):
        if place_id not in self.cache["details"]:
            response = self.session.get(
                f"{API}/places/{place_id}",
                headers={"X-Goog-FieldMask": ",".join(FIELDS)},
                params={"languageCode": "en"},
                timeout=30,
            )
            self.billed["details"] += 1
            self.cache["details"][place_id] = None if response.status_code == 404 else self._json(response)
        return self.cache["details"][place_id]

    def search(self, query):
        if query not in self.cache["search"]:
            body = {
                "textQuery": query,
                "pageSize": 20,
                "languageCode": "en",
                "regionCode": "IE",
                "locationRestriction": ISLAND_OF_IRELAND,
            }
            places = []
            while True:
                response = self.session.post(
                    f"{API}/places:searchText",
                    headers={"X-Goog-FieldMask": ",".join(["nextPageToken"] + [f"places.{f}" for f in FIELDS])},
                    json=body,
                    timeout=30,
                )
                self.billed["search"] += 1
                data = self._json(response)
                places += data.get("places", [])
                if "nextPageToken" not in data:
                    break
                body["pageToken"] = data["nextPageToken"]
            self.cache["search"][query] = places
        return self.cache["search"][query]


def squash(text):
    return " ".join(text.split())


def text_key(text):
    return squash(text).casefold()


def phone_key(phone):
    return re.sub(r"^(00)?(353|44)", "0", re.sub(r"\D", "", phone))


def website_key(url):
    parts = urlsplit(url if "//" in url else f"//{url}")
    return parts.netloc.lower().removeprefix("www.") + parts.path.rstrip("/")


def opening_hours(place):
    return "|".join(squash(day) for day in place.get("regularOpeningHours", {}).get("weekdayDescriptions", []))


def listing_changes(listing, place):
    changes = []
    if place["id"] != listing["place_id"]:
        changes.append(("place_id", listing["place_id"], place["id"]))
    status = place.get("businessStatus", "OPERATIONAL")
    if status != "OPERATIONAL":
        changes.append(("business_status", "OPERATIONAL", status))

    location = place.get("location")
    if location:
        current = (listing["latitude"], listing["longitude"])
        google = (location["latitude"], location["longitude"])
        if None in current or max(abs(a - b) for a, b in zip(current, google)) > MOVED_THRESHOLD_DEGREES:
            changes.append(("location", "" if None in current else "{},{}".format(*current), "{},{}".format(*google)))

    comparisons = [
        ("name", listing["name"], place["displayName"]["text"], text_key),
        ("address", listing["address"], place.get("formattedAddress"), text_key),
        ("phone", listing["phone"], place.get("nationalPhoneNumber"), phone_key),
        ("website", listing["website"], place.get("websiteUri"), website_key),
        ("opening_hours", listing["opening_hours"], opening_hours(place), squash),
        ("rating", listing["rating"], place.get("rating"), float),
        ("reviews_count", listing["reviews_count"], place.get("userRatingCount"), int),
    ]
    # A field Google has no value for is never a change: ours may have been entered by hand.
    for field, current, google, key in comparisons:
        if google in ("", None):
            continue
        if current in ("", None) or key(current) != key(google):
            changes.append((field, current or "", google))
    return changes


def verify(listings, places, out, limit):
    rows = []
    active = [listing for listing in listings if listing["is_active"]][:limit]
    for n, listing in enumerate(active, 1):
        print(f"[{n}/{len(active)}] {listing['name']}", file=sys.stderr)
        note = ""
        if listing["place_id"]:
            place = places.details(listing["place_id"])
        else:
            results = places.search(f"{listing['name']}, {listing['address']}")
            wanted = text_key(listing["name"])
            place = next(
                (p for p in results if wanted in text_key(p["displayName"]["text"])),
                results[0] if results else None,
            )
            if place:
                note = f"matched by name search: {place['displayName']['text']}, {place.get('formattedAddress', '')}"
        changes = listing_changes(listing, place) if place else [("not_found", listing["place_id"], "")]
        rows += [
            {"id": listing["id"], "slug": listing["slug"], "name": listing["name"], "field": field,
             "current": current, "google": google, "note": note}
            for field, current, google in changes
        ]
    rows.sort(key=lambda row: (FIELD_ORDER.index(row["field"]), row["id"]))
    write_csv(out / "listing_changes.csv", ["id", "slug", "name", "field", "current", "google", "note"], rows)
    summary = collections.Counter(row["field"] for row in rows)
    print(f"Verified {len(active)} listings: {dict(summary)}", file=sys.stderr)


def looks_like_sauna(place):
    name = place["displayName"]["text"].lower()
    types = place.get("types", [])
    text = " ".join([name, place.get("websiteUri", "").lower(), *types])
    if place.get("businessStatus") == "CLOSED_PERMANENTLY" or any(k in text for k in EXCLUDE_KEYWORDS):
        return False
    return "sauna" in types or any(k in name for k in SAUNA_KEYWORDS)


def discover(listings, places, out, limit):
    queries = [
        query
        for county in COUNTIES
        for query in (
            f"Sauna in Co. {county}, Ireland",
            f"Sea Swimming Sauna Co. {county}",
            f"Mobile Sauna {county}",
            f"Outdoor Sauna {county}",
        )
    ] + NATIONAL_QUERIES
    queries = queries[:limit]

    found = {}
    for n, query in enumerate(queries, 1):
        print(f"[{n}/{len(queries)}] {query}", file=sys.stderr)
        for place in places.search(query):
            found.setdefault(place["id"], (place, []))[1].append(query)

    known_ids = {listing["place_id"] for listing in listings}
    # Listings without a place_id can only be recognised by name.
    unlinked_names = {text_key(listing["name"]) for listing in listings if not listing["place_id"]}
    rows = []
    for place, matched_queries in found.values():
        name = place["displayName"]["text"]
        if place["id"] in known_ids or text_key(name) in unlinked_names or not looks_like_sauna(place):
            continue
        location = place.get("location", {})
        rows.append({
            "place_id": place["id"],
            "name": name,
            "address": place.get("formattedAddress", ""),
            "phone": place.get("nationalPhoneNumber", ""),
            "website": place.get("websiteUri", ""),
            "rating": place.get("rating", ""),
            "reviews_count": place.get("userRatingCount", ""),
            "business_status": place.get("businessStatus", ""),
            "primary_type": place.get("primaryType", ""),
            "types": " ".join(place.get("types", [])),
            "opening_hours": opening_hours(place),
            "latitude": location.get("latitude", ""),
            "longitude": location.get("longitude", ""),
            "google_maps_url": place.get("googleMapsUri", ""),
            "queries": len(matched_queries),
        })
    rows.sort(key=lambda row: -(row["reviews_count"] or 0))
    write_csv(out / "new_candidates.csv", list(rows[0]) if rows else ["place_id"], rows)
    print(f"{len(found)} places found, {len(rows)} new candidates", file=sys.stderr)


def write_csv(path, fieldnames, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {path}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("step", nargs="?", choices=["verify", "discover"], help="default: both")
    parser.add_argument("--limit", type=int, help="only the first N listings / search queries")
    parser.add_argument("--out", type=Path, default=ROOT / "places_audit")
    args = parser.parse_args()

    load_env_local()
    listings = fetch_listings()
    args.out.mkdir(exist_ok=True)
    places = Places(os.environ["GOOGLE_MAPS_API_KEY"], args.out / "cache.json")
    try:
        if args.step != "discover":
            verify(listings, places, args.out, args.limit)
        if args.step != "verify":
            discover(listings, places, args.out, args.limit)
    finally:
        places.save()
        print(f"Billed requests this run: {dict(places.billed)}", file=sys.stderr)


if __name__ == "__main__":
    main()
