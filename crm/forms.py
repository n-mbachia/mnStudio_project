from django import forms
from .models import ClientProfile, Lead, DesignBrief, Interaction


class ClientProfileForm(forms.ModelForm):
    class Meta:
        model = ClientProfile
        fields = ["name", "email", "phone", "secondary_phone", "address",
                  "county", "acquisition_source", "preference_notes", "is_vip"]
        widgets = {
            "preference_notes": forms.Textarea(attrs={"rows": 3}),
            "address": forms.Textarea(attrs={"rows": 2}),
        }


class LeadForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = ["client", "piece_type", "status", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}


class DesignBriefForm(forms.ModelForm):
    class Meta:
        model = DesignBrief
        fields = ["job", "title", "description", "dimensions",
                  "primary_species", "finish", "attachments_url", "status"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
        }


class InteractionForm(forms.ModelForm):
    class Meta:
        model = Interaction
        fields = ["client", "job", "channel", "note"]
        widgets = {"note": forms.Textarea(attrs={"rows": 3})}
