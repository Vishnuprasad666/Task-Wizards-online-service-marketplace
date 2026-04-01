from django import forms
from django.contrib.auth.forms import UserCreationForm
from account.models import User, BuyerProfile, SellerProfile


# -------------------------
# USER REGISTRATION FORM
# -------------------------

class UserForm(UserCreationForm):
    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "phone",
            "username",
            "role",
        ]
        
        widgets = {

            "first_name": forms.TextInput(attrs={"placeholder": "Enter First Name","class": "form-control"}),
            "last_name": forms.TextInput(attrs={"placeholder": "Enter Last Name","class": "form-control"}),
            "email": forms.EmailInput(attrs={"placeholder": "Enter Email","class": "form-control"}),
            "phone": forms.TextInput(attrs={"placeholder": "Enter Phone Number","class": "form-control"}),
            "username": forms.TextInput(attrs={"placeholder": "Enter Username","class": "form-control"}),
            "role": forms.Select(attrs={"class": "form-control"}),
            
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs.update({"class": "form-control","placeholder": "Enter Password"})
        self.fields["password2"].widget.attrs.update({"class": "form-control","placeholder": "Confirm Password"})
        
    def clean_phone(self):
        phone = self.cleaned_data.get("phone")
        if not phone.isdigit():
            raise forms.ValidationError("Phone number must contain only digits")
        if len(phone) != 10:
            raise forms.ValidationError("Phone number must be exactly 10 digits")
        if phone[0] not in "6789":
            raise forms.ValidationError("Phone number must start with 6, 7, 8, or 9")
        return phone

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Email already exists")
        return email

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone", "location", "linkedin_profile", "twitter_profile"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "First Name"}),
            "last_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Last Name"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email"}),
            "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "Phone"}),
            "location": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. New York, USA"}),
            "linkedin_profile": forms.URLInput(attrs={"class": "form-control", "placeholder": "LinkedIn Profile URL"}),
            "twitter_profile": forms.URLInput(attrs={"class": "form-control", "placeholder": "Twitter Profile URL"}),
        }
    
class OTPForm(forms.Form):

    otp = forms.CharField(
        max_length=10,
        widget=forms.TextInput(attrs={"class": "form-control","placeholder": "Enter OTP"}))

# -------------------------
# LOGIN FORM
# -------------------------

class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter Username or Email"})
    )
    password = forms.CharField(
        max_length=100,
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Enter Password"})
    )


# -------------------------
# BUYER PROFILE FORM
# -------------------------

class BuyerProfileForm(forms.ModelForm):
    photo = forms.ImageField(widget=forms.FileInput(attrs={"class": "form-control"}), required=False)
    class Meta:
        model = BuyerProfile
        exclude = ["owner"]
        widgets = {
            "bio": forms.TextInput(attrs={"class": "form-control","placeholder": "Write something about yourself"}),
            "company_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Company Name"}),
            "interests": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Design, Marketing, Development"}),
            "website": forms.URLInput(attrs={"class": "form-control", "placeholder": "Website URL"}),
            "address": forms.Textarea(attrs={"class": "form-control", "placeholder": "Enter your address", "rows": 3}),
        }


# -------------------------
# SELLER PROFILE FORM
# -------------------------

class SellerProfileForm(forms.ModelForm):
    photo = forms.ImageField(widget=forms.FileInput(attrs={"class": "form-control"}), required=False)
    class Meta:
        model = SellerProfile
        exclude = ["owner", "rating", "orders_completed"]

        widgets = {
            "bio": forms.TextInput(attrs={"class": "form-control","placeholder": "Write about yourself"}),
            "expertise": forms.TextInput(attrs={"class": "form-control","placeholder": "Main expertise"}),
            "skills": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Logo Design, Python, SEO"}),
            "education": forms.TextInput(attrs={"class": "form-control", "placeholder": "Degree / Institution"}),
            "portfolio_link": forms.URLInput(attrs={"class": "form-control","placeholder": "Portfolio / Website link"}),
            "hourly_rate": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Hourly Rate (in ₹)"}),
            "is_available": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

# -------------------------
# PASSWORD RESET FORMS
# -------------------------

class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Enter your email"}))

class ResetPasswordForm(forms.Form):
    otp = forms.CharField(max_length=10, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter OTP"}))
    new_password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Enter new password"}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirm new password"}))

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")
        if new_password != confirm_password:
            raise forms.ValidationError("Passwords do not match")
        return cleaned_data