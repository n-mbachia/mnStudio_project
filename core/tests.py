"""
Core model tests — Job ID generation and state transitions.
"""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User


class JobIDGenerationTest(TestCase):
    def test_job_id_auto_assigned_on_create(self):
        from crm.models import ClientProfile
        from core.models import Job
        client, _ = ClientProfile.objects.get_or_create(
            email="jobid@mn.test",
            defaults={"name": "ID Test", "phone": "+254700000010"}
        )
        job = Job.objects.create(client=client, quoted_price=Decimal("10000"))
        self.assertTrue(job.job_id.startswith("JC-"))
        self.assertEqual(len(job.job_id.split("-")), 5)

    def test_gross_profit_property(self):
        from crm.models import ClientProfile
        from core.models import Job
        client, _ = ClientProfile.objects.get_or_create(
            email="margin@mn.test",
            defaults={"name": "Margin Test", "phone": "+254700000011"}
        )
        job = Job.objects.create(
            client=client, quoted_price=Decimal("100000"),
            actual_cogs=Decimal("55000"), gross_profit=Decimal("45000")
        )
        self.assertEqual(job.actual_margin_pct, Decimal("45.00"))
        self.assertTrue(job.is_profitable)

    def test_cogs_variance(self):
        from crm.models import ClientProfile
        from core.models import Job
        client, _ = ClientProfile.objects.get_or_create(
            email="variance@mn.test",
            defaults={"name": "Variance Test", "phone": "+254700000012"}
        )
        job = Job.objects.create(
            client=client, quoted_price=Decimal("80000"),
            estimated_cogs=Decimal("40000"), actual_cogs=Decimal("43000"),
        )
        # Negative variance = cost overrun
        self.assertEqual(job.cogs_variance, Decimal("-3000"))
