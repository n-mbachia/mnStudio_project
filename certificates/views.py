from django.views.generic import DetailView, View, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django import forms
from django.utils.html import format_html
from .models import Certificate, CareSchedule
from core.models import Job
import json


class CertificateForm(forms.ModelForm):
    class Meta:
        model = Certificate
        fields = ["piece_name", "client_name_display", "species_used", "total_board_feet",
                  "primary_artisan", "completion_date", "care_instructions"]
        widgets = {
            "piece_name": forms.TextInput(attrs={
                "class": "w-full px-3 py-2 border border-stone-300 rounded-lg focus:ring-2 focus:ring-mahogany-500 focus:border-transparent",
                "placeholder": "Name of the piece"
            }),
            "client_name_display": forms.TextInput(attrs={
                "class": "w-full px-3 py-2 border border-stone-300 rounded-lg focus:ring-2 focus:ring-mahogany-500 focus:border-transparent",
                "placeholder": "Client name or 'Private Collection'"
            }),
            "species_used": forms.Textarea(attrs={
                "class": "w-full px-3 py-2 border border-stone-300 rounded-lg focus:ring-2 focus:ring-mahogany-500 focus:border-transparent font-mono text-sm",
                "rows": 3,
                "placeholder": "[\"Mvule\", \"Mahogany\", \"Cedar\"]"
            }),
            "total_board_feet": forms.NumberInput(attrs={
                "class": "w-full px-3 py-2 border border-stone-300 rounded-lg focus:ring-2 focus:ring-mahogany-500 focus:border-transparent",
                "step": "0.01",
                "placeholder": "0.00"
            }),
            "primary_artisan": forms.Select(attrs={
                "class": "w-full px-3 py-2 border border-stone-300 rounded-lg focus:ring-2 focus:ring-mahogany-500 focus:border-transparent"
            }),
            "completion_date": forms.DateInput(attrs={
                "class": "w-full px-3 py-2 border border-stone-300 rounded-lg focus:ring-2 focus:ring-mahogany-500 focus:border-transparent",
                "type": "date"
            }),
            "care_instructions": forms.Textarea(attrs={
                "class": "w-full px-3 py-2 border border-stone-300 rounded-lg focus:ring-2 focus:ring-mahogany-500 focus:border-transparent",
                "rows": 4,
                "placeholder": "Enter care and maintenance guidelines..."
            }),
        }

    def clean_species_used(self):
        """Validate and parse JSON species list."""
        species = self.cleaned_data.get("species_used")
        if isinstance(species, str):
            try:
                species = json.loads(species)
                if not isinstance(species, list):
                    raise ValueError("Must be a list")
            except (json.JSONDecodeError, ValueError):
                raise forms.ValidationError(
                    "Species must be a valid JSON list, e.g. [\"Mvule\", \"Mahogany\"]"
                )
        return species


class CertificatePublicView(DetailView):
    """Public provenance page — accessible via QR code scan, no auth required."""
    model = Certificate
    template_name = "certificates/certificate_public.html"
    context_object_name = "cert"
    slug_field = "certificate_id"
    slug_url_kwarg = "uuid"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["care_schedules"] = self.object.care_schedules.all().order_by("due_date")
        return ctx


class CertificateCreateView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Create a certificate for a completed job."""
    template_name = "certificates/certificate_form.html"

    def test_func(self):
        """Check if user is staff or has permission."""
        return self.request.user.is_staff or self.request.user.has_perm("certificates.add_certificate")

    def get(self, request, job_pk):
        job = get_object_or_404(Job, pk=job_pk)
        form = CertificateForm()
        return render(request, self.template_name, {
            "form": form,
            "job": job,
            "page_title": f"Create Certificate — {job.job_id}"
        })

    def post(self, request, job_pk):
        job = get_object_or_404(Job, pk=job_pk)
        form = CertificateForm(request.POST)

        if form.is_valid():
            cert = form.save(commit=False)
            cert.job = job
            cert.save()

            # Auto-create care schedule
            import datetime
            today = datetime.date.today()
            care_items = [
                (6, CareSchedule.CareType.BOARD_BUTTER),
                (12, CareSchedule.CareType.POLISH),
                (24, CareSchedule.CareType.STRUCTURAL_CHECK),
            ]

            for months, care_type in care_items:
                CareSchedule.objects.create(
                    certificate=cert,
                    care_type=care_type,
                    due_date=today + datetime.timedelta(days=months * 30),
                )

            # Update job status
            from core.models import JobStatus
            job.status = JobStatus.COMPLETED
            job.save()

            messages.success(
                request,
                format_html(
                    'Certificate <code>{}</code> created successfully. Job marked as completed.',
                    cert.certificate_id_short
                )
            )
            return redirect("certificates:detail", uuid=str(cert.certificate_id))

        return render(request, self.template_name, {
            "form": form,
            "job": job,
            "page_title": f"Create Certificate — {job.job_id}"
        })


class CertificatePrintView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Print/PDF view for certificate with QR code."""

    def test_func(self):
        """Check if user is staff."""
        return self.request.user.is_staff

    def get(self, request, pk):
        cert = get_object_or_404(Certificate, pk=pk)
        base_url = request.build_absolute_uri("/")
        qr_data = cert.generate_qr(base_url)

        return render(request, "certificates/certificate_print.html", {
            "cert": cert,
            "qr_data": qr_data,
            "page_title": f"Print Certificate — {cert.piece_name}"
        })
