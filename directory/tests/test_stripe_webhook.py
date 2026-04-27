"""Tests for Stripe-driven featured listing subscription sync."""

from datetime import datetime, timezone as dt_timezone, timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from directory.models import (
    FeaturedListingSubscription,
    Listing,
    StripeWebhookEvent,
)


def _make_listing(**overrides):
    defaults = dict(
        name="Test Sauna",
        slug="test-sauna",
        city="Dublin",
        county="Dublin",
        is_featured=False,
    )
    defaults.update(overrides)
    return Listing.objects.create(**defaults)


def _make_subscription(listing, **overrides):
    defaults = dict(
        stripe_subscription_id="sub_test_123",
        stripe_customer_id="cus_test_123",
        subscription_status="incomplete",
        auto_manage_featured=True,
    )
    defaults.update(overrides)
    return FeaturedListingSubscription.objects.create(listing=listing, **defaults)


def _stripe_subscription_payload(status="active", subscription_id="sub_test_123"):
    period_end = int((timezone.now() + timedelta(days=30)).timestamp())
    return {
        "id": subscription_id,
        "customer": "cus_test_123",
        "status": status,
        "cancel_at_period_end": False,
        "items": {
            "data": [
                {
                    "price": {"id": "price_test_123"},
                    "current_period_end": period_end,
                }
            ]
        },
    }


def _stripe_event(event_type, data_object, event_id="evt_test_1"):
    return {
        "id": event_id,
        "type": event_type,
        "data": {"object": data_object},
    }


class FeaturedSubscriptionModelTests(TestCase):
    def test_should_be_featured_when_active(self):
        listing = _make_listing()
        sub = _make_subscription(listing, subscription_status="active")
        self.assertTrue(sub.should_be_featured())

    def test_should_be_featured_when_trialing(self):
        listing = _make_listing()
        sub = _make_subscription(listing, subscription_status="trialing")
        self.assertTrue(sub.should_be_featured())

    def test_not_featured_when_canceled_no_grace(self):
        listing = _make_listing()
        sub = _make_subscription(listing, subscription_status="canceled")
        self.assertFalse(sub.should_be_featured())

    def test_featured_during_grace_period(self):
        listing = _make_listing()
        sub = _make_subscription(
            listing,
            subscription_status="past_due",
            grace_until=timezone.now() + timedelta(days=2),
        )
        self.assertTrue(sub.should_be_featured())

    def test_not_featured_after_grace_expires(self):
        listing = _make_listing()
        sub = _make_subscription(
            listing,
            subscription_status="past_due",
            grace_until=timezone.now() - timedelta(days=1),
        )
        self.assertFalse(sub.should_be_featured())


@override_settings(STRIPE_ENABLED=True, STRIPE_WEBHOOK_SECRET="whsec_test")
class StripeWebhookTests(TestCase):
    def setUp(self):
        self.listing = _make_listing()
        self.subscription = _make_subscription(self.listing)
        self.url = reverse("stripe_webhook")

    def _post_event(self, event):
        with patch("stripe.Webhook.construct_event", return_value=event):
            return self.client.post(
                self.url,
                data=b"{}",
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="t=1,v1=fake",
            )

    def test_subscription_created_marks_listing_featured(self):
        event = _stripe_event(
            "customer.subscription.created",
            _stripe_subscription_payload(status="active"),
        )
        response = self._post_event(event)
        self.assertEqual(response.status_code, 200)

        self.listing.refresh_from_db()
        self.subscription.refresh_from_db()
        self.assertTrue(self.listing.is_featured)
        self.assertEqual(self.subscription.subscription_status, "active")
        self.assertEqual(self.subscription.stripe_price_id, "price_test_123")
        self.assertIsNotNone(self.subscription.current_period_end)

    def test_subscription_canceled_unfeatures_listing(self):
        self.listing.is_featured = True
        self.listing.save(update_fields=["is_featured"])
        event = _stripe_event(
            "customer.subscription.deleted",
            _stripe_subscription_payload(status="canceled"),
        )
        response = self._post_event(event)
        self.assertEqual(response.status_code, 200)

        self.listing.refresh_from_db()
        self.assertFalse(self.listing.is_featured)

    def test_invoice_payment_failed_starts_grace_period(self):
        self.listing.is_featured = True
        self.listing.save(update_fields=["is_featured"])
        event = _stripe_event(
            "invoice.payment_failed",
            {"subscription": "sub_test_123", "status": "open"},
            event_id="evt_test_failed",
        )
        response = self._post_event(event)
        self.assertEqual(response.status_code, 200)

        self.subscription.refresh_from_db()
        self.listing.refresh_from_db()
        self.assertIsNotNone(self.subscription.grace_until)
        # Still featured during grace.
        self.assertTrue(self.listing.is_featured)

    def test_invoice_paid_clears_grace(self):
        self.subscription.grace_until = timezone.now() + timedelta(days=2)
        self.subscription.save(update_fields=["grace_until"])
        event = _stripe_event(
            "invoice.paid",
            {"subscription": "sub_test_123", "status": "paid"},
            event_id="evt_test_paid",
        )
        response = self._post_event(event)
        self.assertEqual(response.status_code, 200)

        self.subscription.refresh_from_db()
        self.assertIsNone(self.subscription.grace_until)

    def test_duplicate_event_is_ignored(self):
        event = _stripe_event(
            "customer.subscription.updated",
            _stripe_subscription_payload(status="active"),
            event_id="evt_dup",
        )
        first = self._post_event(event)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(StripeWebhookEvent.objects.count(), 1)

        second = self._post_event(event)
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.json().get("duplicate"))
        self.assertEqual(StripeWebhookEvent.objects.count(), 1)

    def test_auto_manage_disabled_does_not_change_listing(self):
        self.subscription.auto_manage_featured = False
        self.subscription.save(update_fields=["auto_manage_featured"])
        event = _stripe_event(
            "customer.subscription.created",
            _stripe_subscription_payload(status="active"),
        )
        response = self._post_event(event)
        self.assertEqual(response.status_code, 200)

        self.listing.refresh_from_db()
        self.assertFalse(self.listing.is_featured)


@override_settings(STRIPE_ENABLED=False)
class StripeWebhookDisabledTests(TestCase):
    def test_returns_503_when_disabled(self):
        url = reverse("stripe_webhook")
        response = self.client.post(url, data=b"{}", content_type="application/json")
        self.assertEqual(response.status_code, 503)


@override_settings(STRIPE_ENABLED=True, STRIPE_WEBHOOK_SECRET="")
class StripeWebhookMisconfiguredTests(TestCase):
    def test_returns_503_when_secret_missing(self):
        url = reverse("stripe_webhook")
        response = self.client.post(url, data=b"{}", content_type="application/json")
        self.assertEqual(response.status_code, 503)
