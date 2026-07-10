from django import forms
# Updated import from ProductImage to ProductMedia
from .models import Product, ProductMedia, AuctionLot, Waitlist, BudgetRange


class ProductForm(forms.ModelForm):
    class Meta:
        model  = Product
        fields = ["name", "slug", "description", "category", "primary_species",
                  "starting_price", "lead_time_days", "whatsapp_cta", "is_featured", "is_active"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}


# Renamed and updated to handle robust media
class ProductMediaForm(forms.ModelForm):
    class Meta:
        model  = ProductMedia
        fields = ["media_type", "media_url", "thumbnail_url", "caption", "is_primary", "order"]


class AuctionLotForm(forms.ModelForm):
    class Meta:
        model  = AuctionLot
        # Note: If your AuctionLot relies on the Product's media, you could consider 
        # dropping the standalone image_url field here in the future.
        fields = ["title", "description", "product", "image_url", "starting_bid",
                  "reserve_price", "start_time", "end_time", "anti_snipe_minutes"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "start_time": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "end_time":   forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


class WaitlistForm(forms.ModelForm):
    class Meta:
        model  = Waitlist
        fields = ["name", "email", "phone", "piece_of_interest", "budget_range", "timeline_months"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "input"})


class BidForm(forms.Form):
    name   = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": "input"}))
    email  = forms.EmailField(widget=forms.EmailInput(attrs={"class": "input"}))
    phone  = forms.CharField(max_length=20, required=False,
                              widget=forms.TextInput(attrs={"class": "input", "placeholder": "+254…"}))
    amount = forms.DecimalField(max_digits=12, decimal_places=2,
                                widget=forms.NumberInput(attrs={"class": "input", "step": "500"}))
