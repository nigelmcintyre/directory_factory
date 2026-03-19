from django.db import models
from django.templatetags.static import static
from django.urls import reverse
from django.utils.text import slugify


CURATED_COVER_IMAGES = {
    "top-5-health-benefits-of-regular-sauna-use": "images/blog/sauna-benefits.webp",
    "wood-fired-vs-infrared-which-sauna-is-right-for-you": "images/blog/sauna-types.webp",
    "the-rise-of-sea-swimming-sauna-culture-in-ireland": "images/blog/sauna-ireland.webp",
}

DEFAULT_COVER_IMAGE = "images/blog/sauna-default.svg"


class Post(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    excerpt = models.TextField(blank=True)
    content = models.TextField()
    cover_image_url = models.URLField(blank=True)
    author = models.CharField(max_length=100, default="Sauna Guide Team")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('post_detail', args=[self.slug])

    @property
    def display_cover_image_url(self):
        image_path = CURATED_COVER_IMAGES.get(self.slug)
        if image_path:
            return static(image_path)
        if self.cover_image_url:
            return self.cover_image_url
        return static(DEFAULT_COVER_IMAGE)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
