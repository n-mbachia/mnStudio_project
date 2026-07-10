"""Ledger views — Quotes, Invoices, Payments, Compliance Dashboard."""
import json
from decimal import Decimal
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from .models import Quote, QuoteStatus, Invoice, InvoiceStatus, Payment, PaymentStatus, CompliancePeriod
from .forms import QuoteForm, QuoteLineItemFormSet, InvoiceForm, InvoiceLineItemFormSet, PaymentForm
from .compliance import compute_period_obligations, save_period_to_db


class QuoteListView(LoginRequiredMixin, ListView):
    model = Quote
    template_name = "ledger/quote_list.html"
    context_object_name = "quotes"
    paginate_by = 20

    def get_queryset(self):
        return Quote.objects.select_related("client").order_by("-created_at")


class QuoteDetailView(LoginRequiredMixin, DetailView):
    model = Quote
    template_name = "ledger/quote_detail.html"
    context_object_name = "quote"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["line_items"] = self.object.line_items.all()
        return ctx


class QuoteCreateView(LoginRequiredMixin, View):
    template_name = "ledger/quote_form.html"

    def get(self, request):
        form = QuoteForm()
        formset = QuoteLineItemFormSet()
        return render(request, self.template_name, {"form": form, "formset": formset})

    def post(self, request):
        form = QuoteForm(request.POST)
        formset = QuoteLineItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            quote = form.save()
            formset.instance = quote
            formset.save()
            quote.recalculate()
            messages.success(request, f"Quote {quote.quote_id} created.")
            return redirect("ledger:quote_detail", pk=quote.pk)
        return render(request, self.template_name, {"form": form, "formset": formset})


class QuoteSendView(LoginRequiredMixin, View):
    def post(self, request, pk):
        quote = get_object_or_404(Quote, pk=pk)
        quote.status = QuoteStatus.SENT
        quote.sent_at = timezone.now()
        quote.save()
        messages.success(request, f"Quote {quote.quote_id} marked as sent.")
        return redirect("ledger:quote_detail", pk=quote.pk)


class QuoteApproveView(LoginRequiredMixin, View):
    """Approve a Quote and create a Job if one doesn't exist."""
    def post(self, request, pk):
        quote = get_object_or_404(Quote, pk=pk)
        quote.status = QuoteStatus.APPROVED
        quote.approved_at = timezone.now()
        quote.save()

        if not quote.job:
            from core.models import Job, JobStatus
            job = Job.objects.create(
                client=quote.client,
                status=JobStatus.QUOTE_APPROVED,
                quoted_price=quote.total,
                description=f"Commission from Quote {quote.quote_id}",
            )
            quote.job = job
            quote.save()
            # Create invoice from quote
            invoice = Invoice.objects.create(
                job=job, client=quote.client, status=InvoiceStatus.DRAFT
            )
            for li in quote.line_items.all():
                from .models import InvoiceLineItem
                InvoiceLineItem.objects.create(
                    invoice=invoice,
                    description=li.description,
                    quantity=li.quantity,
                    unit_price=li.unit_price,
                )
            invoice.recalculate()
            messages.success(request, f"Quote approved. Job {job.job_id} and Invoice {invoice.invoice_id} created.")
        else:
            messages.success(request, f"Quote {quote.quote_id} approved.")

        return redirect("ledger:quote_detail", pk=quote.pk)


class InvoiceListView(LoginRequiredMixin, ListView):
    model = Invoice
    template_name = "ledger/invoice_list.html"
    context_object_name = "invoices"
    paginate_by = 20

    def get_queryset(self):
        return Invoice.objects.select_related("client", "job").order_by("-created_at")


class InvoiceDetailView(LoginRequiredMixin, DetailView):
    model = Invoice
    template_name = "ledger/invoice_detail.html"
    context_object_name = "invoice"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["line_items"] = self.object.line_items.all()
        ctx["payments"] = self.object.payments.order_by("-paid_at")
        ctx["payment_form"] = PaymentForm()
        ctx["balance_due"] = self.object.balance_due
        return ctx


class InvoicePrintView(LoginRequiredMixin, View):
    """Printable invoice — browser print-to-PDF."""
    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        return render(request, "ledger/invoice_print.html", {
            "invoice": invoice,
            "line_items": invoice.line_items.all(),
            "payments": invoice.payments.filter(status=PaymentStatus.CONFIRMED),
        })


class InvoiceCreateView(LoginRequiredMixin, View):
    template_name = "ledger/invoice_form.html"

    def get(self, request, job_pk):
        from core.models import Job
        job = get_object_or_404(Job, pk=job_pk)
        form = InvoiceForm()
        formset = InvoiceLineItemFormSet()
        return render(request, self.template_name, {"form": form, "formset": formset, "job": job})

    def post(self, request, job_pk):
        from core.models import Job
        job = get_object_or_404(Job, pk=job_pk)
        form = InvoiceForm(request.POST)
        formset = InvoiceLineItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            invoice = form.save(commit=False)
            invoice.job = job
            invoice.client = job.client
            invoice.save()
            formset.instance = invoice
            formset.save()
            invoice.recalculate()
            messages.success(request, f"Invoice {invoice.invoice_id} created.")
            return redirect("ledger:invoice_detail", pk=invoice.pk)
        return render(request, self.template_name, {"form": form, "formset": formset, "job": job})


class PaymentCreateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.invoice = invoice
            payment.status = PaymentStatus.CONFIRMED
            payment.recorded_by = request.user
            payment.save()
            messages.success(request, f"Payment of KES {payment.amount} recorded.")
        else:
            messages.error(request, str(form.errors))
        return redirect("ledger:invoice_detail", pk=invoice.pk)


class ComplianceDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "ledger/compliance_dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        now = timezone.now()
        # Current month live computation
        ctx["current"] = compute_period_obligations(now.year, now.month)
        # Last 6 months history
        periods = []
        for i in range(1, 7):
            month = now.month - i
            year  = now.year
            while month < 1:
                month += 12
                year  -= 1
            periods.append(compute_period_obligations(year, month))
        ctx["history"] = periods
        ctx["saved_periods"] = CompliancePeriod.objects.order_by("-year", "-month")[:6]
        return ctx


class ComplianceMonthView(LoginRequiredMixin, TemplateView):
    template_name = "ledger/compliance_month.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["data"] = compute_period_obligations(self.kwargs["year"], self.kwargs["month"])
        return ctx


class ComplianceSaveView(LoginRequiredMixin, View):
    def post(self, request, year, month):
        period = save_period_to_db(year, month)
        messages.success(request, f"Compliance period {period} saved.")
        return redirect("ledger:compliance_dashboard")


@method_decorator(csrf_exempt, name="dispatch")
class MpesaCallbackView(View):
    """M-Pesa Daraja STK Push callback handler."""
    def post(self, request):
        try:
            data = json.loads(request.body)
            result = data.get("Body", {}).get("stkCallback", {})
            result_code = result.get("ResultCode")
            ref = result.get("CheckoutRequestID", "")
            amount_items = result.get("CallbackMetadata", {}).get("Item", [])
            amount = next((i["Value"] for i in amount_items if i["Name"] == "Amount"), None)
            mpesa_ref = next((i["Value"] for i in amount_items if i["Name"] == "MpesaReceiptNumber"), "")

            if result_code == 0 and mpesa_ref:
                # Update pending payment by matching mpesa_ref or amount
                Payment.objects.filter(
                    mpesa_ref=mpesa_ref, status=PaymentStatus.PENDING
                ).update(status=PaymentStatus.CONFIRMED)
        except Exception as e:
            pass
        return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})
