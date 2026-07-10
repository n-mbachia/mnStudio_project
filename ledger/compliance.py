"""
MN Studio Statutory Compliance Service — STATELESS, SIDE-EFFECT FREE.

Kenyan obligations for a sole-proprietor bespoke furniture studio:

  ┌─────────────────────────────────────────────────────────┐
  │ Obligation          Base          Rate   Frequency      │
  ├─────────────────────────────────────────────────────────┤
  │ TOT                 Gross Sales   1.5%   Monthly        │
  │ AHL                 Gross Sales   1.5%   Monthly        │
  │ Retirement Savings  Gross Profit  10%    Monthly        │
  │ SACCO Savings       Gross Profit  10%    Monthly        │
  └─────────────────────────────────────────────────────────┘

CRITICAL:
  - AHL and TOT use GROSS SALES as their base.
  - Retirement and SACCO use GROSS PROFIT as their base.
  These are the most commonly mis-coded rules in this system.

Cash basis:
  Payment.paid_at determines the period — NOT Invoice.issued_at.
  An invoice raised in March but paid in April hits April's compliance period.
"""
import calendar
from decimal import Decimal, ROUND_HALF_UP


def _cents(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def compute_period_obligations(year: int, month: int) -> dict:
    """
    Compute all statutory obligations for a given calendar month.

    Args:
        year:  Calendar year  (e.g. 2025)
        month: Calendar month (1–12)

    Returns:
        dict with keys: year, month, month_label, gross_sales, cogs,
        gross_profit, tot, ahl, retirement_savings, sacco_savings,
        total_obligations, days_in_period
    """
    from django.db.models import Sum
    from ledger.models import Payment, PaymentStatus, COGSRecord

    # ── Gross sales (cash basis) ──────────────────────────────────────────
    gross_sales = _cents(
        Payment.objects
               .filter(paid_at__year=year, paid_at__month=month,
                       status=PaymentStatus.CONFIRMED)
               .aggregate(t=Sum("amount"))["t"]
        or Decimal("0.00")
    )

    # ── COGS: actual cost of jobs whose invoices were paid this period ────
    cogs = _cents(
        COGSRecord.objects
                  .filter(
                      job__invoice__payments__paid_at__year=year,
                      job__invoice__payments__paid_at__month=month,
                      job__invoice__payments__status=PaymentStatus.CONFIRMED,
                  )
                  .aggregate(t=Sum("actual_cogs"))["t"]
        or Decimal("0.00")
    )

    gross_profit = _cents(max(gross_sales - cogs, Decimal("0.00")))

    # ── Statutory calculations ────────────────────────────────────────────
    # TOT and AHL  →  % of GROSS SALES
    tot = _cents(gross_sales * Decimal("0.015"))
    ahl = _cents(gross_sales * Decimal("0.015"))

    # Retirement and SACCO  →  % of GROSS PROFIT
    retirement = _cents(gross_profit * Decimal("0.10"))
    sacco      = _cents(gross_profit * Decimal("0.10"))

    total_obligations = _cents(tot + ahl + retirement + sacco)

    return {
        "year":               year,
        "month":              month,
        "month_label":        f"{calendar.month_name[month]} {year}",
        "gross_sales":        gross_sales,
        "cogs":               cogs,
        "gross_profit":       gross_profit,
        "tot":                tot,
        "ahl":                ahl,
        "retirement_savings": retirement,
        "sacco_savings":      sacco,
        "total_obligations":  total_obligations,
        "days_in_period":     calendar.monthrange(year, month)[1],
    }


def save_period_to_db(year: int, month: int):
    """Compute and persist (upsert) a CompliancePeriod record."""
    from ledger.models import CompliancePeriod
    data = compute_period_obligations(year, month)
    period, _ = CompliancePeriod.objects.update_or_create(
        year=year, month=month,
        defaults={
            "gross_sales":        data["gross_sales"],
            "cogs":               data["cogs"],
            "gross_profit":       data["gross_profit"],
            "tot":                data["tot"],
            "ahl":                data["ahl"],
            "retirement_savings": data["retirement_savings"],
            "sacco_savings":      data["sacco_savings"],
            "total_obligations":  data["total_obligations"],
        }
    )
    return period
