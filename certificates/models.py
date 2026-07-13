"""
Certificates of Authenticity — permanent provenance chain for every commission.
Each completed piece receives a UUID-based Certificate with a QR code.
The public /certificates/<uuid>/ URL is embedded in the QR code affixed to the piece.
"""
import uuid
from django.db import models


class Certificate(models.Model):
    certificate_id    = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    job               = models.OneToOneField("core.Job", on_delete=models.PROTECT, related_name="certificate")
    piece_name        = models.CharField(max_length=200, verbose_name="Piece Name")
    client_name_display = models.CharField(
        max_length=200,
        default="Private Collection",
        verbose_name="Display Name",
        help_text="Client name or 'Private Collection' for anonymous commissions"
    )
    species_used      = models.JSONField(
        default=list,
        verbose_name="Species Used",
        help_text="List of wood species, e.g. ['Mvule', 'Mahogany']"
    )
    total_board_feet  = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        verbose_name="Total Board Feet"
    )
    primary_artisan   = models.ForeignKey(
        "partners.ArtisanProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Primary Artisan"
    )
    completion_date   = models.DateField(verbose_name="Completion Date")
    care_instructions = models.TextField(
        blank=True,
        verbose_name="Care Instructions",
        help_text="Maintenance guidelines for the piece"
    )
    qr_code_data      = models.TextField(blank=True, help_text="Cached QR code data URI")
    created_at        = models.DateTimeField(auto_now_add=True, verbose_name="Created")
    updated_at        = models.DateTimeField(auto_now=True, verbose_name="Updated")

    class Meta:
        ordering = ["-completion_date"]
        verbose_name = "Certificate of Authenticity"
        verbose_name_plural = "Certificates of Authenticity"

    def __str__(self):
        return f"CoA {self.certificate_id.hex[:8]} — {self.piece_name}"

    @property
    def species_formatted(self):
        """Return species list as comma-separated string."""
        if isinstance(self.species_used, list):
            return ", ".join(self.species_used) if self.species_used else "Unknown"
        return str(self.species_used)

    @property
    def certificate_id_short(self):
        """Return first 8 characters of UUID for display."""
        return str(self.certificate_id)[:8].upper()

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("certificates:detail", kwargs={"uuid": str(self.certificate_id)})

    def generate_qr(self, base_url):
        """Generate QR code image and return data URI, caching result."""
        if self.qr_code_data:
            return self.qr_code_data

        import qrcode
        import io
        import base64

        url = f"{base_url.rstrip('/')}{self.get_absolute_url()}"
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        data = base64.b64encode(buffer.getvalue()).decode()
        qr_uri = f"data:image/png;base64,{data}"

        # Cache the QR code
        self.qr_code_data = qr_uri
        self.save(update_fields=["qr_code_data"])

        return qr_uri


class CareSchedule(models.Model):
    """Scheduled care reminders — triggers post-delivery client retention."""

    class CareType(models.TextChoices):
        BOARD_BUTTER = "board_butter", "Board Butter / Oil Treatment"
        POLISH = "polish", "Polish & Clean"
        STRUCTURAL_CHECK = "structural", "Structural Check"
        REFINISHING = "refinishing", "Refinishing"

    certificate = models.ForeignKey(
        Certificate,
        on_delete=models.CASCADE,
        related_name="care_schedules",
        verbose_name="Certificate"
    )
    care_type = models.CharField(
        max_length=20,
        choices=CareType.choices,
        verbose_name="Care Type"
    )
    due_date = models.DateField(verbose_name="Due Date")
    notification_sent = models.BooleanField(
        default=False,
        verbose_name="Notification Sent"
    )
    completed = models.BooleanField(
        default=False,
        verbose_name="Completed"
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notes"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["due_date"]
        verbose_name = "Care Schedule"
        verbose_name_plural = "Care Schedules"

    def __str__(self):
        status = "✓" if self.completed else "○"
        return f"{status} {self.get_care_type_display()} — {self.due_date.strftime('%b %d, %Y')}"
