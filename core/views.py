"""Core views — dashboard and home."""
from decimal import Decimal
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from .models import Job, JobStatus


class HomeView(TemplateView):
    template_name = "storefront/home.html"


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        now = timezone.now()
        # Job pipeline stats
        jobs = Job.objects.all()
        ctx["total_jobs"]       = jobs.count()
        ctx["active_jobs"]      = jobs.filter(status__in=[
            JobStatus.DEPOSIT_PAID, JobStatus.IN_PRODUCTION,
            JobStatus.QUALITY_REVIEW, JobStatus.READY_DELIVERY
        ]).count()
        ctx["completed_jobs"]   = jobs.filter(status=JobStatus.COMPLETED).count()
        ctx["pipeline_jobs"]    = jobs.exclude(status__in=[
            JobStatus.COMPLETED, JobStatus.CANCELLED
        ]).select_related("client").order_by("status")[:10]

        # Financial summary — current month
        from ledger.models import Payment, PaymentStatus
        from django.db.models import Sum
        month_payments = Payment.objects.filter(
            paid_at__year=now.year, paid_at__month=now.month,
            status=PaymentStatus.CONFIRMED
        )
        ctx["month_revenue"] = month_payments.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")

        # Compliance preview
        from ledger.compliance import compute_period_obligations
        ctx["compliance"] = compute_period_obligations(now.year, now.month)
        ctx["current_month"] = now.strftime("%B %Y")
        return ctx
