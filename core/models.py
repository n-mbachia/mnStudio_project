"""
Core models — the universal anchor for the MN Studio platform.

Job is the central entity. Every module (CRM, Production, Ledger, Certificates)
holds a ForeignKey or OneToOneField to Job. This is what prevents the data traps
of disconnected modules described in the architecture review.
"""
from decimal import Decimal
from django.db import models
from django.utils import timezone


class JobStatus(models.TextChoices):
    BRIEF_RECEIVED = "brief_received", "Brief Received"
    QUOTE_SENT     = "quote_sent",     "Quote Sent"
    QUOTE_APPROVED = "quote_approved", "Quote Approved"
    DEPOSIT_PAID   = "deposit_paid",   "Deposit Paid"
    IN_PRODUCTION  = "in_production",  "In Production"
    QUALITY_REVIEW = "quality_review", "Quality Review"
    READY_DELIVERY = "ready_delivery", "Ready for Delivery"
    DELIVERED      = "delivered",      "Delivered"
    COMPLETED      = "completed",      "Completed"
    CANCELLED      = "cancelled",      "Cancelled"


def generate_job_id():
    """Generate sequential Job ID: JC-MM-DD-YYYY-NNNN"""
    now    = timezone.now()
    prefix = f"JC-{now.strftime('%m-%d-%Y')}"
    last   = Job.objects.filter(job_id__startswith=prefix).order_by("-job_id").first()
    seq    = (int(last.job_id.split("-")[-1]) + 1) if last else 1
    return f"{prefix}-{seq:04d}"


class Job(models.Model):
    """
    Central entity — every commission starts here.
    Financial fields are updated by signals in production/signals.py and
    ledger/signals.py; never computed on-the-fly in views or templates.
    """
    job_id         = models.CharField(max_length=25, unique=True, editable=False)
    client         = models.ForeignKey("crm.ClientProfile", on_delete=models.PROTECT,
                                       related_name="jobs")
    status         = models.CharField(max_length=30, choices=JobStatus.choices,
                                      default=JobStatus.BRIEF_RECEIVED)
    description    = models.TextField(blank=True,
                                      help_text="Brief summary of the commission")
    # Financial snapshot — maintained by signals, NOT computed in views
    estimated_cogs = models.DecimalField(max_digits=12, decimal_places=2,
                                          default=Decimal("0.00"))
    actual_cogs    = models.DecimalField(max_digits=12, decimal_places=2,
                                          default=Decimal("0.00"))
    quoted_price   = models.DecimalField(max_digits=12, decimal_places=2,
                                          default=Decimal("0.00"))
    gross_profit   = models.DecimalField(max_digits=12, decimal_places=2,
                                          default=Decimal("0.00"))
    target_margin  = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("40.00"),
        help_text="Target gross margin percentage"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Job"
        verbose_name_plural = "Jobs"

    def save(self, *args, **kwargs):
        if not self.job_id:
            self.job_id = generate_job_id()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.job_id} — {self.client}"

    @property
    def actual_margin_pct(self):
        if self.quoted_price:
            return (self.gross_profit / self.quoted_price * 100).quantize(Decimal("0.01"))
        return Decimal("0.00")

    @property
    def is_profitable(self):
        return self.gross_profit > 0

    @property
    def cogs_variance(self):
        """Positive = under estimated COGS (good). Negative = cost overrun (bad)."""
        return self.estimated_cogs - self.actual_cogs


class AuditLog(models.Model):
    """Lightweight, append-only audit trail for critical state changes."""
    job        = models.ForeignKey(Job, on_delete=models.CASCADE,
                                   related_name="audit_logs", null=True, blank=True)
    user       = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True)
    action     = models.CharField(max_length=100)
    detail     = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Audit Log"

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} | {self.action}"
