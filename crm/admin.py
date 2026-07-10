from django.contrib import admin
from .models import ClientProfile, Lead, DesignBrief, Interaction


class InteractionInline(admin.TabularInline):
    model = Interaction
    extra = 0
    readonly_fields = ("created_at", "created_by")
    fields = ("channel", "note", "job", "created_by", "created_at")


class LeadInline(admin.TabularInline):
    model = Lead
    extra = 0
    fields = ("piece_type", "status", "created_at")
    readonly_fields = ("created_at",)


@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    list_display   = ("name", "email", "phone", "acquisition_source", "is_vip", "job_count", "created_at")
    list_filter    = ("acquisition_source", "is_vip", "county")
    search_fields  = ("name", "email", "phone")
    inlines        = [LeadInline, InteractionInline]
    readonly_fields = ("created_at", "updated_at")

    def job_count(self, obj):
        return obj.jobs.count()
    job_count.short_description = "Jobs"


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display  = ("client", "piece_type", "status", "created_at")
    list_filter   = ("status",)
    search_fields = ("client__name", "piece_type")


@admin.register(DesignBrief)
class DesignBriefAdmin(admin.ModelAdmin):
    list_display  = ("job", "version", "title", "status", "approved_at")
    list_filter   = ("status",)
    search_fields = ("job__job_id", "title")
    readonly_fields = ("created_at", "approved_at")


@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    list_display  = ("client", "channel", "job", "created_by", "created_at")
    list_filter   = ("channel",)
    readonly_fields = ("created_at",)
