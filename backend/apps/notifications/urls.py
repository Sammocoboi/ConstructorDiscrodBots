"""Notifications urls"""
from django.urls import path
from .views import NotificationPingView

urlpatterns = [
    path("notifications/ping", NotificationPingView.as_view(), name="notification-ping"),
]
