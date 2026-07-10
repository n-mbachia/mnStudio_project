"""
Production signals — COGS auto-sync to parent Job on every BOMEntry change.

Architecture:
  - Timber / Hardware / Labour saves  →  recalculate_job_cogs()
  - PurchaseOrder RECEIVED            →  propagate locked price to BOM entries
  - All monetary math uses Decimal

Senders use lazy string references ("app.Model") which Django resolves
after all apps are loaded (safe because signals are imported in AppConfig.ready()).
"""
from decimal import Decimal

from django.db.models.signals import post_save, post_delete
from django.db.models import Sum
from django.dispatch import receiver


# ── Core recalculation helper ─────────────────────────────────────────────

def recalculate_job_cogs(job_card):
    """
    Recompute estimated + actual COGS for the Job attached to job_card.
    Called from every BOMEntry signal handler.
    """
    # Import here to avoid circular dependency at module load time
    from production.models import TimberEntry, HardwareEntry, LaborEntry

    def _sum(model, state):
        return (
            model.objects
                 .filter(job_card=job_card, state=state)
                 .aggregate(t=Sum("total_cost"))["t"]
            or Decimal("0.00")
        )

    estimated_cogs = (
        _sum(TimberEntry,   "estimated") +
        _sum(HardwareEntry, "estimated") +
        _sum(LaborEntry,    "estimated")
    )
    actual_cogs = (
        _sum(TimberEntry,   "actual") +
        _sum(HardwareEntry, "actual") +
        _sum(LaborEntry,    "actual")
    )

    job = job_card.job
    job.estimated_cogs = estimated_cogs
    job.actual_cogs    = actual_cogs
    job.gross_profit   = job.quoted_price - actual_cogs
    job.save(update_fields=["estimated_cogs", "actual_cogs", "gross_profit", "updated_at"])

    # Mirror into the ledger COGSRecord
    try:
        from ledger.models import COGSRecord
        record, _ = COGSRecord.objects.get_or_create(job=job)
        record.estimated_cogs = estimated_cogs
        record.actual_cogs    = actual_cogs
        record.variance       = estimated_cogs - actual_cogs
        record.save(update_fields=["estimated_cogs", "actual_cogs", "variance", "last_updated"])
    except Exception:
        pass


# ── Timber signals ────────────────────────────────────────────────────────

@receiver(post_save,   sender="production.TimberEntry")
def timber_saved(sender, instance, **kwargs):
    recalculate_job_cogs(instance.job_card)


@receiver(post_delete, sender="production.TimberEntry")
def timber_deleted(sender, instance, **kwargs):
    recalculate_job_cogs(instance.job_card)


# ── Hardware signals ──────────────────────────────────────────────────────

@receiver(post_save,   sender="production.HardwareEntry")
def hardware_saved(sender, instance, **kwargs):
    recalculate_job_cogs(instance.job_card)


@receiver(post_delete, sender="production.HardwareEntry")
def hardware_deleted(sender, instance, **kwargs):
    recalculate_job_cogs(instance.job_card)


# ── Labour signals ────────────────────────────────────────────────────────

@receiver(post_save,   sender="production.LaborEntry")
def labor_saved(sender, instance, **kwargs):
    recalculate_job_cogs(instance.job_card)


@receiver(post_delete, sender="production.LaborEntry")
def labor_deleted(sender, instance, **kwargs):
    recalculate_job_cogs(instance.job_card)


# ── Purchase Order received → propagate locked price ─────────────────────

@receiver(post_save, sender="partners.PurchaseOrder")
def po_received_propagate(sender, instance, **kwargs):
    """
    When a PO is marked RECEIVED, lock its unit_cost_at_receipt to all
    linked ESTIMATED BOMEntry records and transition them to ACTUAL.
    """
    if instance.status != "received" or not instance.unit_cost_at_receipt:
        return

    from production.models import TimberEntry, HardwareEntry

    updated_timber = TimberEntry.objects.filter(
        purchase_order=instance, state="estimated"
    )
    for entry in updated_timber:
        entry.unit_cost_per_bf = instance.unit_cost_at_receipt
        entry.state = "actual"
        entry.save()

    updated_hardware = HardwareEntry.objects.filter(
        purchase_order=instance, state="estimated"
    )
    for entry in updated_hardware:
        entry.unit_cost = instance.unit_cost_at_receipt
        entry.state = "actual"
        entry.save()
