"""
Unit tests for the Ledger compliance engine.

These cover the most legally consequential function in the platform:
compute_period_obligations() — ensuring correct statutory bases.

Run: python manage.py test ledger.tests
"""
import datetime
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from unittest.mock import patch, MagicMock


class ComplianceServiceTest(TestCase):
    """
    Tests for ledger.compliance.compute_period_obligations().

    The critical rule being tested:
    - TOT and AHL use GROSS SALES as their base.
    - Retirement and SACCO use GROSS PROFIT as their base.
    These are the most commonly mis-coded rules in this type of system.
    """

    def _make_payment(self, amount, year=2025, month=6):
        from crm.models import ClientProfile
        from core.models import Job
        from ledger.models import Invoice, InvoiceLineItem, Payment, PaymentMethod, PaymentStatus

        client, _ = ClientProfile.objects.get_or_create(
            email=f"test_{amount}@mn.test",
            defaults={"name": "Test Client", "phone": "+254700000001"}
        )
        job = Job.objects.create(client=client, quoted_price=Decimal(str(amount)))
        invoice = Invoice.objects.create(job=job, client=client)
        InvoiceLineItem.objects.create(invoice=invoice, description="Test item",
                                        quantity=Decimal("1"), unit_price=Decimal(str(amount)))
        invoice.recalculate()
        import datetime
        Payment.objects.create(
            invoice=invoice, amount=Decimal(str(amount)),
            method=PaymentMethod.MPESA, status=PaymentStatus.CONFIRMED,
            paid_at = timezone.datetime(year, month, 15, tzinfo=datetime.timezone.utc),
        )
        return invoice

    def test_zero_sales_returns_zero_obligations(self):
        """If no payments exist, all obligations should be zero."""
        from ledger.compliance import compute_period_obligations
        result = compute_period_obligations(2025, 1)
        self.assertEqual(result["gross_sales"],        Decimal("0.00"))
        self.assertEqual(result["tot"],                Decimal("0.00"))
        self.assertEqual(result["ahl"],                Decimal("0.00"))
        self.assertEqual(result["retirement_savings"], Decimal("0.00"))
        self.assertEqual(result["sacco_savings"],      Decimal("0.00"))
        self.assertEqual(result["total_obligations"],  Decimal("0.00"))

    def test_tot_and_ahl_use_gross_sales_base(self):
        """TOT and AHL must be 1.5% of gross sales, NOT gross profit."""
        from ledger.compliance import compute_period_obligations
        self._make_payment(amount=100000, year=2025, month=6)
        result = compute_period_obligations(2025, 6)

        gross_sales = result["gross_sales"]
        self.assertEqual(gross_sales, Decimal("100000.00"))

        expected_tot = (gross_sales * Decimal("0.015")).quantize(Decimal("0.01"))
        expected_ahl = expected_tot  # same base and rate

        self.assertEqual(result["tot"], expected_tot,
                         "TOT must be 1.5% × gross_sales, not gross_profit")
        self.assertEqual(result["ahl"], expected_ahl,
                         "AHL must be 1.5% × gross_sales, not gross_profit")

    def test_retirement_and_sacco_use_gross_profit_base(self):
        """
        Retirement and SACCO must use GROSS PROFIT as base, not gross sales.
        This is the most critical correctness test in the system.
        """
        from ledger.compliance import compute_period_obligations
        # With no COGS records, gross_profit = gross_sales in test env
        self._make_payment(amount=80000, year=2025, month=7)
        result = compute_period_obligations(2025, 7)

        gross_profit = result["gross_profit"]
        expected_retirement = (gross_profit * Decimal("0.10")).quantize(Decimal("0.01"))
        expected_sacco      = expected_retirement

        self.assertEqual(result["retirement_savings"], expected_retirement,
                         "Retirement must be 10% × gross_profit, not gross_sales")
        self.assertEqual(result["sacco_savings"], expected_sacco,
                         "SACCO must be 10% × gross_profit, not gross_sales")

    def test_total_obligations_formula(self):
        """total_obligations = TOT + AHL + Retirement + SACCO."""
        from ledger.compliance import compute_period_obligations
        self._make_payment(amount=50000, year=2025, month=8)
        result = compute_period_obligations(2025, 8)

        expected = result["tot"] + result["ahl"] + result["retirement_savings"] + result["sacco_savings"]
        self.assertEqual(result["total_obligations"], expected,
                         "total_obligations must equal sum of all four components")

    def test_payment_date_not_invoice_date(self):
        """
        Payments collected in month B must hit month B's compliance period,
        even if the invoice was raised in month A.
        (Cash basis, not accrual.)
        """
        from ledger.compliance import compute_period_obligations
        from crm.models import ClientProfile
        from core.models import Job
        from ledger.models import Invoice, InvoiceLineItem, Payment, PaymentMethod, PaymentStatus

        client, _ = ClientProfile.objects.get_or_create(
            email="cashbasis@mn.test",
            defaults={"name": "Cash Basis Client", "phone": "+254700000099"}
        )
        job = Job.objects.create(client=client, quoted_price=Decimal("60000"))
        invoice = Invoice.objects.create(job=job, client=client)
        InvoiceLineItem.objects.create(invoice=invoice, description="Item",
                                        quantity=Decimal("1"), unit_price=Decimal("60000"))
        invoice.recalculate()

        # Invoice raised in September, payment arrives in October
        Payment.objects.create(
            invoice=invoice, amount=Decimal("60000"),
            method=PaymentMethod.BANK, status=PaymentStatus.CONFIRMED,
            paid_at = timezone.datetime(2025, 10, 5, tzinfo=datetime.timezone.utc),  # October
        )

        sep_result = compute_period_obligations(2025, 9)  # September — no payment
        oct_result = compute_period_obligations(2025, 10)  # October — payment here

        self.assertEqual(sep_result["gross_sales"], Decimal("0.00"),
                         "Invoice raised in Sep must NOT appear in Sep compliance (cash basis)")
        self.assertEqual(oct_result["gross_sales"], Decimal("60000.00"),
                         "Payment collected in Oct MUST appear in Oct compliance (cash basis)")

    def test_month_label_format(self):
        """month_label should return human-readable format."""
        from ledger.compliance import compute_period_obligations
        result = compute_period_obligations(2025, 6)
        self.assertEqual(result["month_label"], "June 2025")
        result2 = compute_period_obligations(2025, 1)
        self.assertEqual(result2["month_label"], "January 2025")

    def test_multiple_payments_aggregated(self):
        """Multiple confirmed payments in a month are aggregated correctly."""
        from ledger.compliance import compute_period_obligations
        self._make_payment(amount=30000, year=2025, month=11)
        self._make_payment(amount=45000, year=2025, month=11)
        result = compute_period_obligations(2025, 11)
        self.assertEqual(result["gross_sales"], Decimal("75000.00"))


class JobCOGSSignalTest(TestCase):
    """Tests for the production signals that auto-sync COGS to Job."""

    def test_timber_entry_updates_job_cogs(self):
        """Saving a TimberEntry (ACTUAL state) should update Job.actual_cogs."""
        from crm.models import ClientProfile
        from core.models import Job
        from production.models import JobCard, TimberEntry, BOMState, TimberSpecies
        from partners.models import SupplierProfile, MaterialType, SupplierLocation

        client, _ = ClientProfile.objects.get_or_create(
            email="cogs_test@mn.test",
            defaults={"name": "COGS Test", "phone": "+254700000002"}
        )
        job = Job.objects.create(client=client, quoted_price=Decimal("50000"))
        card = JobCard.objects.create(job=job, is_locked=False)
        supplier, _ = SupplierProfile.objects.get_or_create(
            name="Test Supplier",
            defaults={"phone": "+254700000003", "material_type": MaterialType.TIMBER,
                      "location": SupplierLocation.GIKOMBA, "current_rate": Decimal("400")}
        )

        self.assertEqual(job.actual_cogs, Decimal("0.00"))

        entry = TimberEntry.objects.create(
            job_card=card, species=TimberSpecies.MAHOGANY,
            board_feet=Decimal("10"), unit_cost_per_bf=Decimal("400"),
            state=BOMState.ACTUAL, supplier=supplier
        )

        job.refresh_from_db()
        self.assertEqual(job.actual_cogs, Decimal("4000.00"),
                         "actual_cogs must be updated by signal after TimberEntry save")

    def test_delete_entry_reduces_cogs(self):
        """Deleting a TimberEntry must recalculate COGS downward."""
        from crm.models import ClientProfile
        from core.models import Job
        from production.models import JobCard, TimberEntry, BOMState, TimberSpecies
        from partners.models import SupplierProfile, MaterialType, SupplierLocation

        client, _ = ClientProfile.objects.get_or_create(
            email="cogs_delete@mn.test",
            defaults={"name": "COGS Delete Test", "phone": "+254700000004"}
        )
        job = Job.objects.create(client=client, quoted_price=Decimal("50000"))
        card = JobCard.objects.create(job=job, is_locked=False)
        supplier, _ = SupplierProfile.objects.get_or_create(
            name="Test Supplier Del",
            defaults={"phone": "+254700000005", "material_type": MaterialType.TIMBER,
                      "location": SupplierLocation.GIKOMBA, "current_rate": Decimal("400")}
        )
        entry = TimberEntry.objects.create(
            job_card=card, species=TimberSpecies.MVULE,
            board_feet=Decimal("5"), unit_cost_per_bf=Decimal("450"),
            state=BOMState.ACTUAL, supplier=supplier
        )
        job.refresh_from_db()
        self.assertEqual(job.actual_cogs, Decimal("2250.00"))

        entry.delete()
        job.refresh_from_db()
        self.assertEqual(job.actual_cogs, Decimal("0.00"),
                         "actual_cogs must drop to 0 after the only entry is deleted")
