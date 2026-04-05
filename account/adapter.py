from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.shortcuts import resolve_url
from django.urls import reverse

class RoleSelectionAdapter(DefaultSocialAccountAdapter):
    def get_login_redirect_url(self, request):
        path = super().get_login_redirect_url(request)
        user = request.user
        if user.is_authenticated and not user.is_buyer and not user.is_seller:
            return reverse("role_selection")
        return path
