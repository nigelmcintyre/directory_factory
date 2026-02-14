SITE_NAME = "Sauna Guide"
DOMAIN = "saunaguide.ie"

FILTERS = [
    {
        "key": "county",
        "label": "County",
        "type": "choice",
        "choices": ["Dublin", "Cork", "Kerry", "Galway", "Donegal", "Limerick", "Wicklow", "Mayo", "Clare", "Sligo"],
        "field_type": "model",
    },
    {
        "key": "rating",
        "label": "Minimum Rating",
        "type": "choice",
        "choices": ["4.5+", "4.0+", "3.5+", "Any"],
        "field_type": "model",
    },
    {
        "key": "has_website",
        "label": "Has Website",
        "type": "boolean",
        "field_type": "model",
    },
    {
        "key": "has_phone",
        "label": "Has Phone",
        "type": "boolean",
        "field_type": "model",
    },
    {
        "key": "heat_source",
        "label": "Heat Source",
        "type": "choice",
        "choices": ["Wood", "Electric", "Infrared", "Not Listed"],
    },
    {
        "key": "cold_plunge",
        "label": "Cold Plunge",
        "type": "choice",
        "choices": ["Yes", "No", "Not Listed"],
    },
    {
        "key": "changing_facilities",
        "label": "Changing Facilities",
        "type": "choice",
        "choices": ["Yes", "No", "Not Listed"],
    },
    {
        "key": "showers",
        "label": "Showers",
        "type": "choice",
        "choices": ["Yes", "No", "Not Listed"],
    },
    {
        "key": "sea_view",
        "label": "Sea View",
        "type": "choice",
        "choices": ["Yes", "No", "Not Listed"],
    },
    {
        "key": "dog_friendly",
        "label": "Dog Friendly",
        "type": "choice",
        "choices": ["Yes", "No", "Not Listed"],
    },
]
