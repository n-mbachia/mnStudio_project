from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import Certificate, CareSchedule


class CareScheduleInline(admin.TabularInline):
    model = CareSchedule
    extra = 0
    fields = ("care_type", "due_date", "notification_sent", "completed", "notes")
    ordering = ["due_date"]


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = (
        "certificate_id_short",
        "piece_name",
        "client_name_display",
        "completion_date",
        "primary_artisan",
        "actions_display"
    )
    list_filter = ("completion_date", "primary_artisan", "created_at")
    search_fields = ("piece_name", "client_name_display", "certificate_id")
    readonly_fields = ("certificate_id", "certificate_id_short", "created_at", "updated_at", "qr_preview")
    ordering = ["-completion_date"]
    inlines = [CareScheduleInline]

    fieldsets = (
        ("Certificate Information", {
            "fields": ("certificate_id", "certificate_id_short", "job", "created_at", "updated_at")
        }),
        ("Piece Details", {
            "fields": ("piece_name", "client_name_display", "completion_date", "primary_artisan")
        }),
        ("Materials", {
            "fields": ("species_used", "total_board_feet")
        }),
        ("Care & Instructions", {
            "fields": ("care_instructions",)
        }),
        ("QR Code", {
            "fields": ("qr_preview", "qr_code_data"),
            "classes": ("collapse",)
        }),
    )

    def certificate_id_short(self, obj):
        """Display truncated certificate ID."""
        return format_html(
            '<code style="background:#f0f0f0;padding:4px 8px;border-radius:4px;font-family:monospace">{}</code>',
            obj.certificate_id_short
        )
    certificate_id_short.short_description = "Certificate ID"

    def qr_preview(self, obj):
        """Display QR code preview if available."""
        if obj.qr_code_data:
            return format_html(
                '<img src="{}" style="max-width:150px;border:1px solid #ddd;padding:8px;border-radius:4px">',
                obj.qr_code_data
            )
        return "Not generated yet"
    qr_preview.short_description = "QR Code Preview"

    def actions_display(self, obj):
        """Display action links."""
        print_url = reverse("admin:certificates_certificate_change", args=[obj.id])
        detail_url = reverse("certificates:detail", args=[str(obj.certificate_id)])
        return format_html(
            '<a class="button" href="{}">Print</a> <a class="button" href="{}" target="_blank">View</a>',
            print_url,
            detail_url
        )
    actions_display.short_description = "Actions"


@admin.register(CareSchedule)
class CareScheduleAdmin(admin.ModelAdmin):
    list_display = (
        "certificate_short",
        "care_type",
        "due_date",
        "status_badge",
        "notification_sent"
    )
    list_filter = ("care_type", "completed", "notification_sent", "due_date")
    search_fields = ("certificate__piece_name", "certificate__certificate_id", "notes")
    readonly_fields = ("created_at",)
    ordering = ["-due_date"]

    fieldsets = (
        ("Care Schedule", {
            "fields": ("certificate", "care_type", "due_date")
        }),
        ("Status", {
            "fields": ("completed", "notification_sent", "notes")
        }),
        ("Metadata", {
            "fields": ("created_at",),
            "classes": ("collapse",)
        }),
    )

    def certificate_short(self, obj):
        """Display certificate piece name."""
        return format_html(
            '<strong>{}</strong><br><code style="font-size:11px;color:#666">{}</code>',
            obj.certificate.piece_name,
            obj.certificate.certificate_id_short
        )
    certificate_short.short_description = "Certificate"

    def status_badge(self, obj):
        """Display status badge."""
        if obj.completed:
            color = "#28a745"
            status = "✓ Completed"
        elif obj.notification_sent:
            color = "#ffc107"
            status = "⚠ Pending"
        else:
            color = "#6c757d"
            status = "○ Scheduled"

        return format_html(
            '<span style="background:{};color:white;padding:4px 8px;border-radius:4px;font-size:12px">{}</span>',
            color,
            status
        )
    status_badge.short_description = "Status"
