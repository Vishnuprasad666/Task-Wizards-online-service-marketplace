from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, BuyerProfile, SellerProfile

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "is_buyer", "is_seller", "is_verified", "is_staff")
    list_filter = ("is_buyer", "is_seller", "is_verified", "is_staff", "is_superuser")
    fieldsets = UserAdmin.fieldsets + (
        ("Custom Fields", {"fields": ("is_buyer", "is_seller", "phone", "is_verified", "otp", "role")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Custom Fields", {"fields": ("is_buyer", "is_seller", "phone", "is_verified")}),
    )

@admin.register(BuyerProfile)
class BuyerProfileAdmin(admin.ModelAdmin):
    list_display = ("owner", "bio")
    search_fields = ("owner__username", "bio")

@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    list_display = ("owner", "expertise", "portfolio_link")
    search_fields = ("owner__username", "expertise", "bio")
