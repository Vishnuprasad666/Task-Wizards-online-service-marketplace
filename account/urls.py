from django.urls import path
from account.views import *

urlpatterns = [
    path("", LandingPageView.as_view(), name="home"),
    path("register/", RegisterView.as_view(), name="register"),
    path("verify-otp/", VerifyOTPView.as_view(), name="verify_otp"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),

    path("buyer/dashboard/", BuyerDashboardView.as_view(), name="buyer_dashboard"),
    path("seller/dashboard/", SellerDashboardView.as_view(), name="seller_dashboard"),

    path("buyer/profile/edit/", BuyerProfileUpdateView.as_view(), name="buyer_profile_edit"),
    path("seller/profile/edit/", SellerProfileUpdateView.as_view(), name="seller_profile_edit"),

    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot_password"),
    path("forgot-username/", ForgotUsernameView.as_view(), name="forgot_username"),
    path("reset-password/", ResetPasswordView.as_view(), name="reset_password"),
    path("about/", AboutView.as_view(), name="about"),
    path("how-it-works/", HowItWorksView.as_view(), name="how_it_works"),
    path("role-selection/", RoleSelectionView.as_view(), name="role_selection"),
    path("toggle-mode/", ToggleModeView.as_view(), name="toggle_mode"),
    path("access-denied/", AccessDeniedView.as_view(), name="access_denied"),
]