"""Production views — Job Cards and BOM entry management."""
from django.views.generic import ListView, View, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from core.models import Job, JobStatus
from .models import JobCard, TimberEntry, HardwareEntry, LaborEntry
from .forms import JobCardForm, TimberEntryForm, HardwareEntryForm, LaborEntryForm


def get_or_create_job_card(job):
    card, _ = JobCard.objects.get_or_create(job=job)
    return card


class JobCardListView(LoginRequiredMixin, ListView):
    template_name = "production/jobcard_list.html"
    context_object_name = "job_cards"

    def get_queryset(self):
        return JobCard.objects.select_related("job__client").filter(
            job__status__in=[
                JobStatus.DEPOSIT_PAID, JobStatus.IN_PRODUCTION,
                JobStatus.QUALITY_REVIEW, JobStatus.READY_DELIVERY
            ]
        ).order_by("target_completion")


class JobCardDetailView(LoginRequiredMixin, View):
    template_name = "production/jobcard_detail.html"

    def get(self, request, job_pk):
        job = get_object_or_404(Job, pk=job_pk)
        card = get_or_create_job_card(job)
        ctx = {
            "job": job, "card": card,
            "timber_entries": card.timber_entries.select_related("supplier").order_by("state", "-id"),
            "hardware_entries": card.hardware_entries.select_related("supplier").order_by("state", "-id"),
            "labor_entries": card.labor_entries.select_related("artisan").order_by("state", "-id"),
            "timber_form": TimberEntryForm(),
            "hardware_form": HardwareEntryForm(),
            "labor_form": LaborEntryForm(),
        }
        return render(request, self.template_name, ctx)


class JobCardUnlockView(LoginRequiredMixin, View):
    def post(self, request, job_pk):
        job = get_object_or_404(Job, pk=job_pk)
        card = get_or_create_job_card(job)
        success, reason = card.unlock(request.user)
        if success:
            messages.success(request, reason)
        else:
            messages.error(request, f"Cannot unlock: {reason}")
        return redirect("production:jobcard_detail", job_pk=job.pk)


class JobCardCompleteView(LoginRequiredMixin, View):
    def post(self, request, job_pk):
        job = get_object_or_404(Job, pk=job_pk)
        card = get_or_create_job_card(job)
        card.actual_completion = timezone.now().date()
        card.save()
        job.status = JobStatus.QUALITY_REVIEW
        job.save()
        messages.success(request, f"Job {job.job_id} moved to Quality Review.")
        return redirect("production:jobcard_detail", job_pk=job.pk)


class JobCardPrintView(LoginRequiredMixin, View):
    """Printable Job Card — browser print-to-PDF."""
    template_name = "production/jobcard_print.html"

    def get(self, request, job_pk):
        job = get_object_or_404(Job, pk=job_pk)
        card = get_or_create_job_card(job)
        ctx = {
            "job": job, "card": card,
            "timber_entries": card.timber_entries.filter(state="actual"),
            "hardware_entries": card.hardware_entries.filter(state="actual"),
            "labor_entries": card.labor_entries.filter(state="actual"),
        }
        return render(request, self.template_name, ctx)


class TimberEntryCreateView(LoginRequiredMixin, View):
    def post(self, request, job_pk):
        job = get_object_or_404(Job, pk=job_pk)
        card = get_or_create_job_card(job)
        form = TimberEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.job_card = card
            entry.save()
            messages.success(request, "Timber entry added.")
        else:
            messages.error(request, str(form.errors))
        return redirect("production:jobcard_detail", job_pk=job.pk)


class TimberEntryUpdateView(LoginRequiredMixin, UpdateView):
    model = TimberEntry
    form_class = TimberEntryForm
    template_name = "production/entry_form.html"

    def get_success_url(self):
        return reverse("production:jobcard_detail", kwargs={"job_pk": self.object.job_card.job.pk})


class TimberEntryDeleteView(LoginRequiredMixin, DeleteView):
    model = TimberEntry
    template_name = "production/entry_confirm_delete.html"

    def get_success_url(self):
        return reverse("production:jobcard_detail", kwargs={"job_pk": self.object.job_card.job.pk})


class HardwareEntryCreateView(LoginRequiredMixin, View):
    def post(self, request, job_pk):
        job = get_object_or_404(Job, pk=job_pk)
        card = get_or_create_job_card(job)
        form = HardwareEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.job_card = card
            entry.save()
            messages.success(request, "Hardware entry added.")
        else:
            messages.error(request, str(form.errors))
        return redirect("production:jobcard_detail", job_pk=job.pk)


class HardwareEntryUpdateView(LoginRequiredMixin, UpdateView):
    model = HardwareEntry
    form_class = HardwareEntryForm
    template_name = "production/entry_form.html"

    def get_success_url(self):
        return reverse("production:jobcard_detail", kwargs={"job_pk": self.object.job_card.job.pk})


class HardwareEntryDeleteView(LoginRequiredMixin, DeleteView):
    model = HardwareEntry
    template_name = "production/entry_confirm_delete.html"

    def get_success_url(self):
        return reverse("production:jobcard_detail", kwargs={"job_pk": self.object.job_card.job.pk})


class LaborEntryCreateView(LoginRequiredMixin, View):
    def post(self, request, job_pk):
        job = get_object_or_404(Job, pk=job_pk)
        card = get_or_create_job_card(job)
        form = LaborEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.job_card = card
            entry.save()
            messages.success(request, "Labour entry added.")
        else:
            messages.error(request, str(form.errors))
        return redirect("production:jobcard_detail", job_pk=job.pk)


class LaborEntryUpdateView(LoginRequiredMixin, UpdateView):
    model = LaborEntry
    form_class = LaborEntryForm
    template_name = "production/entry_form.html"

    def get_success_url(self):
        return reverse("production:jobcard_detail", kwargs={"job_pk": self.object.job_card.job.pk})


class LaborEntryDeleteView(LoginRequiredMixin, DeleteView):
    model = LaborEntry
    template_name = "production/entry_confirm_delete.html"

    def get_success_url(self):
        return reverse("production:jobcard_detail", kwargs={"job_pk": self.object.job_card.job.pk})
