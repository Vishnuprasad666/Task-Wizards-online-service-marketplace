from django.contrib.auth.models import AbstractUser
from django.db import models
from random import randint
from django.core.mail import send_mail
from django.conf import settings


class User(AbstractUser):

    ROLE_CHOICES = (
        ("Buyer", "Buyer"),
        ("Seller", "Seller"),
        ("Unassigned", "Unassigned"),
    )
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="Unassigned")
    is_seller = models.BooleanField(default=False)
    is_buyer = models.BooleanField(default=False)
    phone = models.CharField(max_length=15, blank=True, null=True)
    location = models.CharField(max_length=100, blank=True)
    linkedin_profile = models.URLField(blank=True, null=True)
    twitter_profile = models.URLField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    otp = models.CharField(max_length=10, null=True, blank=True)

    def generate_otp(self):
        otp_number = str(randint(100000, 999999))
        self.otp = otp_number
        self.save()
        send_mail(
        "Your OTP Verification Code",
        f"Your OTP is: {otp_number}",
        settings.EMAIL_HOST_USER,
        [self.email],
        fail_silently=False,
    )


# BUYER PROFILE

class BuyerProfile(models.Model):
    
    owner = models.OneToOneField(User,on_delete=models.CASCADE,related_name="buyer_profile")
    bio = models.CharField(max_length=300, blank=True)
    company_name = models.CharField(max_length=100, blank=True)
    interests = models.CharField(max_length=200, blank=True)
    website = models.URLField(blank=True)
    address = models.TextField(null=True, blank=True)
    photo = models.ImageField(upload_to="buyer_profiles/",default="buyer_profiles/default.png")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Buyer Profile"
        verbose_name_plural = "Buyer Profiles"

    def __str__(self):
        return f"Buyer: {self.owner.username}"


# SELLER PROFILE

class SellerProfile(models.Model):

    owner = models.OneToOneField(User,on_delete=models.CASCADE,related_name="seller_profile")
    bio = models.CharField(max_length=300, blank=True)
    expertise = models.CharField(max_length=200, blank=True)
    skills = models.CharField(max_length=300, blank=True)
    education = models.CharField(max_length=200, blank=True)
    portfolio_link = models.URLField(blank=True)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_available = models.BooleanField(default=True)
    photo = models.ImageField(upload_to="seller_profiles/",default="seller_profiles/default.png")
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)
    orders_completed = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def rank_score(self):
        # Formula from guide: score = rating * 0.4 + orders_completed * 0.6
        return float(self.rating) * 0.4 + self.orders_completed * 0.6

    class Meta:
        verbose_name = "Seller Profile"
        verbose_name_plural = "Seller Profiles"

    def __str__(self):
        return f"Seller: {self.owner.username}"
    
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if instance.is_buyer:
        BuyerProfile.objects.get_or_create(owner=instance)
    if instance.is_seller:
        SellerProfile.objects.get_or_create(owner=instance)
    
    # Backward compatibility for 'role' field during transition
    if not instance.is_buyer and not instance.is_seller:
        if instance.role == "Buyer":
            # Use update() instead of save() to avoid re-triggering this signal
            User.objects.filter(pk=instance.pk).update(is_buyer=True)
            BuyerProfile.objects.get_or_create(owner=instance)
        elif instance.role == "Seller":
            User.objects.filter(pk=instance.pk).update(is_seller=True)
            SellerProfile.objects.get_or_create(owner=instance)