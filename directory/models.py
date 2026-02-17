from django.db import models
from django.utils.text import slugify


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
