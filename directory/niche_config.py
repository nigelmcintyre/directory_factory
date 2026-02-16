SITE_NAME = "Sauna Guide"
DOMAIN = "saunaguide.ie"

FILTERS = [
    {
        "key": "county",
        "label": "County",
        "type": "choice",
        "choices": [
            # Republic of Ireland - 26 counties
            "Carlow", "Cavan", "Clare", "Cork", "Donegal", "Dublin", "Galway",
            "Kerry", "Kildare", "Kilkenny", "Laois", "Leitrim", "Limerick",
            "Longford", "Louth", "Mayo", "Meath", "Monaghan", "Offaly",
            "Roscommon", "Sligo", "Tipperary", "Waterford", "Westmeath",
            "Wexford", "Wicklow",
            # Northern Ireland - 6 counties
            "Antrim", "Armagh", "Derry", "Down", "Fermanagh", "Tyrone",
        ],
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
