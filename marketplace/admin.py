from django.contrib import admin
from .models import Category, Service, Order, Review, Message, Favourite, Notification, WithdrawalRequest

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("title", "seller", "category", "price", "created_at")
    list_filter = ("category", "created_at", "seller")
    search_fields = ("title", "description", "seller__username")

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "buyer", "service", "amount", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("razorpay_order_id", "buyer__username", "id")
    readonly_fields = ("razorpay_order_id", "razorpay_payment_id", "razorpay_signature")

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("order", "rating", "created_at")
    list_filter = ("rating", "created_at")

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("sender", "receiver", "timestamp", "is_read")
    list_filter = ("is_read", "timestamp")
    search_fields = ("content", "sender__username", "receiver__username")

@admin.register(Favourite)
class FavouriteAdmin(admin.ModelAdmin):
    list_display = ("user", "service", "created_at")

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "message", "is_read", "created_at")
    list_filter = ("is_read", "created_at")

@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__username", "amount")
    list_editable = ("status",) # Allows quick processing from list view
