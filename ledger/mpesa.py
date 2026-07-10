"""
M-Pesa Daraja API service — STK Push and OAuth token management.

Usage:
    from ledger.mpesa import stk_push
    result = stk_push(phone="254712345678", amount=5000, invoice_id="INV-06-2025-0001")
"""
import base64
import json
import logging
from datetime import datetime
from decimal import Decimal

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

SANDBOX_BASE = "https://sandbox.safaricom.co.ke"
LIVE_BASE    = "https://api.safaricom.co.ke"


def _base_url():
    return SANDBOX_BASE if settings.MPESA_ENVIRONMENT == "sandbox" else LIVE_BASE


def _get_access_token() -> str:
    """Fetch a short-lived OAuth token from Daraja."""
    url = f"{_base_url()}/oauth/v1/generate?grant_type=client_credentials"
    creds = base64.b64encode(
        f"{settings.MPESA_CONSUMER_KEY}:{settings.MPESA_CONSUMER_SECRET}".encode()
    ).decode()
    resp = requests.get(url, headers={"Authorization": f"Basic {creds}"}, timeout=10)
    resp.raise_for_status()
    return resp.json()["access_token"]


def _generate_password() -> tuple[str, str]:
    """Return (password, timestamp) for STK push."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    raw = f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}"
    password = base64.b64encode(raw.encode()).decode()
    return password, timestamp


def stk_push(phone: str, amount: Decimal | int, invoice_id: str, description: str = "MN Studio Payment") -> dict:
    """
    Initiate a Safaricom STK Push (Lipa na M-Pesa Online).

    Args:
        phone:       Kenyan phone number with country code, no +. e.g. "254712345678"
        amount:      Amount in KES (integer, no decimals)
        invoice_id:  Used as AccountReference and stored for callback matching
        description: Short description shown on the M-Pesa prompt

    Returns:
        dict with Daraja API response (contains CheckoutRequestID on success)
    """
    token = _get_access_token()
    password, timestamp = _generate_password()
    url = f"{_base_url()}/mpesa/stkpush/v1/processrequest"

    payload = {
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password":          password,
        "Timestamp":         timestamp,
        "TransactionType":   "CustomerPayBillOnline",
        "Amount":            int(amount),
        "PartyA":            phone,
        "PartyB":            settings.MPESA_SHORTCODE,
        "PhoneNumber":       phone,
        "CallBackURL":       settings.MPESA_CALLBACK_URL,
        "AccountReference":  invoice_id[:12],  # Daraja limit
        "TransactionDesc":   description[:13],
    }

    try:
        resp = requests.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=15,
        )
        data = resp.json()
        logger.info("STK push for %s: %s", invoice_id, data.get("ResponseDescription", ""))
        return data
    except requests.RequestException as e:
        logger.error("STK push failed for %s: %s", invoice_id, e)
        return {"error": str(e)}
