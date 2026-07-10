"""
Certificates of Authenticity — permanent provenance chain for every commission.
Each completed piece receives a UUID-based Certificate with a QR code.
The public /certificates/<uuid>/ URL is embedded in the QR code affixed to the piece.
"""
import uuid
from django.db import models


class Certificate(models.Model):
    certificate_id    = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    job               = models.OneToOneField("core.Job", on_delete=models.PROTECT, related_name="certificate")
    piece_name        = models.CharField(max_length=200)
    client_name_display = models.CharField(max_length=200, default="Private Collection",
                                            help_text="Client name or 'Private Collection' for anonymous")
    species_used      = models.JSONField(default=list,
                                         help_text="List of species used, e.g. ['Mvule', 'Mahogany']")
    total_board_feet  = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    primary_artisan   = models.ForeignKey("partners.ArtisanProfile", on_delete=models.SET_NULL,
                                           null=True, blank=True)
    completion_date   = models.DateField()
    care_instructions = models.TextField(blank=True)
    qr_code_url       = models.URLField(blank=True, help_text="Auto-generated QR code image URL")
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-completion_date"]

    def __str__(self):
        return f"CoA {self.certificate_id} — {self.piece_name}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("certificates:detail", kwargs={"uuid": str(self.certificate_id)})

    def generate_qr(self, base_url):
        """Generate QR code image and return data URI."""
        import qrcode, io, base64
        url = f"{base_url.rstrip('/')}{self.get_absolute_url()}"
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        data = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{data}"


class CareSchedule(models.Model):
    """Scheduled care reminders — triggers post-delivery client retention."""
    certificate = models.ForeignKey(Certificate, on_delete=models.CASCADE, related_name="care_schedules")

    class CareType(models.TextChoices):
        BOARD_BUTTER    = "board_butter",    "Board Butter / Oil Treatment"
        POLISH          = "polish",          "Polish & Clean"
        STRUCTURAL_CHECK = "structural",     "Structural Check"
        REFINISHING     = "refinishing",     "Refinishing"

    care_type          = models.CharField(max_length=20, choices=CareType.choices)
    due_date           = models.DateField()
    notification_sent  = models.BooleanField(default=False)
    completed          = models.BooleanField(default=False)
    notes              = models.TextField(blank=True)

    class Meta:
        ordering = ["due_date"]

    def __str__(self):
        return f"{self.certificate.piece_name} — {self.get_care_type_display()} due {self.due_date}"
