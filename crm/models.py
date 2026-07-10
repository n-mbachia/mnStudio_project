"""
CRM models — client lifecycle from first inquiry to repeat commission.
"""
from django.db import models


class AcquisitionSource(models.TextChoices):
    INSTAGRAM    = "instagram",     "Instagram"
    REFERRAL     = "referral",      "Referral"
    WHATSAPP     = "whatsapp",      "WhatsApp"
    WALK_IN      = "walk_in",       "Walk-In"
    WEBSITE      = "website",       "Website"
    AUCTION      = "auction",       "Auction"
    EXHIBITION   = "exhibition",    "Exhibition"
    OTHER        = "other",         "Other"


class ClientProfile(models.Model):
    name               = models.CharField(max_length=200)
    email              = models.EmailField(unique=True)
    phone              = models.CharField(max_length=20)
    secondary_phone    = models.CharField(max_length=20, blank=True)
    address            = models.TextField(blank=True)
    county             = models.CharField(max_length=50, blank=True)
    acquisition_source = models.CharField(max_length=30, choices=AcquisitionSource.choices,
                                          default=AcquisitionSource.REFERRAL)
    preference_notes   = models.TextField(blank=True,
                                          help_text="Species preferences, style notes, budget hints")
    is_vip             = models.BooleanField(default=False)
    created_at         = models.DateTimeField(auto_now_add=True)
    updated_at         = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Client"
        verbose_name_plural = "Clients"

    def __str__(self):
        return f"{self.name} ({self.email})"

    @property
    def total_spent(self):
        from django.db.models import Sum
        from ledger.models import Payment, PaymentStatus
        return Payment.objects.filter(
            invoice__job__client=self, status=PaymentStatus.CONFIRMED
        ).aggregate(t=Sum("amount"))["t"] or 0

    @property
    def job_count(self):
        return self.jobs.count()


class LeadStatus(models.TextChoices):
    INQUIRY       = "inquiry",      "Inquiry"
    QUOTED        = "quoted",       "Quoted"
    NEGOTIATING   = "negotiating",  "Negotiating"
    APPROVED      = "approved",     "Design Approved"
    IN_PRODUCTION = "production",   "In Production"
    DELIVERED     = "delivered",    "Delivered"
    RETAINED      = "retained",     "Retained Client"
    LOST          = "lost",         "Lost"


class Lead(models.Model):
    client     = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, related_name="leads")
    status     = models.CharField(max_length=20, choices=LeadStatus.choices, default=LeadStatus.INQUIRY)
    piece_type = models.CharField(max_length=100, help_text="e.g. 6-seater dining set, TV unit")
    notes      = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.client.name} — {self.piece_type} [{self.status}]"


class DesignBriefStatus(models.TextChoices):
    DRAFT    = "draft",    "Draft"
    SENT     = "sent",     "Sent to Client"
    REVISION = "revision", "Under Revision"
    APPROVED = "approved", "Approved by Client"
    REJECTED = "rejected", "Rejected"


class DesignBrief(models.Model):
    """
    Versioned design briefs. Only one APPROVED brief can exist per job.
    Approval triggers Job Card unlock (with deposit confirmation).
    """
    job             = models.ForeignKey("core.Job", on_delete=models.CASCADE, related_name="design_briefs")
    version         = models.PositiveIntegerField(default=1)
    title           = models.CharField(max_length=200)
    description     = models.TextField(help_text="Full design specification")
    dimensions      = models.CharField(max_length=200, blank=True, help_text="L × W × H in mm or cm")
    primary_species = models.CharField(max_length=100, blank=True, help_text="e.g. Mvule, Mahogany, Pine")
    finish          = models.CharField(max_length=100, blank=True, help_text="e.g. Natural oil, Teak oil, Paint")
    attachments_url = models.URLField(blank=True, help_text="Cloudinary folder URL or design render link")
    status          = models.CharField(max_length=20, choices=DesignBriefStatus.choices,
                                       default=DesignBriefStatus.DRAFT)
    approved_at     = models.DateTimeField(null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version"]
        unique_together = [["job", "version"]]

    def __str__(self):
        return f"{self.job.job_id} Brief v{self.version} [{self.status}]"


class InteractionChannel(models.TextChoices):
    WHATSAPP  = "whatsapp",  "WhatsApp"
    PHONE     = "phone",     "Phone Call"
    EMAIL     = "email",     "Email"
    SITE      = "site",      "Website"
    IN_PERSON = "in_person", "In Person"
    SMS       = "sms",       "SMS"


class Interaction(models.Model):
    client     = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, related_name="interactions")
    job        = models.ForeignKey("core.Job", on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="interactions")
    channel    = models.CharField(max_length=20, choices=InteractionChannel.choices)
    note       = models.TextField(help_text="Summary of the interaction")
    created_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.client.name} via {self.channel} — {self.created_at:%Y-%m-%d}"
