import base64

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
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


class ListingPhotoTests(TestCase):
    def setUp(self):
        self.photo_bytes = b"RIFF\x00\x00\x00\x00WEBPVP8 fake"
        self.with_photo = _create_listing(name="Photo Sauna", slug="photo-sauna", city="Cork", county="Cork")
        self.with_photo.photo_data = base64.b64encode(self.photo_bytes).decode()
        self.with_photo.save()
        self.without_photo = _create_listing(name="Bare Sauna", slug="bare-sauna", city="Cork", county="Cork")

    def test_photo_view_serves_decoded_webp_with_cdn_cache(self):
        response = self.client.get(reverse("listing_photo", args=["photo-sauna"]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/webp")
        self.assertEqual(response.content, self.photo_bytes)
        self.assertIn("s-maxage", response["Cache-Control"])

    def test_photo_view_404s_without_photo(self):
        response = self.client.get(reverse("listing_photo", args=["bare-sauna"]))

        self.assertEqual(response.status_code, 404)

    def test_pages_link_photos_instead_of_inlining_them(self):
        photo_url = reverse("listing_photo", args=["photo-sauna"])
        for url in [reverse("home"), reverse("pseo_landing", args=["cork"]), reverse("listing_detail", args=["bare-sauna"])]:
            with CaptureQueriesContext(connection) as queries:
                response = self.client.get(url)

            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, "data:image/webp;base64,")
            self.assertContains(response, photo_url)
            self.assertNotContains(response, reverse("listing_photo", args=["bare-sauna"]))
            self.assertFalse(any('"photo_data" FROM' in q["sql"] or '"photo_data",' in q["sql"] for q in queries))
