from django.contrib import admin
from .models import SupplierProfile, SupplierRateHistory, PurchaseOrder, ArtisanProfile


class RateHistoryInline(admin.TabularInline):
    model = SupplierRateHistory
    extra = 0
    readonly_fields = ("created_at",)
    fields = ("rate", "effective_until", "recorded_by", "created_at")


@admin.register(SupplierProfile)
class SupplierProfileAdmin(admin.ModelAdmin):
    list_display  = ("name", "material_type", "location", "current_rate", "is_active")
    list_filter   = ("material_type", "location", "is_active")
    search_fields = ("name", "contact_name", "phone")
    inlines       = [RateHistoryInline]


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display   = ("po_number", "supplier", "status", "estimated_amount", "unit_cost_at_receipt", "raised_at")
    list_filter    = ("status", "supplier__material_type")
    search_fields  = ("po_number", "supplier__name")
    readonly_fields = ("po_number", "raised_at")

    def save_model(self, request, obj, form, change):
        if change and "status" in form.changed_data and obj.status == "received":
            from django.utils import timezone
            if not obj.received_at:
                obj.received_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(ArtisanProfile)
class ArtisanProfileAdmin(admin.ModelAdmin):
    list_display  = ("name", "specialty", "base_piece_rate", "is_active")
    list_filter   = ("specialty", "is_active")
    search_fields = ("name", "phone")
