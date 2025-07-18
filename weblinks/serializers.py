# weblinks/serializers.py

from rest_framework import serializers
from .models import WebLink, Meeting

class WebLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebLink
        fields = ['id', 'link_name', 'url', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']


class MeetingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meeting
        fields = ['id', 'meeting_name', 'meeting_link', 'description', 'start_time', 'end_time', 'created_at']
        read_only_fields = ['id', 'created_at']

from rest_framework import serializers
from .models import WebLink, Meeting, Notification

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'notif_type', 'message', 'created_at', 'is_read']
        read_only_fields = ['id', 'created_at', 'notif_type', 'message']
