from django import forms
from .models import SupplierProfile, PurchaseOrder, ArtisanProfile


class SupplierProfileForm(forms.ModelForm):
    class Meta:
        model = SupplierProfile
        fields = ["name", "contact_name", "phone", "email", "material_type",
                  "location", "current_rate", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ["supplier", "description", "estimated_amount", "notes"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }


class POReceiveForm(forms.Form):
    unit_cost_at_receipt = forms.DecimalField(
        max_digits=10, decimal_places=2,
        label="Actual unit cost at receipt (KES/BF or KES/unit)",
        help_text="This price will be locked and propagated to all linked BOM entries."
    )


class ArtisanProfileForm(forms.ModelForm):
    class Meta:
        model = ArtisanProfile
        fields = ["name", "phone", "specialty", "base_piece_rate", "nssf_number", "joined_at", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}
