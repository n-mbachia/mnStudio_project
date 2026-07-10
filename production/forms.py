from django import forms
from .models import JobCard, TimberEntry, HardwareEntry, LaborEntry


class JobCardForm(forms.ModelForm):
    class Meta:
        model = JobCard
        fields = ["workshop_notes", "start_date", "target_completion"]
        widgets = {"workshop_notes": forms.Textarea(attrs={"rows": 3})}


class TimberEntryForm(forms.ModelForm):
    class Meta:
        model = TimberEntry
        fields = ["species", "board_feet", "unit_cost_per_bf", "supplier",
                  "purchase_order", "state", "date_purchased", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 2})}


class HardwareEntryForm(forms.ModelForm):
    class Meta:
        model = HardwareEntry
        fields = ["item_name", "quantity", "unit_cost", "supplier",
                  "purchase_order", "state", "date_purchased", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 2})}


class LaborEntryForm(forms.ModelForm):
    class Meta:
        model = LaborEntry
        fields = ["artisan", "task_description", "piece_rate", "hours",
                  "state", "work_date", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 2})}
