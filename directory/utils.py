from typing import Optional
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


def get_filtered_listings(request) -> QuerySet[Listing]:
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

    return queryset
