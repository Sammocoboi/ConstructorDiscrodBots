from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("id", "type", "payload", "read_at", "created_at")
        read_only_fields = ("id", "type", "payload", "created_at")
