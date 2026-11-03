"""Partner inquiries and submissions are persisted, notified and spam-filtered."""

from unittest.mock import patch
from urllib.parse import parse_qs

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from directory.models import Listing, PartnerInquiry, SaunaSubmission

INQUIRY = {
    "sauna_name": "Hot & <Cold> Sauna",
    "contact_name": "Owner",
    "contact_email": "owner@example.com",
    "phone": "",
    "tier_interest": "tier1",
    "message": "Interested",
}

SUBMISSION = {
    "name": "New Sauna",
    "city": "Dublin",
    "county": "Dublin",
    "heat_source": "wood",
    "cold_plunge": "yes",
    "submitter_email": "tester@example.com",
}


@override_settings(TELEGRAM_BOT_TOKEN="token", TELEGRAM_CHAT_ID="chat", ADMIN_EMAIL="admin@example.com")
@patch("directory.views.urllib.request.urlopen")
class PartnerInquiryTests(TestCase):
    def test_inquiry_saved_and_alert_escaped(self, urlopen):
        response = self.client.post(reverse("get_featured"), INQUIRY)

        self.assertRedirects(response, reverse("get_featured"))
        self.assertEqual(PartnerInquiry.objects.get().sauna_name, "Hot & <Cold> Sauna")
        text = parse_qs(urlopen.call_args.args[0].data.decode())["text"][0]
        self.assertIn("Hot &amp; &lt;Cold&gt; Sauna", text)

    def test_inquiry_emailed_with_reply_to_owner(self, urlopen):
        self.client.post(reverse("get_featured"), INQUIRY)

        [email] = mail.outbox
        self.assertEqual(email.to, ["admin@example.com"])
        self.assertEqual(email.reply_to, ["owner@example.com"])
        self.assertIn("Sauna: Hot & <Cold> Sauna", email.body)

    def test_inquiry_saved_when_email_fails(self, urlopen):
        with patch("directory.views.EmailMessage.send", side_effect=OSError("smtp down")):
            response = self.client.post(reverse("get_featured"), INQUIRY)

        self.assertRedirects(response, reverse("get_featured"))
        self.assertEqual(PartnerInquiry.objects.count(), 1)

    def test_inquiry_saved_when_telegram_fails(self, urlopen):
        urlopen.side_effect = OSError("telegram down")

        response = self.client.post(reverse("get_featured"), INQUIRY)

        self.assertRedirects(response, reverse("get_featured"))
        self.assertEqual(PartnerInquiry.objects.count(), 1)

    def test_honeypot_discards_inquiry(self, urlopen):
        response = self.client.post(reverse("get_featured"), {**INQUIRY, "fax": "spam"})

        self.assertRedirects(response, reverse("get_featured"))
        self.assertEqual(PartnerInquiry.objects.count(), 0)
        urlopen.assert_not_called()
        self.assertEqual(mail.outbox, [])


@override_settings(TELEGRAM_BOT_TOKEN="token", TELEGRAM_CHAT_ID="chat")
@patch("directory.views.urllib.request.urlopen")
class SubmissionAlertTests(TestCase):
    def test_submission_sends_alert(self, urlopen):
        self.client.post(reverse("submit_sauna"), SUBMISSION)

        self.assertEqual(SaunaSubmission.objects.count(), 1)
        urlopen.assert_called_once()
        self.assertEqual(mail.outbox[0].reply_to, ["tester@example.com"])

    def test_honeypot_discards_submission(self, urlopen):
        response = self.client.post(reverse("submit_sauna"), {**SUBMISSION, "fax": "spam"})

        self.assertRedirects(response, reverse("submit_success"))
        self.assertEqual(SaunaSubmission.objects.count(), 0)
        urlopen.assert_not_called()


class ApproveSubmissionActionTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_superuser("admin", "admin@example.com", "pw"))

    def _approve(self, *submissions):
        return self.client.post(
            reverse("admin:directory_saunasubmission_changelist"),
            {"action": "approve_submissions", "_selected_action": [s.pk for s in submissions]},
        )

    def test_creates_listing_with_unique_slug(self):
        Listing.objects.create(name="New Sauna", slug="new-sauna", city="Cork", county="Cork")
        submission = SaunaSubmission.objects.create(**SUBMISSION, website="https://new.ie")

        self._approve(submission)

        listing = Listing.objects.get(slug="new-sauna-2")
        self.assertEqual(listing.website, "https://new.ie")
        self.assertEqual(listing.attributes["cold_plunge"], "yes")
        self.assertEqual(listing.attributes["showers"], "not listed")
        submission.refresh_from_db()
        self.assertEqual(submission.status, "approved")

    def test_skips_already_approved(self):
        submission = SaunaSubmission.objects.create(**SUBMISSION, status="approved")

        self._approve(submission)

        self.assertFalse(Listing.objects.exists())
