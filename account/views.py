from django.shortcuts import render,redirect
from django.views.generic import CreateView, FormView, UpdateView, TemplateView, View, DetailView
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q

from account.models import User, BuyerProfile, SellerProfile
from account.forms import UserForm, LoginForm, BuyerProfileForm, SellerProfileForm, OTPForm, ForgotPasswordForm, ResetPasswordForm, UserUpdateForm
from marketplace.models import Category, Service

# Create your views here.

class BuyerRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_buyer:
            return redirect("access_denied")
        return super().dispatch(request, *args, **kwargs)

class SellerRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_seller:
            return redirect("access_denied")
        return super().dispatch(request, *args, **kwargs)

class LandingPageView(View):
    def get(self,request):
        if request.user.is_authenticated:
            if not request.user.is_buyer and not request.user.is_seller:
                return redirect("role_selection")
            
            mode = request.session.get('user_mode')
            if mode == 'seller' and request.user.is_seller:
                return redirect("seller_dashboard")
            elif mode == 'buyer' and request.user.is_buyer:
                return redirect("buyer_dashboard")
            
            # Default fallback
            if request.user.is_seller:
                request.session['user_mode'] = 'seller'
                return redirect("seller_dashboard")
            return redirect("buyer_dashboard")
        
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
        except User.DoesNotExist:
            return redirect('register')
        if user.otp == otp:
            user.is_verified = True
            user.otp=None
            user.save()
            
            # Ensure profiles exist if flags were already somehow set
            if user.is_buyer:
                BuyerProfile.objects.get_or_create(owner=user)
            if user.is_seller:
                SellerProfile.objects.get_or_create(owner=user)
                
            del self.request.session["verify_user"]
            messages.success(self.request, "Account verified successfully! Please login.")
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
        user = authenticate(self.request, username=username, password=password)
        
        if user:
            if user.is_verified:
                login(self.request, user)
                if not user.is_buyer and not user.is_seller:
                    return redirect("role_selection")
                
                # Set the session mode before any redirect
                if user.is_seller:
                    self.request.session['user_mode'] = 'seller'
                else:
                    self.request.session['user_mode'] = 'buyer'

                # Respect ?next= redirect parameter (for @login_required protected pages)
                next_url = self.request.GET.get('next') or self.request.POST.get('next')
                if next_url:
                    return redirect(next_url)

                # Default dashboard redirect
                if user.is_seller:
                    return redirect("seller_dashboard")
                return redirect("buyer_dashboard")
            else:
                form.add_error(None, "Your account is not verified. Please verify your OTP.")
                return self.form_invalid(form)
        else:
            form.add_error(None, "Invalid username or password.")
            return self.form_invalid(form)

class BuyerDashboardView(LoginRequiredMixin, BuyerRequiredMixin, TemplateView):
    template_name = "buyer/dashboard.html"

    def get_context_data(self, **kwargs):
        from marketplace.models import Order
        from django.core.paginator import Paginator
        context = super().get_context_data(**kwargs)
        
        # Base Queryset
        orders_qs = Order.objects.filter(buyer=self.request.user).order_by("-created_at")
        
        # Search Filtering
        search_query = self.request.GET.get('search', '')
        if search_query:
            orders_qs = orders_qs.filter(
                Q(service__title__icontains=search_query) | 
                Q(service__seller__username__icontains=search_query)
            )
        
        # Pagination
        paginator = Paginator(orders_qs, 10)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context["orders"] = page_obj
        context["search_query"] = search_query
        
        # Recalculate stats based on full queryset (not just page)
        context["active_tasks"] = orders_qs.filter(status__in=["Paid", "In Progress", "Delivered", "Revision Requested"]).count()
        context["completed_tasks"] = orders_qs.filter(status="Completed").count()
        context["cancelled_tasks"] = orders_qs.filter(status="Cancelled").count()
        context["total_spent"] = sum(order.amount for order in orders_qs.exclude(status__in=["Pending", "Cancelled"]))
        return context
    
class SellerDashboardView(LoginRequiredMixin, SellerRequiredMixin, TemplateView):
    template_name = "seller/dashboard.html"

    def get_context_data(self, **kwargs):
        from marketplace.models import Service, Order
        from django.core.paginator import Paginator
        context = super().get_context_data(**kwargs)
        
        context["services"] = Service.objects.filter(seller=self.request.user)
        
        # Base Queryset
        orders_qs = Order.objects.filter(service__seller=self.request.user).order_by("-created_at")
        
        # Search Filtering
        search_query = self.request.GET.get('search', '')
        if search_query:
            orders_qs = orders_qs.filter(
                Q(service__title__icontains=search_query) | 
                Q(buyer__username__icontains=search_query)
            )
            
        # Pagination
        paginator = Paginator(orders_qs, 10)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context["orders"] = page_obj
        context["search_query"] = search_query
        
        # Stats based on full queryset
        context["total_earnings"] = sum(order.amount for order in orders_qs.filter(status="Completed"))
        context["active_tasks"] = orders_qs.filter(status__in=["Paid", "In Progress", "Delivered", "Revision Requested"]).count()
        context["completed_tasks"] = orders_qs.filter(status="Completed").count()
        context["cancelled_tasks"] = orders_qs.filter(status="Cancelled").count()
        return context
    
class BuyerProfileUpdateView(LoginRequiredMixin, BuyerRequiredMixin, UpdateView):
    model = BuyerProfile
    form_class = BuyerProfileForm
    template_name = "buyer/profile_edit.html"
    success_url = reverse_lazy("buyer_dashboard")
    
    def get_object(self):
        return self.request.user.buyer_profile

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "user_form" not in context:
            context["user_form"] = UserUpdateForm(instance=self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        profile_form = self.get_form()
        user_form = UserUpdateForm(request.POST, instance=request.user)

        if profile_form.is_valid() and user_form.is_valid():
            user_form.save()
            return self.form_valid(profile_form)
        else:
            return self.render_to_response(self.get_context_data(form=profile_form, user_form=user_form))
    
class SellerProfileUpdateView(LoginRequiredMixin, SellerRequiredMixin, UpdateView):
    model = SellerProfile
    form_class = SellerProfileForm
    template_name = "seller/profile_edit.html"
    success_url = reverse_lazy("seller_dashboard")
    
    def get_object(self):
        return self.request.user.seller_profile

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "user_form" not in context:
            context["user_form"] = UserUpdateForm(instance=self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        profile_form = self.get_form()
        user_form = UserUpdateForm(request.POST, instance=request.user)

        if profile_form.is_valid() and user_form.is_valid():
            user_form.save()
            return self.form_valid(profile_form)
        else:
            return self.render_to_response(self.get_context_data(form=profile_form, user_form=user_form))
    
class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect("login")

class AboutView(TemplateView):
    template_name = 'account/about.html'

class HowItWorksView(TemplateView):
    template_name = 'account/how_it_works.html'


class RoleSelectionView(LoginRequiredMixin, View):
    def get(self, request):
        if request.user.is_buyer or request.user.is_seller:
            if request.user.is_seller:
                return redirect("seller_dashboard")
            return redirect("buyer_dashboard")
        return render(request, "account/role_selection.html")

    def post(self, request):
        is_client = request.POST.get("is_client") == "on"
        is_freelancer = request.POST.get("is_freelancer") == "on"
        
        if is_client or is_freelancer:
            user = request.user
            user.is_buyer = is_client
            user.is_seller = is_freelancer
            user.is_verified = True
            user.save()
            
            if is_freelancer:
                request.session['user_mode'] = 'seller'
                return redirect("seller_dashboard")
            else:
                request.session['user_mode'] = 'buyer'
                return redirect("buyer_dashboard")
        return redirect("role_selection")

class ToggleModeView(LoginRequiredMixin, View):
    def get(self, request):
        current_mode = request.session.get('user_mode', 'buyer')
        if current_mode == 'seller' and request.user.is_buyer:
            request.session['user_mode'] = 'buyer'
            return redirect('buyer_dashboard')
        elif current_mode == 'buyer' and request.user.is_seller:
            request.session['user_mode'] = 'seller'
            return redirect('seller_dashboard')
        return redirect('landing_page')

class AccessDeniedView(TemplateView):
    template_name = "account/access_denied.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Check the referer or request path to determine which role was required
        if 'seller' in self.request.path or 'service' in self.request.path:
            context['required_role'] = 'Freelancer'
        else:
            context['required_role'] = 'Client'
        return context

class ForgotUsernameView(View):
    def get(self, request):
        from account.forms import ForgotPasswordForm
        form = ForgotPasswordForm()
        return render(request, "account/forgot_username.html", {"form": form})

    def post(self, request):
        from account.forms import ForgotPasswordForm
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            users = User.objects.filter(email=email)
            if users.exists():
                usernames = [u.username for u in users]
                username_list = ", ".join(usernames)
                
                from django.core.mail import send_mail
                from django.conf import settings
                
                subject = "Task Wizards: Your Username Recovery"
                message = f"Hello,\n\nThe username(s) associated with this email address are: {username_list}\n\nYou can login here: {request.build_absolute_uri('/')}"
                
                try:
                    send_mail(
                        subject,
                        message,
                        settings.EMAIL_HOST_USER,
                        [email],
                        fail_silently=False,
                    )
                    messages.success(request, "If an account exists with that email, we've sent the username(s).")
                except Exception as e:
                    messages.error(request, "Failed to send email. Please try again later.")
            else:
                messages.success(request, "If an account exists with that email, we've sent the username(s).")
            return redirect("login")
        return render(request, "account/forgot_username.html", {"form": form})