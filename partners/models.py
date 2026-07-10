"""
Partners app — supplier registry, purchase orders, artisan profiles.

Key invariant:
  PurchaseOrder.unit_cost_at_receipt is locked when status → RECEIVED.
  A post_save signal in production/signals.py propagates this locked price
  to all linked ESTIMATED BOMEntry records, converting them to ACTUAL state.
"""
from decimal import Decimal
from django.db import models
from django.utils import timezone


class MaterialType(models.TextChoices):
    TIMBER     = "timber",     "Timber"
    HARDWARE   = "hardware",   "Hardware & Fittings"
    UPHOLSTERY = "upholstery", "Upholstery Fabric"
    FINISH     = "finish",     "Finishes & Oils"
    ADHESIVES  = "adhesives",  "Adhesives & Chemicals"
    OTHER      = "other",      "Other"


class SupplierLocation(models.TextChoices):
    GIKOMBA = "gikomba", "Gikomba Market"
    NGARA   = "ngara",   "Ngara"
    NGONG   = "ngong",   "Ngong Road"
    MOMBASA = "mombasa", "Mombasa Road"
    OTHER   = "other",   "Other"


class SupplierProfile(models.Model):
    name          = models.CharField(max_length=200)
    contact_name  = models.CharField(max_length=100, blank=True)
    phone         = models.CharField(max_length=20)
    email         = models.EmailField(blank=True)
    material_type = models.CharField(max_length=20, choices=MaterialType.choices)
    location      = models.CharField(max_length=20, choices=SupplierLocation.choices,
                                     default=SupplierLocation.GIKOMBA)
    current_rate  = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"),
        help_text="Current price per BF (timber) or per unit (hardware) in KES"
    )
    notes         = models.TextField(blank=True)
    is_active     = models.BooleanField(default=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Supplier"

    def __str__(self):
        return f"{self.name} ({self.get_material_type_display()})"

    def update_rate(self, new_rate, user=None):
        """Update current rate and record the change in history."""
        SupplierRateHistory.objects.create(
            supplier=self, rate=self.current_rate,
            effective_until=timezone.now(), recorded_by=user
        )
        self.current_rate = new_rate
        self.save()


class SupplierRateHistory(models.Model):
    """
    Historical rate log — allows reconstructing true COGS for any past job
    even after the supplier's current_rate has changed.
    """
    supplier        = models.ForeignKey(SupplierProfile, on_delete=models.CASCADE,
                                         related_name="rate_history")
    rate            = models.DecimalField(max_digits=10, decimal_places=2)
    effective_until = models.DateTimeField()
    recorded_by     = models.ForeignKey("auth.User", on_delete=models.SET_NULL,
                                         null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Supplier Rate History"

    def __str__(self):
        return f"{self.supplier.name} — KES {self.rate}/unit until {self.effective_until:%Y-%m-%d}"


class POStatus(models.TextChoices):
    RAISED    = "raised",    "Raised"
    CONFIRMED = "confirmed", "Confirmed by Supplier"
    RECEIVED  = "received",  "Goods Received"
    CANCELLED = "cancelled", "Cancelled"


def generate_po_number():
    now    = timezone.now()
    prefix = f"PO-{now.strftime('%m-%Y')}"
    last   = PurchaseOrder.objects.filter(po_number__startswith=prefix).order_by("-po_number").first()
    seq    = (int(last.po_number.split("-")[-1]) + 1) if last else 1
    return f"{prefix}-{seq:04d}"


class PurchaseOrder(models.Model):
    """
    Workshop PO raised to a supplier.
    Once RECEIVED, unit_cost_at_receipt is locked and propagated to linked
    BOMEntry records via the signal in production/signals.py.
    """
    po_number            = models.CharField(max_length=25, unique=True, editable=False)
    supplier             = models.ForeignKey(SupplierProfile, on_delete=models.PROTECT,
                                              related_name="purchase_orders")
    status               = models.CharField(max_length=15, choices=POStatus.choices,
                                             default=POStatus.RAISED)
    description          = models.TextField(help_text="Items ordered, quantities, specifications")
    estimated_amount     = models.DecimalField(max_digits=12, decimal_places=2,
                                               default=Decimal("0.00"))
    unit_cost_at_receipt = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Locked when goods are received — auto-propagated to linked BOM entries"
    )
    notes       = models.TextField(blank=True)
    raised_at   = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    received_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-raised_at"]
        verbose_name = "Purchase Order"

    def save(self, *args, **kwargs):
        if not self.po_number:
            self.po_number = generate_po_number()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.po_number} — {self.supplier.name} [{self.status}]"

    def mark_received(self, unit_cost, user=None):
        """Lock cost and save; signal propagates price to BOM entries."""
        self.status              = POStatus.RECEIVED
        self.unit_cost_at_receipt = unit_cost
        self.received_at         = timezone.now()
        self.save()


class ArtisanSpecialty(models.TextChoices):
    CARPENTRY  = "carpentry",  "Carpentry & Joinery"
    UPHOLSTERY = "upholstery", "Upholstery"
    FINISHING  = "finishing",  "Finishing & Polishing"
    CARVING    = "carving",    "Carving & Engraving"
    WELDING    = "welding",    "Metal & Welding"
    GENERAL    = "general",    "General Workshop"


class ArtisanProfile(models.Model):
    name            = models.CharField(max_length=150)
    phone           = models.CharField(max_length=20)
    specialty       = models.CharField(max_length=20, choices=ArtisanSpecialty.choices)
    base_piece_rate = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"),
        help_text="Default piece-rate per task in KES"
    )
    nssf_number = models.CharField(max_length=20, blank=True)
    is_active   = models.BooleanField(default=True)
    joined_at   = models.DateField(null=True, blank=True)
    notes       = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Artisan"

    def __str__(self):
        return f"{self.name} ({self.get_specialty_display()})"
