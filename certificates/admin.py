from django.contrib import admin
from .models import Certificate, CareSchedule


class CareScheduleInline(admin.TabularInline):
    model = CareSchedule
    extra = 0
    fields = ("care_type", "due_date", "notification_sent", "completed")


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display  = ("certificate_id", "piece_name", "client_name_display", "completion_date", "primary_artisan")
    search_fields = ("piece_name", "client_name_display", "certificate_id")
    readonly_fields = ("certificate_id", "created_at")
    inlines       = [CareScheduleInline]


@admin.register(CareSchedule)
class CareScheduleAdmin(admin.ModelAdmin):
    list_display  = ("certificate", "care_type", "due_date", "notification_sent", "completed")
    list_filter   = ("care_type", "notification_sent", "completed")
