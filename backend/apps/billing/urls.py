from django.urls import path

from . import views

app_name = "billing"

urlpatterns = [
    path("plans", views.PlanListView.as_view(), name="plans"),
    path("me/subscription", views.SubscriptionView.as_view(), name="subscription"),
    path("me/usage", views.UsageView.as_view(), name="usage"),
    path("billing/checkout", views.CheckoutView.as_view(), name="checkout"),
    path("billing/portal", views.PortalView.as_view(), name="portal"),
    path("billing/invoices", views.InvoiceListView.as_view(), name="invoices"),
    path("billing/webhook/stripe", views.StripeWebhookView.as_view(), name="stripe-webhook"),
]
