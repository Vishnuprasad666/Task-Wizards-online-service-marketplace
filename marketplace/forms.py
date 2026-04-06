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
    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image:
            # Check file size (e.g., 2MB)
            if image.size > 2 * 1024 * 1024:
                raise forms.ValidationError("Image file size should not exceed 2MB.")
            
            # Check file extension
            import os
            ext = os.path.splitext(image.name)[1].lower()
            if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
                raise forms.ValidationError("Unsupported image format. Please use JPG, PNG, or WEBP.")
        return image
