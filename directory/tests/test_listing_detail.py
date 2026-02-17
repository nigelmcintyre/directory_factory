from django.test import TestCase
from django.urls import reverse

from directory.models import Listing


def _create_listing(*, name, slug, city, county=""):
    return Listing.objects.create(
        name=name,
        slug=slug,
        city=city,
        county=county,
        description="",
        address="",
        website="",
        phone="",
    )


class ListingDetailRelatedListingsTests(TestCase):
    def test_listing_detail_uses_county_then_city_fallback(self):
        primary = _create_listing(
            name="Sauna One",
            slug="sauna-one",
            city="Dublin",
            county="Dublin",
        )
        county_match = _create_listing(
            name="Sauna Two",
            slug="sauna-two",
            city="Dublin",
            county="Dublin",
        )
        city_fallback = _create_listing(
            name="Sauna Three",
            slug="sauna-three",
            city="Dublin",
            county="",
        )

        response = self.client.get(
            reverse("listing_detail", kwargs={"slug": primary.slug})
        )

        self.assertEqual(response.status_code, 200)
        related = response.context["related_listings"]
        related_slugs = {listing.slug for listing in related}
        self.assertIn(county_match.slug, related_slugs)
        self.assertIn(city_fallback.slug, related_slugs)

    def test_listing_detail_without_county_uses_city(self):
        primary = _create_listing(
            name="Sauna A",
            slug="sauna-a",
            city="Galway",
            county="",
        )
        city_match = _create_listing(
            name="Sauna B",
            slug="sauna-b",
            city="Galway",
            county="",
        )

        response = self.client.get(
            reverse("listing_detail", kwargs={"slug": primary.slug})
        )

        self.assertEqual(response.status_code, 200)
        related = response.context["related_listings"]
        related_slugs = {listing.slug for listing in related}
        self.assertIn(city_match.slug, related_slugs)


class CountyRedirectTests(TestCase):
    def test_county_redirect_preserves_multi_select_filters(self):
        url = (
            reverse("pseo_landing", kwargs={"county": "dublin"})
            + "?county=Cork&heat_source=wood&heat_source=electric&dog_friendly=yes"
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"],
            "/cork/?heat_source=wood&heat_source=electric&dog_friendly=yes",
        )
