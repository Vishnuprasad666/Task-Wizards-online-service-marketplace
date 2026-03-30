from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from marketplace.models import Service, Order, Category, SellerProfile, BuyerProfile

User = get_user_model()

class MarketplaceFlowTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name="Design")
        
        # Create Seller
        self.seller = User.objects.create_user(username="seller", password="password", role="Seller", email="seller@example.com", is_verified=True)
        # Profile is created via signals
        
        # Create Buyer
        self.buyer = User.objects.create_user(username="buyer", password="password", role="Buyer", email="buyer@example.com", is_verified=True)
        
        # Create Service
        self.service = Service.objects.create(
            seller=self.seller,
            category=self.category,
            title="Logo Design",
            description="Professional logo design",
            price=10.00,
            delivery_time=3
        )
        
        # Create Order
        self.order = Order.objects.create(
            buyer=self.buyer,
            service=self.service,
            amount=10.00,
            status="Paid"
        )

    def test_order_detail_access(self):
        # Buyer can access
        self.client.login(username="buyer", password="password")
        response = self.client.get(reverse("marketplace:order_detail", kwargs={"pk": self.order.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Logo Design")
        self.client.logout()

        # Seller can access
        self.client.login(username="seller", password="password")
        response = self.client.get(reverse("marketplace:order_detail", kwargs={"pk": self.order.pk}))
        self.assertEqual(response.status_code, 200)
        self.client.logout()

        # Another user cannot access (if we had another user)
        other_user = User.objects.create_user(username="other", password="password", role="Buyer", email="other@example.com", is_verified=True)
        self.client.login(username="other", password="password")
        response = self.client.get(reverse("marketplace:order_detail", kwargs={"pk": self.order.pk}))
        self.assertEqual(response.status_code, 404) # get_queryset filters them out

    def test_order_start_flow(self):
        self.client.login(username="seller", password="password")
        response = self.client.post(reverse("marketplace:order_start", kwargs={"pk": self.order.pk}))
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "In Progress")
        self.assertRedirects(response, reverse("marketplace:order_detail", kwargs={"pk": self.order.pk}))

    def test_order_deliver_redirection(self):
        self.order.status = "In Progress"
        self.order.save()
        self.client.login(username="seller", password="password")
        
        # Simulate file upload
        import io
        from django.core.files.uploadedfile import SimpleUploadedFile
        file_content = b"test content"
        delivery_file = SimpleUploadedFile("result.txt", file_content)
        
        response = self.client.post(reverse("marketplace:order_deliver", kwargs={"pk": self.order.pk}), {
            "delivery_file": delivery_file,
            "delivery_message": "Here is your logo"
        })
        
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "Delivered")
        self.assertRedirects(response, reverse("marketplace:order_detail", kwargs={"pk": self.order.pk}))
