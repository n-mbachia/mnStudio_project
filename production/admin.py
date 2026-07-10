from django.contrib import admin
from .models import JobCard, TimberEntry, HardwareEntry, LaborEntry


class TimberInline(admin.TabularInline):
    model = TimberEntry
    extra = 0
    fields = ("species", "board_feet", "unit_cost_per_bf", "total_cost", "state", "supplier")
    readonly_fields = ("total_cost",)


class HardwareInline(admin.TabularInline):
    model = HardwareEntry
    extra = 0
    fields = ("item_name", "quantity", "unit_cost", "total_cost", "state", "supplier")
    readonly_fields = ("total_cost",)


class LaborInline(admin.TabularInline):
    model = LaborEntry
    extra = 0
    fields = ("artisan", "task_description", "piece_rate", "total_cost", "state")
    readonly_fields = ("total_cost",)


@admin.register(JobCard)
class JobCardAdmin(admin.ModelAdmin):
    list_display   = ("job", "is_locked", "start_date", "target_completion", "actual_completion")
    list_filter    = ("is_locked",)
    readonly_fields = ("unlocked_at", "unlocked_by", "created_at")
    inlines        = [TimberInline, HardwareInline, LaborInline]


@admin.register(TimberEntry)
class TimberEntryAdmin(admin.ModelAdmin):
    list_display = ("job_card", "species", "board_feet", "unit_cost_per_bf", "total_cost", "state")
    list_filter  = ("species", "state")
    readonly_fields = ("total_cost",)


@admin.register(HardwareEntry)
class HardwareEntryAdmin(admin.ModelAdmin):
    list_display = ("job_card", "item_name", "quantity", "unit_cost", "total_cost", "state")
    list_filter  = ("state",)
    readonly_fields = ("total_cost",)


@admin.register(LaborEntry)
class LaborEntryAdmin(admin.ModelAdmin):
    list_display = ("job_card", "artisan", "task_description", "piece_rate", "state")
    list_filter  = ("state", "artisan__specialty")
