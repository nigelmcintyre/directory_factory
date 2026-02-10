from django.contrib import admin
from .models import Listing


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "category", "is_active", "created_at")
    search_fields = ("name", "city", "category")
    list_filter = ("is_active", "city", "category")
