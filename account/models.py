from django.contrib.auth.models import AbstractUser
from django.db import models
from random import randint
from django.core.mail import send_mail
from django.conf import settings


class User(AbstractUser):

    ROLE_CHOICES = (
        ("Buyer", "Buyer"),
        ("Seller", "Seller"),
    )
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="Buyer")
    phone = models.CharField(max_length=15)
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
    @property
    def rank_score(self):
        # Formula from guide: score = rating * 0.4 + orders_completed * 0.6
        return float(self.rating) * 0.4 + self.orders_completed * 0.6

    def __str__(self):
        return f"Seller: {self.owner.username}"
    
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):

    if created:

        if instance.role == "Buyer":
            BuyerProfile.objects.create(owner=instance)

        elif instance.role == "Seller":
            SellerProfile.objects.create(owner=instance)