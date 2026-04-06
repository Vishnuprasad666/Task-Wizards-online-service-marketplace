from django.urls import path
from . import views

app_name = "marketplace"

urlpatterns = [
    # Buyer URLs
    path("services/", views.ServiceListView.as_view(), name="service_list"),
    path("services/<int:pk>/", views.ServiceDetailView.as_view(), name="service_detail"),
    path("services/<int:pk>/purchase/", views.PurchaseServiceView.as_view(), name="purchase_service"),
    path("payment/callback/", views.PaymentCallbackView.as_view(), name="payment_callback"),
    
    # Seller URLs
    path("my-services/", views.SellerServiceListView.as_view(), name="seller_service_list"),
    path("my-services/add/", views.ServiceCreateView.as_view(), name="service_create"),
    path("my-services/<int:pk>/edit/", views.ServiceUpdateView.as_view(), name="service_update"),
    path("my-services/<int:pk>/delete/", views.ServiceDeleteView.as_view(), name="service_delete"),
    path("withdraw/", views.WithdrawalRequestView.as_view(), name="withdrawal_request"),
    
    # Order Fulfillment
    path("order/<int:pk>/deliver/", views.OrderDeliverView.as_view(), name="order_deliver"),
    path("order/<int:pk>/complete/", views.OrderCompleteView.as_view(), name="order_complete"),
    path("order/<int:pk>/cancel/", views.OrderCancelView.as_view(), name="order_cancel"),
    path("order/<int:pk>/reject/", views.OrderRejectView.as_view(), name="order_reject"),
    
    # Messaging
    path("inbox/", views.InboxView.as_view(), name="inbox"),
    path("chat/<int:user_id>/", views.ChatDetailView.as_view(), name="chat_detail"),
    path("favourite/toggle/<int:pk>/", views.ToggleFavouriteView.as_view(), name="toggle_favourite"),
    path("favourites/", views.FavouriteListView.as_view(), name="favourite_list"),
    path("order/<int:pk>/", views.OrderDetailView.as_view(), name="order_detail"),
    path("order/<int:pk>/start/", views.OrderStartView.as_view(), name="order_start"),
    path("order/<int:pk>/revision/", views.OrderRevisionView.as_view(), name="order_revision"),
    
    # Notifications
    path("notifications/", views.NotificationListView.as_view(), name="notification_list"),
    path("notifications/<int:pk>/read/", views.MarkNotificationReadView.as_view(), name="mark_notification_read"),
    path("notifications/unread-count/", views.UnreadNotificationCountView.as_view(), name="unread_notification_count"),
]
