"""
Ledger app — Quotes, Invoices, Payments, COGS Records, Compliance Periods.

Financial rules:
- All monetary fields use DecimalField — never FloatField.
- Invoices are immutable once PAID; corrections use credit notes.
- Payment.paid_at drives compliance period assignment (cash basis).
- Compliance bases: TOT/AHL on gross_sales; Retirement/SACCO on gross_profit.
"""
from decimal import Decimal
from django.db import models
from django.db.models import Sum
from django.utils import timezone


class QuoteStatus(models.TextChoices):
    DRAFT       = "draft",       "Draft"
    SENT        = "sent",        "Sent to Client"
    NEGOTIATING = "negotiating", "Under Negotiation"
    APPROVED    = "approved",    "Approved"
    EXPIRED     = "expired",     "Expired"
    DECLINED    = "declined",    "Declined"


def generate_quote_id():
    now = timezone.now()
    prefix = f"QT-{now.strftime('%m-%Y')}"
    last = Quote.objects.filter(quote_id__startswith=prefix).order_by("-quote_id").first()
    seq = (int(last.quote_id.split("-")[-1]) + 1) if last else 1
    return f"{prefix}-{seq:04d}"


class Quote(models.Model):
    quote_id       = models.CharField(max_length=20, unique=True, editable=False)
    client         = models.ForeignKey("crm.ClientProfile", on_delete=models.PROTECT,
                                       related_name="quotes")
    job            = models.OneToOneField("core.Job", on_delete=models.SET_NULL,
                                          null=True, blank=True, related_name="quote")
    status         = models.CharField(max_length=15, choices=QuoteStatus.choices,
                                      default=QuoteStatus.DRAFT)
    notes          = models.TextField(blank=True)
    subtotal       = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount       = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total          = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    deposit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"),
                                         help_text="Deposit required before production starts (typically 50%)")
    valid_until    = models.DateField(null=True, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    sent_at        = models.DateTimeField(null=True, blank=True)
    approved_at    = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Quote"

    def save(self, *args, **kwargs):
        if not self.quote_id:
            self.quote_id = generate_quote_id()
        if self.pk:
            self.subtotal = self.line_items.aggregate(t=Sum("total"))["t"] or Decimal("0.00")
        self.total = max(self.subtotal - self.discount, Decimal("0.00"))
        if not self.deposit_amount and self.total:
            self.deposit_amount = (self.total * Decimal("0.50")).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quote_id} — {self.client.name} [KES {self.total}]"

    def recalculate(self):
        self.subtotal = self.line_items.aggregate(t=Sum("total"))["t"] or Decimal("0.00")
        self.total    = max(self.subtotal - self.discount, Decimal("0.00"))
        self.save(update_fields=["subtotal", "total"])


class QuoteLineItem(models.Model):
    quote       = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="line_items")
    description = models.CharField(max_length=300)
    quantity    = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("1.00"))
    unit_price  = models.DecimalField(max_digits=12, decimal_places=2)
    total       = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"),
                                      editable=False)

    def save(self, *args, **kwargs):
        self.total = (self.quantity * self.unit_price).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)
        self.quote.recalculate()

    def __str__(self):
        return f"{self.description} × {self.quantity} = KES {self.total}"


class InvoiceStatus(models.TextChoices):
    DRAFT          = "draft",          "Draft"
    SENT           = "sent",           "Sent"
    PARTIALLY_PAID = "partially_paid", "Partially Paid"
    PAID           = "paid",           "Fully Paid"
    CANCELLED      = "cancelled",      "Cancelled"


def generate_invoice_id():
    now = timezone.now()
    prefix = f"INV-{now.strftime('%m-%Y')}"
    last = Invoice.objects.filter(invoice_id__startswith=prefix).order_by("-invoice_id").first()
    seq = (int(last.invoice_id.split("-")[-1]) + 1) if last else 1
    return f"{prefix}-{seq:04d}"


class Invoice(models.Model):
    invoice_id  = models.CharField(max_length=22, unique=True, editable=False)
    job         = models.OneToOneField("core.Job", on_delete=models.PROTECT,
                                       related_name="invoice")
    client      = models.ForeignKey("crm.ClientProfile", on_delete=models.PROTECT,
                                    related_name="invoices")
    status      = models.CharField(max_length=20, choices=InvoiceStatus.choices,
                                   default=InvoiceStatus.DRAFT)
    notes       = models.TextField(blank=True)
    subtotal    = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total       = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    issued_at   = models.DateTimeField(null=True, blank=True)
    due_at      = models.DateField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Invoice"

    def save(self, *args, **kwargs):
        if not self.invoice_id:
            self.invoice_id = generate_invoice_id()
        if self.pk:
            self.subtotal = self.line_items.aggregate(t=Sum("total"))["t"] or Decimal("0.00")
        self.total = self.subtotal
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.invoice_id} — {self.client.name} [KES {self.total}]"

    @property
    def amount_paid(self):
        return (
            self.payments
                .filter(status=PaymentStatus.CONFIRMED)
                .aggregate(t=Sum("amount"))["t"]
            or Decimal("0.00")
        )

    @property
    def balance_due(self):
        return max(self.total - self.amount_paid, Decimal("0.00"))

    def recalculate(self):
        self.subtotal = self.line_items.aggregate(t=Sum("total"))["t"] or Decimal("0.00")
        self.total    = self.subtotal
        self.save(update_fields=["subtotal", "total"])


class InvoiceLineItem(models.Model):
    invoice     = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="line_items")
    description = models.CharField(max_length=300)
    quantity    = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("1.00"))
    unit_price  = models.DecimalField(max_digits=12, decimal_places=2)
    total       = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"),
                                      editable=False)

    def save(self, *args, **kwargs):
        self.total = (self.quantity * self.unit_price).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)
        self.invoice.recalculate()

    def __str__(self):
        return f"{self.description} × {self.quantity} = KES {self.total}"


class PaymentMethod(models.TextChoices):
    MPESA = "mpesa", "M-Pesa"
    BANK  = "bank",  "Bank Transfer"
    CASH  = "cash",  "Cash"


class PaymentStatus(models.TextChoices):
    PENDING   = "pending",   "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    FAILED    = "failed",    "Failed"


class Payment(models.Model):
    """
    Cash-basis record. paid_at (not invoice.issued_at)
    determines which compliance period this payment belongs to.
    """
    invoice     = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="payments")
    amount      = models.DecimalField(max_digits=12, decimal_places=2)
    method      = models.CharField(max_length=10, choices=PaymentMethod.choices,
                                   default=PaymentMethod.MPESA)
    mpesa_ref   = models.CharField(max_length=50, blank=True,
                                   help_text="M-Pesa transaction receipt number")
    status      = models.CharField(max_length=15, choices=PaymentStatus.choices,
                                   default=PaymentStatus.PENDING)
    paid_at     = models.DateTimeField(default=timezone.now,
                                       help_text="Actual collection date — drives compliance period")
    recorded_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL,
                                    null=True, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-paid_at"]
        verbose_name = "Payment"

    def __str__(self):
        return f"KES {self.amount} via {self.method} [{self.status}] — {self.invoice.invoice_id}"


class COGSRecord(models.Model):
    """
    Ledger-side COGS snapshot synced from production.signals on every BOMEntry save.
    One record per Job; updated in-place (not versioned).
    """
    job            = models.OneToOneField("core.Job", on_delete=models.CASCADE,
                                          related_name="cogs_record")
    estimated_cogs = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    actual_cogs    = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    variance       = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"),
        help_text="Positive = under-spent vs estimate (good). Negative = cost overrun (bad)."
    )
    last_updated   = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "COGS Record"

    def __str__(self):
        return f"COGS {self.job.job_id}: est={self.estimated_cogs} act={self.actual_cogs}"


class CompliancePeriod(models.Model):
    """
    Persisted snapshot of monthly statutory obligations.
    Always recomputed via ledger.compliance.save_period_to_db() — never edited directly.

    Statutory bases (Kenyan law):
      TOT & AHL        → 1.5% of GROSS SALES
      Retirement/SACCO → 10%  of GROSS PROFIT
    """
    year               = models.PositiveIntegerField()
    month              = models.PositiveIntegerField()
    gross_sales        = models.DecimalField(max_digits=14, decimal_places=2,
                                             default=Decimal("0.00"))
    cogs               = models.DecimalField(max_digits=14, decimal_places=2,
                                             default=Decimal("0.00"))
    gross_profit       = models.DecimalField(max_digits=14, decimal_places=2,
                                             default=Decimal("0.00"))
    tot                = models.DecimalField(max_digits=12, decimal_places=2,
                                             default=Decimal("0.00"),
                                             help_text="Turnover Tax: 1.5% × gross sales")
    ahl                = models.DecimalField(max_digits=12, decimal_places=2,
                                             default=Decimal("0.00"),
                                             help_text="Affordable Housing Levy: 1.5% × gross sales")
    retirement_savings = models.DecimalField(max_digits=12, decimal_places=2,
                                             default=Decimal("0.00"),
                                             help_text="Owner retirement savings: 10% × gross profit")
    sacco_savings      = models.DecimalField(max_digits=12, decimal_places=2,
                                             default=Decimal("0.00"),
                                             help_text="Business SACCO savings: 10% × gross profit")
    total_obligations  = models.DecimalField(max_digits=12, decimal_places=2,
                                             default=Decimal("0.00"))
    is_finalised       = models.BooleanField(default=False)
    computed_at        = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [["year", "month"]]
        ordering        = ["-year", "-month"]
        verbose_name        = "Compliance Period"
        verbose_name_plural = "Compliance Periods"

    def __str__(self):
        return f"Compliance {self.year}-{self.month:02d} | KES {self.total_obligations}"
