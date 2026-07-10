"""
Production app — the Material-to-Margin Intelligence (MMI) Engine.

JobCard is the operational view of a Job. BOMEntry records (Timber, Hardware, Labour)
exist in two states: ESTIMATED (from Quote) and ACTUAL (from workshop).
Signals auto-sync actual_cogs to the parent Job on every BOMEntry save/delete.
"""
from decimal import Decimal
from django.db import models
from django.utils import timezone


class BOMState(models.TextChoices):
    ESTIMATED = "estimated", "Estimated (from Quote)"
    ACTUAL    = "actual",    "Actual (Workshop Record)"


class TimberSpecies(models.TextChoices):
    MAHOGANY = "mahogany", "Mahogany (Meliaceae)"
    MVULE    = "mvule",    "Mvule / African Teak"
    PINE     = "pine",     "Pine (Softwood)"
    CEDAR    = "cedar",    "East African Cedar"
    ELGON    = "elgon",    "Elgon Olive"
    CAMPHOR  = "camphor",  "Camphor"
    NANDI    = "nandi",    "Nandi Flame"
    OTHER    = "other",    "Other / Mixed"


class JobCard(models.Model):
    """
    Workshop job card — links the client's Job to physical production.
    is_locked=True until: (a) DesignBrief APPROVED + (b) deposit confirmed.
    """
    job              = models.OneToOneField("core.Job", on_delete=models.CASCADE, related_name="job_card")
    is_locked        = models.BooleanField(default=True, help_text="Locked until brief approved + deposit paid")
    unlocked_at      = models.DateTimeField(null=True, blank=True)
    unlocked_by      = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True)
    workshop_notes   = models.TextField(blank=True)
    start_date       = models.DateField(null=True, blank=True)
    target_completion = models.DateField(null=True, blank=True)
    actual_completion = models.DateField(null=True, blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Job Card"

    def __str__(self):
        lock = "🔒" if self.is_locked else "🔓"
        return f"{lock} {self.job.job_id}"

    def unlock(self, user):
        """
        Gate: brief must be APPROVED and deposit payment CONFIRMED.
        Returns (True, "") on success or (False, reason) on failure.
        """
        job = self.job
        brief_approved = job.design_briefs.filter(status="approved").exists()
        from ledger.models import PaymentStatus
        deposit_paid = False
        try:
            invoice = job.invoice
            deposit_paid = invoice.payments.filter(
                status=PaymentStatus.CONFIRMED,
                amount__gte=job.quote.deposit_amount
            ).exists()
        except Exception:
            pass

        if not brief_approved:
            return False, "No approved Design Brief found for this job."
        if not deposit_paid:
            return False, "Deposit payment not yet confirmed."

        self.is_locked = False
        self.unlocked_at = timezone.now()
        self.unlocked_by = user
        self.save()

        from core.models import JobStatus
        if job.status == JobStatus.DEPOSIT_PAID:
            job.status = JobStatus.IN_PRODUCTION
            job.save()

        return True, "Job Card unlocked. Production can begin."


class TimberEntry(models.Model):
    """Timber consumption record — the primary COGS driver for hardwood commissions."""
    job_card      = models.ForeignKey(JobCard, on_delete=models.CASCADE, related_name="timber_entries")
    species       = models.CharField(max_length=20, choices=TimberSpecies.choices)
    board_feet    = models.DecimalField(max_digits=8, decimal_places=3,
                                        help_text="Board feet consumed (1 BF = 1ft × 1ft × 1in)")
    unit_cost_per_bf = models.DecimalField(max_digits=10, decimal_places=2,
                                           help_text="KES per board foot (locked from PO receipt if linked)")
    total_cost    = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"),
                                        editable=False)
    supplier      = models.ForeignKey("partners.SupplierProfile", on_delete=models.SET_NULL,
                                      null=True, blank=True)
    purchase_order = models.ForeignKey("partners.PurchaseOrder", on_delete=models.SET_NULL,
                                       null=True, blank=True, related_name="timber_entries")
    state         = models.CharField(max_length=15, choices=BOMState.choices, default=BOMState.ESTIMATED)
    date_purchased = models.DateField(null=True, blank=True)
    notes         = models.TextField(blank=True)

    class Meta:
        verbose_name = "Timber Entry"
        verbose_name_plural = "Timber Entries"

    def save(self, *args, **kwargs):
        self.total_cost = (self.board_feet * self.unit_cost_per_bf).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_species_display()} — {self.board_feet} BF @ KES {self.unit_cost_per_bf} [{self.state}]"


class HardwareEntry(models.Model):
    """Hardware and fittings — hinges, screws, glass, upholstery foam, etc."""
    job_card      = models.ForeignKey(JobCard, on_delete=models.CASCADE, related_name="hardware_entries")
    item_name     = models.CharField(max_length=200, help_text="e.g. Piano hinge 3-inch, M6 bolt")
    quantity      = models.DecimalField(max_digits=8, decimal_places=2)
    unit_cost     = models.DecimalField(max_digits=10, decimal_places=2, help_text="KES per unit")
    total_cost    = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"),
                                        editable=False)
    supplier      = models.ForeignKey("partners.SupplierProfile", on_delete=models.SET_NULL,
                                      null=True, blank=True)
    purchase_order = models.ForeignKey("partners.PurchaseOrder", on_delete=models.SET_NULL,
                                       null=True, blank=True, related_name="hardware_entries")
    state         = models.CharField(max_length=15, choices=BOMState.choices, default=BOMState.ESTIMATED)
    date_purchased = models.DateField(null=True, blank=True)
    notes         = models.TextField(blank=True)

    class Meta:
        verbose_name = "Hardware Entry"
        verbose_name_plural = "Hardware Entries"

    def save(self, *args, **kwargs):
        self.total_cost = (self.quantity * self.unit_cost).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item_name} × {self.quantity} @ KES {self.unit_cost} [{self.state}]"


class LaborEntry(models.Model):
    """Artisan piece-rate or hourly labour entries."""
    job_card          = models.ForeignKey(JobCard, on_delete=models.CASCADE, related_name="labor_entries")
    artisan           = models.ForeignKey("partners.ArtisanProfile", on_delete=models.SET_NULL,
                                          null=True, blank=True)
    task_description  = models.CharField(max_length=300)
    piece_rate        = models.DecimalField(max_digits=10, decimal_places=2,
                                            help_text="KES for this task/piece")
    hours             = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True,
                                            help_text="Optional — for hourly billing verification")
    total_cost        = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"),
                                            editable=False)
    state             = models.CharField(max_length=15, choices=BOMState.choices, default=BOMState.ESTIMATED)
    work_date         = models.DateField(null=True, blank=True)
    notes             = models.TextField(blank=True)

    class Meta:
        verbose_name = "Labour Entry"
        verbose_name_plural = "Labour Entries"

    def save(self, *args, **kwargs):
        # Labour total = piece_rate (the amount agreed for this task)
        self.total_cost = self.piece_rate.quantize(Decimal("0.01"))
        super().save(*args, **kwargs)

    def __str__(self):
        artisan = self.artisan.name if self.artisan else "Unassigned"
        return f"{artisan} — {self.task_description} KES {self.piece_rate} [{self.state}]"
