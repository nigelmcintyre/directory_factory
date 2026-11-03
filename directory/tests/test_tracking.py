"""Per-listing views, impressions and outbound clicks."""

import json
from datetime import date
from io import StringIO

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from directory.links import link_type, with_utm
from directory.models import Listing, ListingDailyStat

BROWSER_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)"


def _make_listing(**overrides):
    defaults = dict(name="Test Sauna", slug="test-sauna", city="Ennis", county="Clare")
    defaults.update(overrides)
    return Listing.objects.create(**defaults)


class LinkTests(SimpleTestCase):
    def test_link_type(self):
        self.assertEqual(link_type("https://www.instagram.com/wonkysauna.howth"), "social")
        self.assertEqual(link_type("https://linktr.ee/sauna"), "social")
        self.assertEqual(link_type("https://hylosaunasbooking.as.me/"), "booking")
        self.assertEqual(link_type("https://lakesidesaunas.simplybook.it/v2/"), "booking")
        self.assertEqual(link_type("http://buk.ie/twr"), "booking")
        self.assertEqual(link_type("https://thehotboxsauna.ie/"), "website")

    def test_with_utm_preserves_query_and_fragment(self):
        self.assertEqual(
            with_utm("https://example.ie/book?loc=1#slots"),
            "https://example.ie/book?loc=1&utm_source=saunaguide.ie&utm_medium=referral&utm_campaign=listing#slots",
        )

    def test_with_utm_keeps_existing_utm_values(self):
        self.assertIn("utm_source=other", with_utm("https://example.ie/?utm_source=other"))
        self.assertEqual(with_utm("https://example.ie/?utm_source=other").count("utm_source"), 1)

    def test_with_utm_skips_social(self):
        url = "https://www.instagram.com/wonkysauna.howth"
        self.assertEqual(with_utm(url), url)


class TrackEndpointTests(TestCase):
    def setUp(self):
        self.listing = _make_listing()

    def _post(self, events, user_agent=BROWSER_UA):
        return self.client.post(
            reverse("track_listing_events"),
            json.dumps({"events": events}),
            content_type="text/plain",
            HTTP_USER_AGENT=user_agent,
        )

    def _counts(self):
        return dict(ListingDailyStat.objects.values_list("metric", "count"))

    def test_counts_accumulate_per_metric(self):
        events = [
            {"listing_id": self.listing.id, "metric": "impression"},
            {"listing_id": self.listing.id, "metric": "impression"},
            {"listing_id": self.listing.id, "metric": "click_booking"},
        ]

        self.assertEqual(self._post(events).status_code, 204)
        self._post(events[:1])

        self.assertEqual(self._counts(), {"impression": 3, "click_booking": 1})
        self.assertEqual(ListingDailyStat.objects.get(metric="impression").date, timezone.now().date())

    def test_ignores_unknown_metrics_and_inactive_or_missing_listings(self):
        inactive = _make_listing(slug="closed", is_active=False)

        self._post([
            {"listing_id": self.listing.id, "metric": "click_hack"},
            {"listing_id": inactive.id, "metric": "view"},
            {"listing_id": 999999, "metric": "view"},
        ])

        self.assertFalse(ListingDailyStat.objects.exists())

    def test_bots_are_not_counted(self):
        response = self._post(
            [{"listing_id": self.listing.id, "metric": "view"}],
            user_agent="Mozilla/5.0 (compatible; Googlebot/2.1)",
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(ListingDailyStat.objects.exists())

    def test_caps_events_per_beacon(self):
        self._post([{"listing_id": self.listing.id, "metric": "impression"}] * 500)

        self.assertEqual(self._counts(), {"impression": 50})

    def test_malformed_payload_is_rejected(self):
        for body in ["not json", "[]", json.dumps({"events": [{"metric": "view"}]})]:
            response = self.client.post(
                reverse("track_listing_events"), body, content_type="text/plain", HTTP_USER_AGENT=BROWSER_UA
            )
            self.assertEqual(response.status_code, 400, body)

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(reverse("track_listing_events")).status_code, 405)


class TemplateMarkupTests(TestCase):
    def test_detail_and_card_links_are_tagged(self):
        listing = _make_listing(website="https://hylosaunasbooking.as.me/", phone="087 000 0000")

        detail = self.client.get(reverse("listing_detail", args=[listing.slug])).content.decode()
        card = self.client.get(reverse("pseo_landing", args=["clare"])).content.decode()

        self.assertIn(f'data-listing-id="{listing.id}"', detail)
        self.assertIn('data-placement="detail"', detail)
        self.assertIn('data-placement="card"', card)
        for html in (detail, card):
            self.assertIn('href="https://hylosaunasbooking.as.me/?utm_source=saunaguide.ie', html)
            self.assertIn('data-click-type="booking"', html)
            self.assertIn('data-click-type="phone"', html)


class ListingReportTests(TestCase):
    def test_pivots_one_month(self):
        listing = _make_listing(is_featured=True)
        other = _make_listing(name="Other", slug="other")
        ListingDailyStat.objects.create(listing=listing, date=date(2026, 11, 2), metric="view", count=10)
        ListingDailyStat.objects.create(listing=listing, date=date(2026, 11, 30), metric="click_booking", count=4)
        ListingDailyStat.objects.create(listing=listing, date=date(2026, 11, 3), metric="click_phone", count=1)
        ListingDailyStat.objects.create(listing=listing, date=date(2026, 12, 1), metric="view", count=99)
        ListingDailyStat.objects.create(listing=other, date=date(2026, 11, 5), metric="impression", count=3)

        out = StringIO()
        call_command("listing_report", month="2026-11", stdout=out)

        lines = out.getvalue().splitlines()
        self.assertEqual(
            lines[0],
            "slug,name,county,is_featured,view,impression,click_website,click_booking,click_social,"
            "click_phone,click_directions,click_review,total_clicks",
        )
        self.assertEqual(lines[1], "test-sauna,Test Sauna,Clare,1,10,0,0,4,0,1,0,0,5")
        self.assertEqual(lines[2], "other,Other,Clare,0,0,3,0,0,0,0,0,0,0")
