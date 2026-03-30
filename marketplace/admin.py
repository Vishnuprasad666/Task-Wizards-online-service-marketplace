from django.contrib import admin
from .models import Category, Service, Order

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("title", "seller", "category", "price", "created_at")
    list_filter = ("category", "created_at")
    search_fields = ("title", "description", "seller__username")

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "buyer", "service", "amount", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("razorpay_order_id", "buyer__username")
