from django.contrib import admin
from .models import Listing, SaunaSubmission, FeaturedListingSubscription


class FeaturedListingSubscriptionInline(admin.StackedInline):
    model = FeaturedListingSubscription
    extra = 0
    max_num = 1
    readonly_fields = ("created_at", "updated_at")


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "city",
        "county",
        "is_featured",
        "stripe_subscription_status",
        "is_active",
        "rating",
        "reviews_count",
        "created_at",
    )
    search_fields = ("name", "city", "county")
    list_filter = ("is_featured", "is_active", "city", "county")
    actions = ["mark_as_featured", "mark_as_not_featured"]
    inlines = [FeaturedListingSubscriptionInline]

    def stripe_subscription_status(self, obj):
        subscription = getattr(obj, "featured_subscription", None)
        return subscription.subscription_status if subscription else "-"
    stripe_subscription_status.short_description = "Stripe status"
    
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


@admin.register(FeaturedListingSubscription)
class FeaturedListingSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "listing",
        "subscription_status",
        "stripe_subscription_id",
        "stripe_customer_id",
        "current_period_end",
        "grace_until",
        "auto_manage_featured",
        "updated_at",
    )
    list_filter = ("subscription_status", "auto_manage_featured", "cancel_at_period_end")
    search_fields = ("listing__name", "stripe_subscription_id", "stripe_customer_id")
    readonly_fields = ("created_at", "updated_at")
