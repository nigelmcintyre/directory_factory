from django.contrib import admin
from .models import Listing


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "county", "is_active", "created_at")
    search_fields = ("name", "city", "county")
    list_filter = ("is_active", "city", "county")
