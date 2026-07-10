"""
Ledger signals — keep Invoice.status in sync after each Payment save.

Connected via LedgerConfig.ready() so all models are guaranteed loaded.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Sum


@receiver(post_save, sender="ledger.Payment")
def sync_invoice_status(sender, instance, **kwargs):
    """
    After any Payment is saved, recalculate the parent Invoice's
    paid status based on the sum of all CONFIRMED payments.
    State transitions (one-way):
        DRAFT / SENT → PARTIALLY_PAID → PAID
    CANCELLED invoices are never touched.
    """
    from ledger.models import Invoice, InvoiceStatus, PaymentStatus

    invoice = instance.invoice
    if invoice.status == InvoiceStatus.CANCELLED:
        return

    confirmed_total = (
        invoice.payments
               .filter(status=PaymentStatus.CONFIRMED)
               .aggregate(t=Sum("amount"))["t"]
        or 0
    )

    if confirmed_total >= invoice.total:
        new_status = InvoiceStatus.PAID
        # Back-fill Job quoted_price and gross_profit from the confirmed invoice
        job = invoice.job
        job.quoted_price = invoice.total
        job.gross_profit = invoice.total - job.actual_cogs
        job.save(update_fields=["quoted_price", "gross_profit", "updated_at"])
    elif confirmed_total > 0:
        new_status = InvoiceStatus.PARTIALLY_PAID
    else:
        new_status = InvoiceStatus.SENT

    if invoice.status != new_status:
        invoice.status = new_status
        invoice.save(update_fields=["status"])
