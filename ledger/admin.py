from django.contrib import admin
from .models import Quote, QuoteLineItem, Invoice, InvoiceLineItem, Payment, COGSRecord, CompliancePeriod


class QuoteLineItemInline(admin.TabularInline):
    model = QuoteLineItem
    extra = 1
    readonly_fields = ("total",)
    fields = ("description", "quantity", "unit_price", "total")


class InvoiceLineItemInline(admin.TabularInline):
    model = InvoiceLineItem
    extra = 1
    readonly_fields = ("total",)
    fields = ("description", "quantity", "unit_price", "total")


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ("recorded_at",)
    fields = ("amount", "method", "mpesa_ref", "status", "paid_at", "recorded_by")


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display  = ("quote_id", "client", "status", "total", "deposit_amount", "created_at")
    list_filter   = ("status",)
    search_fields = ("quote_id", "client__name")
    readonly_fields = ("quote_id", "subtotal", "total", "created_at", "sent_at", "approved_at")
    inlines       = [QuoteLineItemInline]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display  = ("invoice_id", "client", "status", "total", "issued_at")
    list_filter   = ("status",)
    search_fields = ("invoice_id", "client__name")
    readonly_fields = ("invoice_id", "subtotal", "total", "created_at")
    inlines       = [InvoiceLineItemInline, PaymentInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display  = ("invoice", "amount", "method", "status", "paid_at")
    list_filter   = ("method", "status")
    readonly_fields = ("recorded_at",)


@admin.register(COGSRecord)
class COGSRecordAdmin(admin.ModelAdmin):
    list_display  = ("job", "estimated_cogs", "actual_cogs", "variance", "last_updated")
    readonly_fields = ("last_updated",)


@admin.register(CompliancePeriod)
class CompliancePeriodAdmin(admin.ModelAdmin):
    list_display  = ("__str__", "gross_sales", "gross_profit", "tot", "ahl",
                     "retirement_savings", "sacco_savings", "total_obligations", "is_finalised")
    list_filter   = ("year", "is_finalised")
    readonly_fields = ("computed_at",)
