# Generated manually for featured listing subscription scaffolding

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("directory", "0011_add_photo_data"),
    ]

    operations = [
        migrations.CreateModel(
            name="FeaturedListingSubscription",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("stripe_customer_id", models.CharField(blank=True, db_index=True, max_length=255)),
                ("stripe_subscription_id", models.CharField(db_index=True, max_length=255, unique=True)),
                ("stripe_price_id", models.CharField(blank=True, max_length=255)),
                (
                    "subscription_status",
                    models.CharField(
                        choices=[
                            ("incomplete", "Incomplete"),
                            ("incomplete_expired", "Incomplete Expired"),
                            ("trialing", "Trialing"),
                            ("active", "Active"),
                            ("past_due", "Past Due"),
                            ("canceled", "Canceled"),
                            ("unpaid", "Unpaid"),
                            ("paused", "Paused"),
                        ],
                        db_index=True,
                        default="incomplete",
                        max_length=32,
                    ),
                ),
                ("current_period_end", models.DateTimeField(blank=True, null=True)),
                ("cancel_at_period_end", models.BooleanField(default=False)),
                ("last_invoice_status", models.CharField(blank=True, max_length=64)),
                (
                    "grace_until",
                    models.DateTimeField(
                        blank=True,
                        help_text="Optional grace window after payment failure before auto-unfeature.",
                        null=True,
                    ),
                ),
                (
                    "auto_manage_featured",
                    models.BooleanField(
                        default=True,
                        help_text="When enabled, webhooks will update listing.is_featured automatically.",
                    ),
                ),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "listing",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="featured_subscription",
                        to="directory.listing",
                    ),
                ),
            ],
            options={
                "ordering": ["-updated_at"],
            },
        ),
    ]
