from django.contrib import admin
from .models import Job, AuditLog


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display  = ("job_id", "client", "status", "quoted_price", "actual_cogs", "gross_profit", "created_at")
    list_filter   = ("status", "created_at")
    search_fields = ("job_id", "client__name", "description")
    readonly_fields = ("job_id", "estimated_cogs", "actual_cogs", "gross_profit", "created_at", "updated_at")
    fieldsets = (
        ("Identity",   {"fields": ("job_id", "client", "status", "description")}),
        ("Financials", {"fields": ("quoted_price", "target_margin", "estimated_cogs", "actual_cogs", "gross_profit")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display  = ("created_at", "job", "user", "action")
    list_filter   = ("action",)
    readonly_fields = ("created_at",)
