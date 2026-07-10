"""
Celery tasks for the Ledger app.

Tasks:
  - send_stk_push         : Trigger M-Pesa STK push for an invoice
  - refresh_compliance    : Recompute and persist the current month's compliance period
  - send_care_reminders   : Dispatch WhatsApp/SMS care schedule reminders
"""
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_stk_push(self, invoice_pk: int, phone: str):
    """
    Trigger an M-Pesa STK push for a given invoice.
    Retries up to 3 times with 30s delay on transient failure.
    """
    try:
        from ledger.models import Invoice
        from ledger.mpesa import stk_push

        invoice = Invoice.objects.get(pk=invoice_pk)
        result = stk_push(
            phone=phone,
            amount=invoice.balance_due,
            invoice_id=invoice.invoice_id,
            description="MN Studio Commission",
        )
        if "error" in result:
            raise Exception(result["error"])
        logger.info("STK push queued for invoice %s", invoice.invoice_id)
        return result
    except Exception as exc:
        logger.error("STK push task error: %s", exc)
        raise self.retry(exc=exc)


@shared_task
def refresh_compliance_period(year: int = None, month: int = None):
    """
    Recompute and save a compliance period record.
    Defaults to the current calendar month.
    """
    from ledger.compliance import save_period_to_db

    now   = timezone.now()
    year  = year  or now.year
    month = month or now.month
    period = save_period_to_db(year, month)
    logger.info("Compliance period saved: %s", period)
    return str(period)


@shared_task
def send_care_reminders():
    """
    Find care schedule items due in the next 7 days and send WhatsApp/SMS reminders.
    Marks notification_sent=True after dispatch.
    """
    import datetime
    from certificates.models import CareSchedule

    today = datetime.date.today()
    due_soon = CareSchedule.objects.filter(
        due_date__lte=today + datetime.timedelta(days=7),
        due_date__gte=today,
        notification_sent=False,
        completed=False,
    ).select_related("certificate__job__client")

    sent = 0
    for schedule in due_soon:
        client = schedule.certificate.job.client
        try:
            _send_whatsapp_reminder(
                phone=client.phone,
                name=client.name,
                piece=schedule.certificate.piece_name,
                care_type=schedule.get_care_type_display(),
                due_date=schedule.due_date,
            )
            schedule.notification_sent = True
            schedule.save(update_fields=["notification_sent"])
            sent += 1
        except Exception as e:
            logger.error("Failed to send care reminder to %s: %s", client.name, e)

    logger.info("Sent %d care reminders.", sent)
    return sent


def _send_whatsapp_reminder(phone: str, name: str, piece: str, care_type: str, due_date):
    """
    Send a WhatsApp message via Africa's Talking API.
    Falls back to SMS if WhatsApp delivery fails.
    """
    from django.conf import settings
    import requests

    message = (
        f"Hi {name}, your MN Studio piece '{piece}' is due for its "
        f"{care_type} on {due_date.strftime('%d %B %Y')}. "
        f"Reply HELP for care instructions or to book a maintenance visit."
    )

    if not settings.AT_API_KEY or settings.AT_API_KEY == "":
        logger.warning("Africa's Talking API key not configured. Skipping notification.")
        return

    url = "https://voice.africastalking.com/whatsapp/message"
    headers = {"ApiKey": settings.AT_API_KEY, "Content-Type": "application/json"}
    payload = {
        "username": settings.AT_USERNAME,
        "to":       phone if phone.startswith("+") else f"+{phone}",
        "message":  message,
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error("WhatsApp send failed, attempting SMS: %s", e)
        _send_sms_fallback(phone=phone, message=message, settings=settings)


def _send_sms_fallback(phone, message, settings):
    """Africa's Talking SMS fallback."""
    import requests
    url = "https://api.africastalking.com/version1/messaging"
    headers = {"ApiKey": settings.AT_API_KEY, "Content-Type": "application/x-www-form-urlencoded"}
    data = {"username": settings.AT_USERNAME, "to": phone, "message": message}
    requests.post(url, data=data, headers=headers, timeout=10)
