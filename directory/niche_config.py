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
        "key": "heat_source",
        "label": "Heat Source",
        "type": "choice",
        "choices": ["wood", "electric", "infrared", "not listed"],
    },
    {
        "key": "cold_plunge",
        "label": "Cold Plunge",
        "type": "choice",
        "choices": ["yes", "no", "not listed"],
    },
    {
        "key": "changing_facilities",
        "label": "Changing Facilities",
        "type": "choice",
        "choices": ["yes", "no", "not listed"],
    },
    {
        "key": "showers",
        "label": "Showers",
        "type": "choice",
        "choices": ["yes", "no", "not listed"],
    },
    {
        "key": "sea_view",
        "label": "Sea View",
        "type": "choice",
        "choices": ["yes", "no", "not listed"],
    },
    {
        "key": "dog_friendly",
        "label": "Dog Friendly",
        "type": "choice",
        "choices": ["yes", "no", "not listed"],
    },
]
