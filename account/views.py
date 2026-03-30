from django.shortcuts import render,redirect
from django.views.generic import CreateView, FormView, UpdateView, TemplateView, View, DetailView
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages

from account.models import User, BuyerProfile, SellerProfile
from account.forms import UserForm, LoginForm, BuyerProfileForm, SellerProfileForm, OTPForm, ForgotPasswordForm, ResetPasswordForm
from marketplace.models import Category, Service

# Create your views here.

class BuyerRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if request.user.role != "Buyer":
            return redirect("seller_dashboard")
        return super().dispatch(request, *args, **kwargs)

class SellerRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if request.user.role != "Seller":
            return redirect("buyer_dashboard")
        return super().dispatch(request, *args, **kwargs)

class LandingPageView(View):
    def get(self,request):
        if request.user.is_authenticated:
            if request.user.role == "Buyer":
                return redirect("buyer_dashboard")
            if request.user.role == "Seller":
                return redirect("seller_dashboard")
        
        context = {
            "categories": Category.objects.all(),
            "popular_services": Service.objects.all().order_by("-updated_at")[:4] # Placeholder for "popular"
        }
        return render(request, 'account/landingpage.html', context)

class RegisterView(CreateView):
    model = User
    form_class = UserForm
    template_name = "account/register.html"
    success_url = reverse_lazy("verify_otp")

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.object
        user.generate_otp()
        self.request.session["verify_user"] = user.id
        return response

class VerifyOTPView(FormView):
    template_name = "account/verify_otp.html"
    form_class = OTPForm
    success_url = reverse_lazy("login")

    def form_valid(self, form):
        otp = form.cleaned_data["otp"]
        user_id = self.request.session.get("verify_user")
        if not user_id:
            return redirect('register')
        try:
            user = User.objects.get(id=user_id)
        except user.DoesNotExist:
            return redirect('register')
        if user.otp == otp:
            user.is_verified = True
            user.otp=None
            user.save()
            del self.request.session["verify_user"]
            return super().form_valid(form)
        return redirect("verify_otp")
    
class ForgotPasswordView(FormView):
    template_name = "account/forgot_password.html"
    form_class = ForgotPasswordForm
    success_url = reverse_lazy("reset_password")

    def form_valid(self, form):
        email = form.cleaned_data.get("email")
        try:
            user = User.objects.get(email=email)
            user.generate_otp()
            self.request.session["reset_email"] = email
            messages.success(self.request, "OTP sent to your email.")
            return super().form_valid(form)
        except User.DoesNotExist:
            messages.error(self.request, "User with this email does not exist.")
            return self.form_invalid(form)

class ResetPasswordView(FormView):
    template_name = "account/reset_password.html"
    form_class = ResetPasswordForm
    success_url = reverse_lazy("login")

    def form_valid(self, form):
        otp = form.cleaned_data.get("otp")
        new_password = form.cleaned_data.get("new_password")
        email = self.request.session.get("reset_email")

        if not email:
            messages.error(self.request, "Session expired. Please try again.")
            return redirect("forgot_password")

        try:
            user = User.objects.get(email=email)
            if user.otp == otp:
                user.set_password(new_password)
                user.otp = None
                user.save()
                del self.request.session["reset_email"]
                messages.success(self.request, "Password reset successful! Please login.")
                return super().form_valid(form)
            else:
                messages.error(self.request, "Invalid OTP.")
                return self.form_invalid(form)
        except User.DoesNotExist:
            return redirect("forgot_password")

class LoginView(FormView):
    form_class = LoginForm
    template_name = "account/login.html"

    def form_valid(self, form):
        username = form.cleaned_data["username"]
        password = form.cleaned_data["password"]
        user = authenticate(self.request,username=username,password=password)
        if user and user.is_verified:
            login(self.request, user)
            if user.role == "Buyer":
                return redirect("buyer_dashboard")
            elif user.role == "Seller":
                return redirect("seller_dashboard")
        messages.error(self.request,"Invalid credentials or account not verified")
        return redirect("login")

class BuyerDashboardView(LoginRequiredMixin, BuyerRequiredMixin, TemplateView):
    template_name = "buyer/dashboard.html"

    def get_context_data(self, **kwargs):
        from marketplace.models import Order
        context = super().get_context_data(**kwargs)
        context["orders"] = Order.objects.filter(buyer=self.request.user).order_by("-created_at")
        context["active_tasks"] = context["orders"].filter(status__in=["Paid", "In Progress", "Delivered", "Revision Requested"]).count()
        # count for total completed (not in active anymore) is handled in completed_tasks
        context["completed_tasks"] = context["orders"].filter(status="Completed").count()
        context["total_spent"] = sum(order.amount for order in context["orders"].exclude(status="Pending"))
        return context
    
class SellerDashboardView(LoginRequiredMixin, SellerRequiredMixin, TemplateView):
    template_name = "seller/dashboard.html"

    def get_context_data(self, **kwargs):
        from marketplace.models import Service, Order
        context = super().get_context_data(**kwargs)
        context["services"] = Service.objects.filter(seller=self.request.user)
        context["orders"] = Order.objects.filter(service__seller=self.request.user).order_by("-created_at")
        context["total_earnings"] = sum(order.amount for order in context["orders"].filter(status="Completed"))
        context["active_tasks"] = context["orders"].filter(status__in=["Paid", "In Progress", "Delivered", "Revision Requested"]).count()
        context["completed_tasks"] = context["orders"].filter(status="Completed").count()
        return context
    
class BuyerProfileUpdateView(LoginRequiredMixin, BuyerRequiredMixin, UpdateView):
    model = BuyerProfile
    form_class = BuyerProfileForm
    template_name = "buyer/profile_edit.html"
    success_url = reverse_lazy("buyer_dashboard")
    
    def get_object(self):
        return self.request.user.buyer_profile
    
class SellerProfileUpdateView(LoginRequiredMixin, SellerRequiredMixin, UpdateView):
    model = SellerProfile
    form_class = SellerProfileForm
    template_name = "seller/profile_edit.html"
    success_url = reverse_lazy("seller_dashboard")
    
    def get_object(self):
        return self.request.user.seller_profile
    
class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect("login")

class AboutView(TemplateView):
    template_name = 'account/about.html'

class HowItWorksView(TemplateView):
    template_name = 'account/how_it_works.html'