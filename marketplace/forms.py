from django import forms
from marketplace.models import Service

class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ["category", "title", "description", "price", "delivery_time", "image"]
        widgets = {
            "category": forms.Select(attrs={"class": "form-control"}),
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter service title"}),
            "description": forms.Textarea(attrs={"class": "form-control", "placeholder": "Describe your service", "rows": 4}),
            "price": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Price in INR"}),
            "delivery_time": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Expected delivery (Days)"}),
            "image": forms.FileInput(attrs={"class": "form-control"}),
        }
