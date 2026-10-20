"""Notifications views"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import NotificationService

class NotificationPingView(APIView):
    def get(self, request):
        return Response({"status": "ok", "service": "notifications"})
