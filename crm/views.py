"""CRM views — client management, pipeline, design briefs."""
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from .models import ClientProfile, Lead, LeadStatus, DesignBrief, DesignBriefStatus, Interaction
from .forms import ClientProfileForm, LeadForm, DesignBriefForm, InteractionForm


class ClientListView(LoginRequiredMixin, ListView):
    model = ClientProfile
    template_name = "crm/client_list.html"
    context_object_name = "clients"
    paginate_by = 20

    def get_queryset(self):
        qs = ClientProfile.objects.all()
        q = self.request.GET.get("q", "")
        if q:
            qs = qs.filter(name__icontains=q) | qs.filter(email__icontains=q)
        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["query"] = self.request.GET.get("q", "")
        return ctx


class ClientDetailView(LoginRequiredMixin, DetailView):
    model = ClientProfile
    template_name = "crm/client_detail.html"
    context_object_name = "client"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["jobs"] = self.object.jobs.select_related().order_by("-created_at")
        ctx["interactions"] = self.object.interactions.order_by("-created_at")[:10]
        ctx["interaction_form"] = InteractionForm(initial={"client": self.object})
        return ctx


class ClientCreateView(LoginRequiredMixin, CreateView):
    model = ClientProfile
    form_class = ClientProfileForm
    template_name = "crm/client_form.html"

    def get_success_url(self):
        return reverse_lazy("crm:client_detail", kwargs={"pk": self.object.pk})


class ClientUpdateView(LoginRequiredMixin, UpdateView):
    model = ClientProfile
    form_class = ClientProfileForm
    template_name = "crm/client_form.html"

    def get_success_url(self):
        return reverse_lazy("crm:client_detail", kwargs={"pk": self.object.pk})


class PipelineView(LoginRequiredMixin, TemplateView):
    template_name = "crm/pipeline.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["stages"] = [
            {"key": s.value, "label": s.label, "leads": Lead.objects.filter(status=s).select_related("client")}
            for s in [LeadStatus.INQUIRY, LeadStatus.QUOTED, LeadStatus.NEGOTIATING,
                      LeadStatus.APPROVED, LeadStatus.IN_PRODUCTION, LeadStatus.DELIVERED]
        ]
        return ctx


class LeadCreateView(LoginRequiredMixin, CreateView):
    model = Lead
    form_class = LeadForm
    template_name = "crm/lead_form.html"
    success_url = reverse_lazy("crm:pipeline")


class DesignBriefCreateView(LoginRequiredMixin, CreateView):
    model = DesignBrief
    form_class = DesignBriefForm
    template_name = "crm/brief_form.html"
    success_url = reverse_lazy("crm:pipeline")


class DesignBriefApproveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        brief = get_object_or_404(DesignBrief, pk=pk)
        brief.status = DesignBriefStatus.APPROVED
        brief.approved_at = timezone.now()
        brief.save()
        # Update Job status
        job = brief.job
        from core.models import JobStatus
        if job.status == JobStatus.QUOTE_APPROVED:
            job.status = JobStatus.DEPOSIT_PAID
            job.save()
        messages.success(request, f"Design Brief v{brief.version} approved.")
        return redirect("crm:client_detail", pk=job.client.pk)


class InteractionCreateView(LoginRequiredMixin, CreateView):
    model = Interaction
    form_class = InteractionForm
    template_name = "crm/interaction_form.html"
    success_url = reverse_lazy("crm:client_list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        obj = self.object
        return reverse_lazy("crm:client_detail", kwargs={"pk": obj.client.pk})
