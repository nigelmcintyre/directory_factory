from typing import Optional, Tuple, Dict, Any, List, Union
from math import radians, cos, sin, asin, sqrt
from django.db.models import Q, QuerySet
from .models import Listing
from .niche_config import FILTERS


def _normalize_bool(value: Optional[str]) -> Optional[bool]:
    if value is None:
        return None
    value = value.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return None


def _parse_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    value = str(value).strip()
    if not value or value.lower() in {"nan", "none"}:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    # Haversine formula to compute great-circle distance in km.
    radius_km = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return radius_km * c


def get_filtered_listings(request) -> Tuple[Union[QuerySet[Listing], List[Listing]], Dict[str, Any]]:
    queryset = Listing.objects.filter(is_active=True)

    for definition in FILTERS:
        key = definition.get("key")
        filter_type = definition.get("type", "choice")
        field_type = definition.get("field_type", "attribute")  # Default to attribute filtering
        
        if not key:
            continue

        # Handle model field filters (not in attributes JSON)
        if field_type == "model":
            if key == "county":
                raw_value = request.GET.get(key)
                if raw_value:
                    queryset = queryset.filter(county__iexact=raw_value)
            elif key == "rating":
                raw_value = request.GET.get(key)
                if raw_value and raw_value != "Any":
                    # Extract minimum rating (e.g., "4.5+" -> 4.5)
                    try:
                        min_rating = float(raw_value.rstrip("+"))
                        queryset = queryset.filter(rating__gte=min_rating)
                    except (ValueError, AttributeError):
                        pass
            elif key == "has_website":
                raw_value = request.GET.get(key)
                bool_value = _normalize_bool(raw_value)
                if bool_value is True:
                    queryset = queryset.exclude(website="")
            elif key == "has_phone":
                raw_value = request.GET.get(key)
                bool_value = _normalize_bool(raw_value)
                if bool_value is True:
                    queryset = queryset.exclude(phone="")
            continue

        # Handle attribute field filters (JSON field)
        if filter_type == "boolean":
            raw_value = request.GET.get(key)
            bool_value = _normalize_bool(raw_value)
            if bool_value is None:
                continue
            queryset = queryset.filter(**{f"attributes__{key}": bool_value})
            continue

        values = [value for value in request.GET.getlist(key) if value]
        if not values:
            single_value = request.GET.get(key)
            if single_value:
                values = [single_value]

        if not values:
            continue

        if len(values) == 1:
            queryset = queryset.filter(**{f"attributes__{key}__iexact": values[0]})
        else:
            query = Q()
            for value in values:
                query |= Q(**{f"attributes__{key}__iexact": value})
            queryset = queryset.filter(query)

    # Sorting
    sort_by = request.GET.get("sort", "featured")
    
    if sort_by == "rating":
        # Featured first, then highest rating, then most reviews
        queryset = queryset.order_by('-is_featured', '-rating', '-reviews_count')
    elif sort_by == "name":
        queryset = queryset.order_by('-is_featured', 'name')
    else:
        # Default: Featured first, then name
        queryset = queryset.order_by('-is_featured', 'name')

    near_me = _normalize_bool(request.GET.get("near_me")) is True
    user_lat = _parse_float(request.GET.get("lat"))
    user_lng = _parse_float(request.GET.get("lng"))
    distance_km = _parse_float(request.GET.get("distance_km")) or 50.0

    if near_me and user_lat is not None and user_lng is not None:
        candidates = queryset.exclude(latitude__isnull=True).exclude(longitude__isnull=True)
        results: List[Listing] = []
        for listing in candidates:
            if listing.latitude is None or listing.longitude is None:
                continue
            distance = _haversine_km(user_lat, user_lng, listing.latitude, listing.longitude)
            if distance <= distance_km:
                listing.distance_km = round(distance, 1)
                results.append(listing)
        
        # Sort the in-memory list
        if sort_by == "distance":
             # Sort by distance (ASC)
             results.sort(key=lambda item: (not item.is_featured, getattr(item, "distance_km", 9999)))
        elif sort_by == "rating":
             # Sort by rating (DESC)
             results.sort(key=lambda item: (not item.is_featured, -(float(item.rating or 0))))
        else:
             # Default sort (Featured first, then distance or name)
             # If strictly featured, maybe distance secondary?
             results.sort(key=lambda item: (not item.is_featured, getattr(item, "distance_km", 9999)))

        return results, {
            "near_me": True,
            "user_lat": user_lat,
            "user_lng": user_lng,
            "distance_km": distance_km,
        }

    return queryset, {
        "near_me": False,
        "user_lat": user_lat,
        "user_lng": user_lng,
        "distance_km": distance_km,
    }
