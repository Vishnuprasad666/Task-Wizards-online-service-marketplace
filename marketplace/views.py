import razorpay
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import HttpResponseBadRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db.models import Q, Count
from django.contrib.auth import get_user_model

from marketplace.models import Service, Order, Category, Message, Review, Favourite
from marketplace.forms import ServiceForm
from account.views import BuyerRequiredMixin, SellerRequiredMixin

User = get_user_model()
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

# --- BUYER VIEWS ---

class ServiceListView(ListView):
    model = Service
    template_name = "marketplace/service_list.html"
    context_object_name = "services"
    paginate_by = 9

    def get_queryset(self):
        queryset = super().get_queryset()
        category_id = self.request.GET.get("category")
        search_query = self.request.GET.get("search")
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if search_query:
            queryset = queryset.filter(Q(title__icontains=search_query) | Q(description__icontains=search_query))
            
        min_price = self.request.GET.get("min_price")
        max_price = self.request.GET.get("max_price")
        
        if min_price and min_price.isdigit():
            queryset = queryset.filter(price__gte=int(min_price))
        if max_price and max_price.isdigit():
            queryset = queryset.filter(price__lte=int(max_price))
        
        sort_by = self.request.GET.get("sort")
        if sort_by == "price_low":
            queryset = queryset.order_by("price")
        elif sort_by == "price_high":
            queryset = queryset.order_by("-price")
        elif sort_by == "newest":
            queryset = queryset.order_by("-created_at")
        elif sort_by == "best_selling":
            queryset = queryset.annotate(num_orders=Count('orders', filter=Q(orders__status='Completed'))).order_by("-num_orders")
        else:
            queryset = queryset.order_by("-seller__seller_profile__rating", "-created_at")
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Category.objects.all()
        if self.request.user.is_authenticated:
            context["user_favourite_ids"] = Favourite.objects.filter(user=self.request.user).values_list('service_id', flat=True)
        return context

class ServiceDetailView(DetailView):
    model = Service
    template_name = "marketplace/service_detail.html"
    context_object_name = "service"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["razorpay_key_id"] = settings.RAZORPAY_KEY_ID
        if self.request.user.is_authenticated:
            context["is_favourite"] = Favourite.objects.filter(user=self.request.user, service=self.object).exists()
        # Get reviews for this service
        context["reviews"] = Review.objects.filter(order__service=self.object).order_by("-created_at")
        return context

# --- SELLER VIEWS ---

class SellerServiceListView(LoginRequiredMixin, SellerRequiredMixin, ListView):
    model = Service
    template_name = "marketplace/seller_service_list.html"
    context_object_name = "services"

    def get_queryset(self):
        return Service.objects.filter(seller=self.request.user)

class ServiceCreateView(LoginRequiredMixin, SellerRequiredMixin, CreateView):
    model = Service
    form_class = ServiceForm
    template_name = "marketplace/service_form.html"
    success_url = reverse_lazy("marketplace:seller_service_list")

    def form_valid(self, form):
        form.instance.seller = self.request.user
        messages.success(self.request, "Service created successfully!")
        return super().form_valid(form)

class ServiceUpdateView(LoginRequiredMixin, SellerRequiredMixin, UpdateView):
    model = Service
    form_class = ServiceForm
    template_name = "marketplace/service_form.html"
    success_url = reverse_lazy("marketplace:seller_service_list")

    def get_queryset(self):
        return Service.objects.filter(seller=self.request.user)

class ServiceDeleteView(LoginRequiredMixin, SellerRequiredMixin, DeleteView):
    model = Service
    template_name = "marketplace/service_confirm_delete.html"
    success_url = reverse_lazy("marketplace:seller_service_list")

    def get_queryset(self):
        return Service.objects.filter(seller=self.request.user)

# --- PAYMENT & ORDER FLOW ---

class PurchaseServiceView(LoginRequiredMixin, BuyerRequiredMixin, View):
    def post(self, request, pk):
        service = get_object_or_404(Service, pk=pk)
        buyer_note = request.POST.get("buyer_note", "")
        
        amount = int(service.price * 100)
        data = {"amount": amount, "currency": "INR", "payment_capture": "1"}
        
        try:
            razorpay_order = razorpay_client.order.create(data=data)
            razorpay_order_id = razorpay_order['id']
            
            Order.objects.create(
                buyer=request.user,
                service=service,
                amount=service.price,
                razorpay_order_id=razorpay_order_id,
                status="Pending",
                buyer_note=buyer_note
            )
            
            context = {
                "service": service,
                "razorpay_order_id": razorpay_order_id,
                "razorpay_key_id": settings.RAZORPAY_KEY_ID,
                "amount": amount,
                "currency": "INR",
                "callback_url": request.build_absolute_uri(reverse_lazy("marketplace:payment_callback"))
            }
            return render(request, "marketplace/payment_checkout.html", context)
            
        except Exception as e:
            messages.error(request, f"Payment initialization failed: {str(e)}")
            return redirect("marketplace:service_detail", pk=pk)

@method_decorator(csrf_exempt, name='dispatch')
class PaymentCallbackView(View):
    def post(self, request):
        payment_id = request.POST.get("razorpay_payment_id")
        order_id = request.POST.get("razorpay_order_id")
        signature = request.POST.get("razorpay_signature")
        
        params_dict = {
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        }
        
        try:
            razorpay_client.utility.verify_payment_signature(params_dict)
            order = Order.objects.get(razorpay_order_id=order_id)
            order.razorpay_payment_id = payment_id
            order.razorpay_signature = signature
            order.status = "Paid"  # Guide implies Paid should move to "In Progress" eventually
            order.save()
            messages.success(request, "Payment successful! The seller will start working soon.")
            return redirect("marketplace:order_detail", pk=order.pk)
        except Exception as e:
            messages.error(request, f"Payment verification failed: {str(e)}")
            return redirect("marketplace:service_list")

# --- ORDER FULFILLMENT ---

class OrderDeliverView(LoginRequiredMixin, SellerRequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk, service__seller=request.user)
        delivery_file = request.FILES.get("delivery_file")
        delivery_message = request.POST.get("delivery_message")
        
        if delivery_file:
            order.delivery_file = delivery_file
            order.delivery_message = delivery_message
            order.status = "Delivered"
            order.save()
            messages.success(request, "Task delivered successfully!")
        else:
            messages.error(request, "Please attach a file for delivery.")
            
        return redirect("marketplace:order_detail", pk=pk)

class OrderStartView(LoginRequiredMixin, SellerRequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk, service__seller=request.user, status="Paid")
        order.status = "In Progress"
        order.save()
        messages.success(request, "Order started! Let's get to work.")
        return redirect("marketplace:order_detail", pk=pk)

class OrderCompleteView(LoginRequiredMixin, BuyerRequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk, buyer=request.user, status="Delivered")
        order.status = "Completed"
        order.save()
        
        # Update seller stats
        seller_profile = order.service.seller.seller_profile
        seller_profile.orders_completed += 1
        seller_profile.save()
        
        # Create a Review
        rating = request.POST.get("rating")
        comment = request.POST.get("comment")
        if rating:
            Review.objects.create(order=order, rating=rating, comment=comment)
            # Update average rating
            reviews = Review.objects.filter(order__service__seller=order.service.seller)
            avg_rating = sum(r.rating for r in reviews) / reviews.count()
            seller_profile.rating = avg_rating
            seller_profile.save()
            
        messages.success(request, "Order completed and review submitted!")
        return redirect("marketplace:order_detail", pk=pk)

class OrderRevisionView(LoginRequiredMixin, BuyerRequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk, buyer=request.user, status="Delivered")
        revision_note = request.POST.get("revision_note")
        if revision_note:
            order.status = "Revision Requested"
            order.revision_note = revision_note
            order.revision_count += 1
            order.save()
            messages.success(request, "Revision requested successfully.")
        else:
            messages.error(request, "Please provide a revision note.")
        return redirect("marketplace:order_detail", pk=pk)

class OrderDetailView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = "marketplace/order_detail.html"
    context_object_name = "order"

    def get_queryset(self):
        # Ensure only the buyer or the seller of the order can view it
        if self.request.user.role == "Buyer":
            return Order.objects.filter(buyer=self.request.user)
        else:
            return Order.objects.filter(service__seller=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add messages related to this order or common chat history
        other_user = self.object.service.seller if self.request.user.role == "Buyer" else self.object.buyer
        context["chat_user"] = other_user
        return context

# --- MESSAGING ---

class InboxView(LoginRequiredMixin, TemplateView):
    template_name = "marketplace/messaging/inbox.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        # Find all users this user has messaged or received messages from
        sent_to = Message.objects.filter(sender=user).values_list('receiver', flat=True)
        received_from = Message.objects.filter(receiver=user).values_list('sender', flat=True)
        contact_ids = set(list(sent_to) + list(received_from))
        
        contacts = User.objects.filter(id__in=contact_ids)
        context["contacts"] = contacts
        return context

class ChatDetailView(LoginRequiredMixin, View):
    def get(self, request, user_id):
        other_user = get_object_or_404(User, id=user_id)
        messages_list = Message.objects.filter(
            (Q(sender=request.user) & Q(receiver=other_user)) |
            (Q(sender=other_user) & Q(receiver=request.user))
        ).order_by("timestamp")
        
        # Mark as read
        messages_list.filter(receiver=request.user).update(is_read=True)
        
        # Add contacts for sidebar
        user = self.request.user
        sent_to = Message.objects.filter(sender=user).values_list('receiver', flat=True)
        received_from = Message.objects.filter(receiver=user).values_list('sender', flat=True)
        contact_ids = set(list(sent_to) + list(received_from))
        contacts = User.objects.filter(id__in=contact_ids)
        
        return render(request, "marketplace/messaging/chat.html", {
            "other_user": other_user,
            "messages_list": messages_list,
            "contacts": contacts
        })

    def post(self, request, user_id):
        other_user = get_object_or_404(User, id=user_id)
        content = request.POST.get("content")
        if content:
            Message.objects.create(sender=request.user, receiver=other_user, content=content)
        return redirect("marketplace:chat_detail", user_id=user_id)

class ToggleFavouriteView(LoginRequiredMixin, BuyerRequiredMixin, View):
    def post(self, request, pk):
        service = get_object_or_404(Service, pk=pk)
        favourite, created = Favourite.objects.get_or_create(user=request.user, service=service)
        
        if not created:
            favourite.delete()
            status = "removed"
        else:
            status = "added"
            
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({"status": status})
            
        return redirect(request.META.get('HTTP_REFERER', 'marketplace:service_list'))

class FavouriteListView(LoginRequiredMixin, BuyerRequiredMixin, ListView):
    model = Favourite
    template_name = "marketplace/favourite_list.html"
    context_object_name = "favourites"

    def get_queryset(self):
        return Favourite.objects.filter(user=self.request.user).select_related('service').order_by("-created_at")
