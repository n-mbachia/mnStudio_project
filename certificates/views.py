from django.views.generic import DetailView, View, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django import forms
from .models import Certificate, CareSchedule
from core.models import Job


class CertificateForm(forms.ModelForm):
    class Meta:
        model = Certificate
        fields = ["piece_name", "client_name_display", "species_used", "total_board_feet",
                  "primary_artisan", "completion_date", "care_instructions"]
        widgets = {
            "care_instructions": forms.Textarea(attrs={"rows": 3}),
            "completion_date": forms.DateInput(attrs={"type": "date"}),
        }


class CertificatePublicView(DetailView):
    """Public provenance page — accessible via QR code scan, no auth required."""
    model = Certificate
    template_name = "certificates/certificate_public.html"
    context_object_name = "cert"
    slug_field = "certificate_id"
    slug_url_kwarg = "uuid"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["care_schedules"] = self.object.care_schedules.all()
        return ctx


class CertificateCreateView(LoginRequiredMixin, View):
    template_name = "certificates/certificate_form.html"

    def get(self, request, job_pk):
        job = get_object_or_404(Job, pk=job_pk)
        form = CertificateForm()
        return render(request, self.template_name, {"form": form, "job": job})

    def post(self, request, job_pk):
        job = get_object_or_404(Job, pk=job_pk)
        form = CertificateForm(request.POST)
        if form.is_valid():
            cert = form.save(commit=False)
            cert.job = job
            cert.save()
            # Auto-create care schedule (12-month interval)
            import datetime
            today = datetime.date.today()
            for months, care_type in [
                (6,  CareSchedule.CareType.BOARD_BUTTER),
                (12, CareSchedule.CareType.POLISH),
                (24, CareSchedule.CareType.STRUCTURAL_CHECK),
            ]:
                CareSchedule.objects.create(
                    certificate=cert,
                    care_type=care_type,
                    due_date=today + datetime.timedelta(days=months * 30),
                )
            # Update job status
            from core.models import JobStatus
            job.status = JobStatus.COMPLETED
            job.save()
            messages.success(request, f"Certificate {cert.certificate_id} created. Job marked completed.")
            return redirect("certificates:detail", uuid=str(cert.certificate_id))
        return render(request, self.template_name, {"form": form, "job": job})


class CertificatePrintView(LoginRequiredMixin, View):
    def get(self, request, pk):
        cert = get_object_or_404(Certificate, pk=pk)
        base_url = request.build_absolute_uri("/")
        qr_data = cert.generate_qr(base_url)
        return render(request, "certificates/certificate_print.html", {
            "cert": cert, "qr_data": qr_data,
        })
