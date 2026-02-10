from django.db import models


class Listing(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    city = models.CharField(max_length=120)
    county = models.CharField(max_length=120, blank=True)
    category = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=500, blank=True)
    website = models.URLField(max_length=500, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    place_id = models.CharField(max_length=255, blank=True)
    photo_ref = models.CharField(max_length=500, blank=True)
    rating = models.DecimalField(max_digits=2, decimal_places=1, null=True, blank=True)
    reviews_count = models.IntegerField(null=True, blank=True)
    attributes = models.JSONField(default=dict, blank=True)
    structured_data = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["city", "category"]),
        ]

    def __str__(self) -> str:
        return self.name
