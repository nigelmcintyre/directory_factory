import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

CLICK_TYPES = ["website", "booking", "social", "phone", "directions", "review"]

SOCIAL_HOSTS = re.compile(r"(^|\.)(instagram\.com|facebook\.com|fb\.com|tiktok\.com|linktr\.ee)$")
BOOKING_HOSTS = re.compile(
    r"(^|\.)(calendly\.com|as\.me|acuityscheduling\.com|bookwhen\.com|wunderbook\.(app|link|com)|fresha\.com"
    r"|setmore\.com|buk\.ie|booksy\.com|gettimely\.com|bookeo\.com|checkfront\.com|simplybook\.\w+|eventbrite\.\w+"
    r"|easyweek\.ie|rezgo\.com|fadsaoil\.app|saunaspot\.ie)$"
)
UTM_PARAMS = {"utm_source": "saunaguide.ie", "utm_medium": "referral", "utm_campaign": "listing"}


def link_type(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower()
    if SOCIAL_HOSTS.search(host):
        return "social"
    if BOOKING_HOSTS.search(host):
        return "booking"
    return "website"


def with_utm(url: str) -> str:
    """Tag outbound links so owners can see saunaguide.ie traffic in their own analytics."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or link_type(url) == "social":
        return url
    query = parse_qsl(parts.query, keep_blank_values=True)
    existing = {key for key, _ in query}
    query += [(key, value) for key, value in UTM_PARAMS.items() if key not in existing]
    return urlunsplit(parts._replace(query=urlencode(query)))
