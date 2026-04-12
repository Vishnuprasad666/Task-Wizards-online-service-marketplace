import os
from django import forms
from django.db.models import Sum
from marketplace.models import Order, Service, WithdrawalRequest


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
            ext = os.path.splitext(image.name)[1].lower()
            if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
                raise forms.ValidationError("Unsupported image format. Please use JPG, PNG, or WEBP.")
        return image

class WithdrawalRequestForm(forms.ModelForm):
    class Meta:
        model = WithdrawalRequest
        fields = ['amount']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Amount to withdraw (₹)'})
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if self.user:
            # Calculate total earnings from completed orders
            total_earned = Order.objects.filter(
                service__seller=self.user, 
                status="Completed"
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Calculate already withdrawn or pending amounts
            total_withdrawn = WithdrawalRequest.objects.filter(
                user=self.user
            ).exclude(status="Rejected").aggregate(total=Sum('amount'))['total'] or 0
            
            available_balance = float(total_earned) - float(total_withdrawn)
            
            if float(amount) > available_balance:
                raise forms.ValidationError(f"Insufficient balance. Your available balance is ₹{available_balance:.2f}")
            if float(amount) <= 0:
                raise forms.ValidationError("Withdrawal amount must be greater than zero.")
        return amount
