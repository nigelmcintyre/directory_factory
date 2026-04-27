# Generated manually for Stripe webhook idempotency tracking

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("directory", "0012_featured_listing_subscription"),
    ]

    operations = [
        migrations.CreateModel(
            name="StripeWebhookEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("stripe_event_id", models.CharField(max_length=255, unique=True)),
                ("event_type", models.CharField(blank=True, max_length=128)),
                ("received_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-received_at"],
            },
        ),
    ]
