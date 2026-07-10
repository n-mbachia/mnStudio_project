from django import forms
from django.forms import inlineformset_factory
from .models import Quote, QuoteLineItem, Invoice, InvoiceLineItem, Payment


class QuoteForm(forms.ModelForm):
    class Meta:
        model = Quote
        fields = ["client", "discount", "deposit_amount", "valid_until", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 2})}


QuoteLineItemFormSet = inlineformset_factory(
    Quote, QuoteLineItem,
    fields=["description", "quantity", "unit_price"],
    extra=3, can_delete=True
)


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ["notes", "due_at"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 2})}


InvoiceLineItemFormSet = inlineformset_factory(
    Invoice, InvoiceLineItem,
    fields=["description", "quantity", "unit_price"],
    extra=2, can_delete=True
)


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["amount", "method", "mpesa_ref", "paid_at"]
        widgets = {"paid_at": forms.DateTimeInput(attrs={"type": "datetime-local"})}
