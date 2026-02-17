from django.contrib import admin
from .models import Listing, SaunaSubmission


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "county", "is_featured", "is_active", "created_at")
    search_fields = ("name", "city", "county")
    list_filter = ("is_featured", "is_active", "city", "county")
    actions = ["mark_as_featured", "mark_as_not_featured"]
    
    def mark_as_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f"{updated} listing(s) marked as featured.")
    mark_as_featured.short_description = "Mark selected as featured"
    
    def mark_as_not_featured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f"{updated} listing(s) marked as not featured.")
    mark_as_not_featured.short_description = "Remove featured status"


@admin.register(SaunaSubmission)
class SaunaSubmissionAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "county", "status", "submitter_email", "created_at")
    list_filter = ("status", "county", "created_at")
    search_fields = ("name", "city", "county", "submitter_email", "submitter_name")
    readonly_fields = ("created_at", "updated_at")
    
    fieldsets = (
        ("Sauna Information", {
            "fields": ("name", "city", "county", "address", "website", "phone", "description")
        }),
        ("Attributes", {
            "fields": ("heat_source", "cold_plunge", "dog_friendly", "showers", "changing_facilities", "sea_view", "opening_hours")
        }),
        ("Submission Details", {
            "fields": ("submitter_name", "submitter_email", "status", "admin_notes", "created_at", "updated_at")
        }),
    )
    
    actions = ["approve_submissions", "reject_submissions"]
    
    def approve_submissions(self, request, queryset):
        updated = queryset.update(status='approved')
        self.message_user(request, f"{updated} submission(s) marked as approved.")
    approve_submissions.short_description = "Mark selected as approved"
    
    def reject_submissions(self, request, queryset):
        updated = queryset.update(status='rejected')
        self.message_user(request, f"{updated} submission(s) marked as rejected.")
    reject_submissions.short_description = "Mark selected as rejected"
