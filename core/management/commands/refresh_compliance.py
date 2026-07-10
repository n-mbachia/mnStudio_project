"""
Management command: refresh_compliance
Recomputes and saves the current (or a specified) month's compliance period.

Usage:
    python manage.py refresh_compliance
    python manage.py refresh_compliance --year 2025 --month 5
"""
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Recompute and persist a compliance period."

    def add_arguments(self, parser):
        parser.add_argument("--year",  type=int, default=None)
        parser.add_argument("--month", type=int, default=None)

    def handle(self, *args, **options):
        from ledger.compliance import save_period_to_db, compute_period_obligations

        now   = timezone.now()
        year  = options["year"]  or now.year
        month = options["month"] or now.month

        data   = compute_period_obligations(year, month)
        period = save_period_to_db(year, month)

        self.stdout.write(f"\n📊 Compliance — {data['month_label']}")
        self.stdout.write(f"   Gross Sales:        KES {data['gross_sales']:,.2f}")
        self.stdout.write(f"   COGS:               KES {data['cogs']:,.2f}")
        self.stdout.write(f"   Gross Profit:       KES {data['gross_profit']:,.2f}")
        self.stdout.write(f"   TOT (1.5%):         KES {data['tot']:,.2f}")
        self.stdout.write(f"   AHL (1.5%):         KES {data['ahl']:,.2f}")
        self.stdout.write(f"   Retirement (10%):   KES {data['retirement_savings']:,.2f}")
        self.stdout.write(f"   SACCO (10%):        KES {data['sacco_savings']:,.2f}")
        self.stdout.write(f"   ─────────────────────────────────")
        self.stdout.write(f"   Total Obligations:  KES {data['total_obligations']:,.2f}")
        self.stdout.write(f"\n✅ Saved to CompliancePeriod pk={period.pk}\n")
