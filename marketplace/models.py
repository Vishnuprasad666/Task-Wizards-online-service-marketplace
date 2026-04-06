from django.db import models
from django.conf import settings

class Category(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

class Service(models.Model):
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="services")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name="category_services")
    title = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_time = models.PositiveIntegerField(help_text="Delivery time in days", default=3)
    image = models.ImageField(upload_to="services/")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Service"
        verbose_name_plural = "Services"

    def __str__(self):
        return self.title

    @property
    def get_average_rating(self):
        from .models import Review
        reviews = Review.objects.filter(order__service=self)
        if not reviews.exists():
            return 0
        return sum(r.rating for r in reviews) / reviews.count()

    @property
    def get_review_count(self):
        from .models import Review
        return Review.objects.filter(order__service=self).count()

class Order(models.Model):
    STATUS_CHOICES = (
        ("Pending", "Pending"),
        ("Paid", "Paid"),
        ("In Progress", "In Progress"),
        ("Delivered", "Delivered"),
        ("Revision Requested", "Revision Requested"),
        ("Completed", "Completed"),
        ("Cancelled", "Cancelled"),
        ("Refunded", "Refunded"),
        ("Failed", "Failed"),
    )

    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="orders")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    
    buyer_note = models.TextField(blank=True, null=True)
    
    # Delivery fields
    delivery_file = models.FileField(upload_to="deliveries/", blank=True, null=True)
    delivery_message = models.TextField(blank=True, null=True)
    
    # Revision fields
    revision_note = models.TextField(blank=True, null=True)
    revision_count = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def get_progress_percentage(self):
        if self.status == 'Paid':
            return 20
        elif self.status == 'In Progress':
            return 40
        elif self.status == 'Revision Requested':
            return 60
        elif self.status == 'Delivered':
            return 80
        elif self.status == 'Completed':
            return 100
        return 0

    def __str__(self):
        return f"Order {self.id} - {self.service.title}"

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"

class Review(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="review")
    rating = models.PositiveIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review for Order {self.order.id}"

    class Meta:
        verbose_name = "Review"
        verbose_name_plural = "Reviews"
        ordering = ["-created_at"]

class Message(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_messages")
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"From {self.sender} to {self.receiver} at {self.timestamp}"

class Favourite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favourites")
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="favourited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "service")

    def __str__(self):
        return f"{self.user.username} - {self.service.title}"

    class Meta:
        verbose_name = "Favourite"
        verbose_name_plural = "Favourites"

# --- SIGNALS FOR AUTO-UPDATES ---
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Avg

@receiver(post_save, sender=Order)
def update_seller_stats_on_order(sender, instance, **kwargs):
    if instance.status == "Completed":
        seller_profile = instance.service.seller.seller_profile
        # count for all completed orders for this seller
        count = Order.objects.filter(service__seller=instance.service.seller, status="Completed").count()
        seller_profile.orders_completed = count
        seller_profile.save()

@receiver(post_save, sender=Review)
def update_seller_rating(sender, instance, **kwargs):
    seller_profile = instance.order.service.seller.seller_profile
    # avg rating from all reviews for this seller
    avg_rating = Review.objects.filter(order__service__seller=instance.order.service.seller).aggregate(Avg('rating'))['rating__avg']
    if avg_rating:
        seller_profile.rating = avg_rating
        seller_profile.save()

class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    message = models.CharField(max_length=255)
    link = models.CharField(max_length=255, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message}"

import threading
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

def send_email_in_background(user, message, link):
    """
    Background worker function that sends the email.
    """
    if not user.email:
        return
        
    subject = "Task Wizards: New Notification"
    from_email = settings.EMAIL_HOST_USER
    to = [user.email]
    
    site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
    
    context = {
        "user": user,
        "message": message,
        "link": link,
        "site_url": site_url,
    }
    
    # Render the HTML template we just created
    html_content = render_to_string("marketplace/email/notification.html", context)
    
    # Create the plain-text fallback gracefully
    text_content = strip_tags(html_content)
    
    # Compose the email
    email = EmailMultiAlternatives(subject, text_content, from_email, to)
    email.attach_alternative(html_content, "text/html")
    
    try:
        email.send()
    except Exception as e:
        print(f"Error sending email to {user.email}: {e}")


def send_notification(user, message, link=""):
    """
    Creates a new notification record AND triggers an asynchronous email.
    """
    # 1. Create the database record immediately
    Notification.objects.create(user=user, message=message, link=link)
    
    # 2. Fire and forget the email in a separate thread so the user doesn't wait
    email_thread = threading.Thread(
        target=send_email_in_background, 
        args=(user, message, link)
    )
    email_thread.start()

class WithdrawalRequest(models.Model):
    STATUS_CHOICES = (
        ("Pending", "Pending"),
        ("Completed", "Completed"),
        ("Rejected", "Rejected"),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="withdrawal_requests")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Withdrawal Request"
        verbose_name_plural = "Withdrawal Requests"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Withdrawal request of {self.amount} by {self.user.username}"
