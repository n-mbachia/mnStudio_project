from django.views.generic import ListView, DetailView, CreateView, UpdateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from .models import SupplierProfile, PurchaseOrder, POStatus, ArtisanProfile
from .forms import SupplierProfileForm, PurchaseOrderForm, POReceiveForm, ArtisanProfileForm


class SupplierListView(LoginRequiredMixin, ListView):
    model = SupplierProfile
    template_name = "partners/supplier_list.html"
    context_object_name = "suppliers"

    def get_queryset(self):
        qs = SupplierProfile.objects.filter(is_active=True)
        mt = self.request.GET.get("type", "")
        if mt:
            qs = qs.filter(material_type=mt)
        return qs


class SupplierDetailView(LoginRequiredMixin, DetailView):
    model = SupplierProfile
    template_name = "partners/supplier_detail.html"
    context_object_name = "supplier"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["pos"] = self.object.purchase_orders.order_by("-raised_at")[:10]
        ctx["rate_history"] = self.object.rate_history.order_by("-created_at")[:5]
        return ctx


class SupplierCreateView(LoginRequiredMixin, CreateView):
    model = SupplierProfile
    form_class = SupplierProfileForm
    template_name = "partners/supplier_form.html"

    def get_success_url(self):
        return reverse_lazy("partners:supplier_detail", kwargs={"pk": self.object.pk})


class SupplierUpdateView(LoginRequiredMixin, UpdateView):
    model = SupplierProfile
    form_class = SupplierProfileForm
    template_name = "partners/supplier_form.html"

    def get_success_url(self):
        return reverse_lazy("partners:supplier_detail", kwargs={"pk": self.object.pk})


class PurchaseOrderListView(LoginRequiredMixin, ListView):
    model = PurchaseOrder
    template_name = "partners/po_list.html"
    context_object_name = "orders"
    paginate_by = 20

    def get_queryset(self):
        qs = PurchaseOrder.objects.select_related("supplier").order_by("-raised_at")
        status = self.request.GET.get("status", "")
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["statuses"] = POStatus.choices
        ctx["current_status"] = self.request.GET.get("status", "")
        return ctx


class PurchaseOrderDetailView(LoginRequiredMixin, DetailView):
    model = PurchaseOrder
    template_name = "partners/po_detail.html"
    context_object_name = "po"


class PurchaseOrderCreateView(LoginRequiredMixin, CreateView):
    model = PurchaseOrder
    form_class = PurchaseOrderForm
    template_name = "partners/po_form.html"
    success_url = reverse_lazy("partners:po_list")


class POConfirmView(LoginRequiredMixin, View):
    def post(self, request, pk):
        po = get_object_or_404(PurchaseOrder, pk=pk)
        from django.utils import timezone
        po.status = POStatus.CONFIRMED
        po.confirmed_at = timezone.now()
        po.save()
        messages.success(request, f"{po.po_number} confirmed.")
        return redirect("partners:po_detail", pk=po.pk)


class POReceiveView(LoginRequiredMixin, View):
    def get(self, request, pk):
        from django.shortcuts import render
        po = get_object_or_404(PurchaseOrder, pk=pk)
        form = POReceiveForm(initial={"unit_cost_at_receipt": po.supplier.current_rate})
        return render(request, "partners/po_receive.html", {"po": po, "form": form})

    def post(self, request, pk):
        po = get_object_or_404(PurchaseOrder, pk=pk)
        form = POReceiveForm(request.POST)
        if form.is_valid():
            unit_cost = form.cleaned_data["unit_cost_at_receipt"]
            po.mark_received(unit_cost=unit_cost, user=request.user)
            # Update supplier current rate
            po.supplier.current_rate = unit_cost
            po.supplier.save()
            messages.success(request, f"{po.po_number} marked received at KES {unit_cost}/unit. BOM entries updated.")
            return redirect("partners:po_detail", pk=po.pk)
        from django.shortcuts import render
        return render(request, "partners/po_receive.html", {"po": po, "form": form})


class ArtisanListView(LoginRequiredMixin, ListView):
    model = ArtisanProfile
    template_name = "partners/artisan_list.html"
    context_object_name = "artisans"

    def get_queryset(self):
        return ArtisanProfile.objects.filter(is_active=True)


class ArtisanDetailView(LoginRequiredMixin, DetailView):
    model = ArtisanProfile
    template_name = "partners/artisan_detail.html"
    context_object_name = "artisan"


class ArtisanCreateView(LoginRequiredMixin, CreateView):
    model = ArtisanProfile
    form_class = ArtisanProfileForm
    template_name = "partners/artisan_form.html"
    success_url = reverse_lazy("partners:artisan_list")
