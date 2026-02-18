from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from directory.models import Listing, SaunaSubmission


def _create_listing(**kwargs):
    defaults = {
        "name": "Test Sauna",
        "slug": "test-sauna",
        "city": "Dublin",
        "county": "Dublin",
        "description": "",
        "address": "",
        "website": "",
        "phone": "",
        "rating": None,
        "reviews_count": None,
        "latitude": None,
        "longitude": None,
        "is_featured": False,
    }
    defaults.update(kwargs)
    return Listing.objects.create(**defaults)


class HomePageTests(TestCase):
    def test_home_page_returns_200(self):
        _create_listing(slug="home-listing")
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    def test_home_sort_by_rating_orders_desc(self):
        low = _create_listing(
            name="Low Rated",
            slug="low-rated",
            rating=Decimal("3.2"),
            reviews_count=10,
        )
        high = _create_listing(
            name="High Rated",
            slug="high-rated",
            rating=Decimal("4.8"),
            reviews_count=5,
        )

        response = self.client.get(reverse("home"), {"sort": "rating"})
        self.assertEqual(response.status_code, 200)
        listings = list(response.context["listings"])
        self.assertEqual(listings[0].id, high.id)
        self.assertEqual(listings[1].id, low.id)

    def test_home_sort_by_name_orders_asc(self):
        first = _create_listing(name="A Sauna", slug="a-sauna")
        second = _create_listing(name="B Sauna", slug="b-sauna")

        response = self.client.get(reverse("home"), {"sort": "name"})
        self.assertEqual(response.status_code, 200)
        listings = list(response.context["listings"])
        self.assertEqual(listings[0].id, first.id)
        self.assertEqual(listings[1].id, second.id)

    def test_home_sort_by_distance_orders_nearest(self):
        nearest = _create_listing(
            name="Nearest",
            slug="nearest",
            latitude=53.0,
            longitude=-6.0,
        )
        farther = _create_listing(
            name="Farther",
            slug="farther",
            latitude=54.0,
            longitude=-6.0,
        )

        response = self.client.get(
            reverse("home"),
            {
                "near_me": "1",
                "lat": "53.0",
                "lng": "-6.0",
                "distance_km": "200",
                "sort": "distance",
            },
        )
        self.assertEqual(response.status_code, 200)
        listings = response.context["listings"]
        self.assertIsInstance(listings, list)
        self.assertEqual(listings[0].id, nearest.id)
        self.assertEqual(listings[1].id, farther.id)


class SubmissionTests(TestCase):
    def test_submit_sauna_post_creates_submission(self):
        payload = {
            "name": "New Sauna",
            "city": "Dublin",
            "county": "Dublin",
            "address": "",
            "website": "",
            "phone": "",
            "description": "A test submission",
            "heat_source": "wood",
            "cold_plunge": "not listed",
            "dog_friendly": "not listed",
            "showers": "not listed",
            "changing_facilities": "not listed",
            "sea_view": "not listed",
            "opening_hours": "",
            "submitter_name": "Tester",
            "submitter_email": "tester@example.com",
        }

        response = self.client.post(reverse("submit_sauna"), payload)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(SaunaSubmission.objects.count(), 1)


class ListingDetailTests(TestCase):
    def test_listing_detail_handles_empty_google_reviews(self):
        listing = _create_listing(slug="no-reviews")

        response = self.client.get(
            reverse("listing_detail", kwargs={"slug": listing.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["google_reviews"], [])


class MetadataEndpointTests(TestCase):
    def test_robots_and_sitemap_return_200(self):
        robots = self.client.get(reverse("robots_txt"))
        self.assertEqual(robots.status_code, 200)
        self.assertIn("Sitemap:", robots.content.decode("utf-8"))

        sitemap = self.client.get(
            reverse("django.contrib.sitemaps.views.sitemap")
        )
        self.assertEqual(sitemap.status_code, 200)
