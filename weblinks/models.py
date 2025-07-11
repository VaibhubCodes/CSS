# weblinks/models.py

from django.db import models
from django.conf import settings

class WebLink(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='weblinks')
    link_name = models.CharField(max_length=255)
    url = models.URLField()
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.link_name


class Meeting(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='meetings')
    meeting_name = models.CharField(max_length=255)
    meeting_link = models.URLField()
    description = models.TextField(blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.meeting_name

from django.db import models
from django.conf import settings
from django.utils import timezone

class Notification(models.Model):
    NOTIF_TYPE_CHOICES = [
        ('weblink',   'WebLink Created'),
        ('meeting',   'Meeting Created'),
        ('meeting_upcoming', 'Meeting Starting Soon'),
        # … you can add more types
    ]

    user        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    notif_type  = models.CharField(max_length=32, choices=NOTIF_TYPE_CHOICES)
    message     = models.CharField(max_length=255)
    created_at  = models.DateTimeField(auto_now_add=True)
    is_read     = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user} – {self.notif_type}: {self.message[:20]}"