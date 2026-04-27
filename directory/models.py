from django.db import models
from django.utils.text import slugify
from django.utils import timezone


class Listing(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    city = models.CharField(max_length=120)
    county = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=500, blank=True)
    website = models.URLField(max_length=500, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    place_id = models.CharField(max_length=255, blank=True)
    photo_ref = models.CharField(max_length=500, blank=True)
    photo_data = models.TextField(blank=True, help_text="Base64 encoded WebP image data")
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    rating = models.DecimalField(max_digits=2, decimal_places=1, null=True, blank=True)
    reviews_count = models.IntegerField(null=True, blank=True)
    attributes = models.JSONField(default=dict, blank=True)
    structured_data = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["county"]),
            models.Index(fields=["-is_featured", "name"]),
        ]

    def __str__(self) -> str:
        return self.name


class SaunaSubmission(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    # Basic information
    name = models.CharField(max_length=255)
    city = models.CharField(max_length=120)
    county = models.CharField(max_length=120)
    address = models.CharField(max_length=500, blank=True)
    website = models.URLField(max_length=500, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True, help_text="Tell us about this sauna")
    
    # Attributes
    heat_source = models.CharField(max_length=50, blank=True)
    cold_plunge = models.CharField(max_length=20, blank=True)
    dog_friendly = models.CharField(max_length=20, blank=True)
    showers = models.CharField(max_length=20, blank=True)
    changing_facilities = models.CharField(max_length=20, blank=True)
    sea_view = models.CharField(max_length=20, blank=True)
    opening_hours = models.TextField(blank=True, help_text="Optional: Opening hours information")
    
    # Submission tracking
    submitter_name = models.CharField(max_length=255, blank=True)
    submitter_email = models.EmailField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self) -> str:
        return f"{self.name} - {self.status}"


class FeaturedListingSubscription(models.Model):
    STATUS_CHOICES = [
        ("incomplete", "Incomplete"),
        ("incomplete_expired", "Incomplete Expired"),
        ("trialing", "Trialing"),
        ("active", "Active"),
        ("past_due", "Past Due"),
        ("canceled", "Canceled"),
        ("unpaid", "Unpaid"),
        ("paused", "Paused"),
    ]

    listing = models.OneToOneField(
        Listing,
        on_delete=models.CASCADE,
        related_name="featured_subscription",
    )
    stripe_customer_id = models.CharField(max_length=255, blank=True, db_index=True)
    stripe_subscription_id = models.CharField(max_length=255, unique=True, db_index=True)
    stripe_price_id = models.CharField(max_length=255, blank=True)
    subscription_status = models.CharField(
        max_length=32,
        choices=STATUS_CHOICES,
        default="incomplete",
        db_index=True,
    )
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    last_invoice_status = models.CharField(max_length=64, blank=True)
    grace_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional grace window after payment failure before auto-unfeature.",
    )
    auto_manage_featured = models.BooleanField(
        default=True,
        help_text="When enabled, webhooks will update listing.is_featured automatically.",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"{self.listing.name} ({self.subscription_status})"

    def should_be_featured(self, now=None) -> bool:
        now = now or timezone.now()
        if self.subscription_status in {"active", "trialing"}:
            return True
        return bool(self.grace_until and self.grace_until >= now)


class StripeWebhookEvent(models.Model):
    """Record of processed Stripe webhook events for idempotency."""

    stripe_event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=128, blank=True)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-received_at"]

    def __str__(self) -> str:
        return f"{self.event_type} {self.stripe_event_id}"
