from django.contrib import admin
from django.utils.safestring import mark_safe
from django.shortcuts import render
from .models import Product, ProductMedia, AuctionLot, AuctionBid, Waitlist


class ProductMediaInline(admin.TabularInline):
    model = ProductMedia
    extra = 1
    # Added 'media_preview' here
    fields = ("media_type", "media_url", "thumbnail_url", "caption", "is_primary", "order", "media_preview")
    readonly_fields = ("media_preview",)

    def media_preview(self, obj):
        """Generates an HTML preview depending on whether it's an image or a video."""
        if not obj.id or not obj.media_url:
            return mark_safe('<span style="color: #b0b0b0; font-style: italic;">Save to preview</span>')

        # If it's a video, render a small HTML5 video element with muted autoplay loop
        if obj.media_type == ProductMedia.VIDEO:
            return mark_safe(
                f'<video src="{obj.media_url}" style="width: 80px; height: 60px; object-fit: cover; border-radius: 4px;" muted autoplay loop playsinline></video>'
            )
        
        # Default to rendering a standard image preview
        return mark_safe(
            f'<img src="{obj.media_url}" style="width: 80px; height: 60px; object-fit: cover; border-radius: 4px;" />'
        )
    media_preview.short_description = "Preview"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display  = ("name", "category", "primary_species", "dimensions_display", "starting_price", "is_featured", "is_active")
    list_filter   = ("category", "is_featured", "is_active")
    search_fields = ("name", "primary_species")
    prepopulated_fields = {"slug": ("name",)}
    inlines       = [ProductMediaInline]
    
    # Organize fields cleanly into functional sections
    fieldsets = [
        ("Basic Information", {
            "fields": ["name", "slug", "description", "category", "primary_species"]
        }),
        ("Physical Dimensions & Layouts", {
            "fields": ["width_cm", "height_cm", "depth_cm", "architectural_drawing_url"],
            "description": "Provide structured sizing and line diagrams to help buyers verify spatial fits."
        }),
        ("Commercials & Logistics", {
            "fields": ["starting_price", "lead_time_days", "whatsapp_cta", "is_featured", "is_active"]
        }),
    ]
    inlines = [ProductMediaInline]


class AuctionBidInline(admin.TabularInline):
    model = AuctionBid
    extra = 0
    readonly_fields = ("placed_at",)


@admin.register(AuctionLot)
class AuctionLotAdmin(admin.ModelAdmin):
    # Added 'lot_preview' to display a clean thumbnail in the admin list view
    list_display  = ("lot_preview", "title", "status", "starting_bid", "current_bid", "bid_count", "end_time")
    list_filter   = ("status",)
    readonly_fields = ("current_bid", "created_at", "detail_preview")
    inlines       = [AuctionBidInline]

    def lot_preview(self, obj):
        """Displays a tiny thumbnail in the list dashboard grid."""
        # Pulls the primary_image_url property we defined on the Product model
        if obj.product and obj.product.primary_image_url:
            return mark_safe(f'<img src="{obj.product.primary_image_url}" style="width: 45px; height: 35px; object-fit: cover; border-radius: 4px;" />')
        return mark_safe('<span style="color: #b0b0b0; font-size: 11px; font-style: italic;">No Media</span>')
    lot_preview.short_description = "Item"

    def detail_preview(self, obj):
        """Displays a full-width media block inside the Auction Lot editor page."""
        if obj.product and obj.product.primary_image_url:
            return mark_safe(f'<img src="{obj.product.primary_image_url}" style="max-width: 320px; max-height: 240px; object-fit: contain; border-radius: 8px;" />')
        return "No primary media found for the linked product."
    detail_preview.short_description = "Product Visual Reference"


@admin.register(Waitlist)
class WaitlistAdmin(admin.ModelAdmin):
    list_display = (
        "image_thumbnail", 
        "name", 
        "email", 
        "piece_of_interest", 
        "budget_range", 
        "timeline_months", 
        "status", 
        "created_at"
    )
    list_filter = ("budget_range", "status")
    search_fields = ("name", "email", "piece_of_interest")
    readonly_fields = ("image_preview",)
    
    actions = ['print_waitlist_cards']

    def image_thumbnail(self, obj):
        if obj.reference_image:
            return mark_safe(f'<img src="{obj.reference_image.url}" style="width: 45px; height: 35px; object-fit: cover; border-radius: 4px;" />')
        return mark_safe('<span style="color: #b0b0b0; font-size: 11px; font-style: italic;">No Asset</span>')
    image_thumbnail.short_description = "Thumbnail"

    def image_preview(self, obj):
        if obj.reference_image:
            return mark_safe(f'<img src="{obj.reference_image.url}" style="max-width: 100%; max-height: 320px; object-fit: contain; border-radius: 8px;" />')
        return "No design blueprint references were attached."
    image_preview.short_description = "Artisan Design Reference Blueprint"

    def print_waitlist_cards(self, request, queryset):
        """Renders a minimal, print-optimized sheet for selected workshop jobs."""
        return render(request, 'storefront/print_waitlist.html', {
            'items': queryset,
            'title': 'MN Studio — Production Waitlist Run'
        })
    print_waitlist_cards.short_description = "🖨️ Print Selected Work Orders"
