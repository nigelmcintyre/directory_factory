from django.contrib import admin
from django.utils.text import slugify
from .models import FeaturedListingSubscription, Listing, ListingDailyStat, PartnerInquiry, SaunaSubmission

SUBMISSION_ATTRIBUTES = ["heat_source", "cold_plunge", "dog_friendly", "showers", "changing_facilities", "sea_view"]


def _unique_listing_slug(name):
    base = slugify(name) or "sauna"
    slug, n = base, 2
    while Listing.objects.filter(slug=slug).exists():
        slug, n = f"{base}-{n}", n + 1
    return slug


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
        # Opening hours are free text on submissions but "Day: hours|Day: hours" on listings,
        # so they are left for manual entry.
        created = []
        for submission in queryset.exclude(status="approved"):
            listing = Listing.objects.create(
                name=submission.name,
                slug=_unique_listing_slug(submission.name),
                city=submission.city,
                county=submission.county,
                address=submission.address,
                website=submission.website,
                phone=submission.phone,
                description=submission.description,
                attributes={key: getattr(submission, key) or "not listed" for key in SUBMISSION_ATTRIBUTES},
            )
            submission.status = "approved"
            submission.save(update_fields=["status", "updated_at"])
            created.append(listing.slug)
        self.message_user(request, f"Created {len(created)} listing(s): {', '.join(created) or 'none'}.")
    approve_submissions.short_description = "Approve and create listings"
    
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


@admin.register(PartnerInquiry)
class PartnerInquiryAdmin(admin.ModelAdmin):
    list_display = ("sauna_name", "contact_name", "contact_email", "tier_interest", "status", "created_at")
    list_filter = ("status", "tier_interest", "created_at")
    search_fields = ("sauna_name", "contact_name", "contact_email")
    list_editable = ("status",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(ListingDailyStat)
class ListingDailyStatAdmin(admin.ModelAdmin):
    list_display = ("listing", "date", "metric", "count")
    list_filter = ("metric", "date")
    search_fields = ("listing__name",)
    date_hierarchy = "date"
    list_select_related = ("listing",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
