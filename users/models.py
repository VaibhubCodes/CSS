from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    google_id = models.CharField(max_length=100, blank=True, null=True)
    profile_picture = models.URLField(max_length=500, blank=True, null=True)
    assistant_settings = models.JSONField(null=True, blank=True)
    
    def __str__(self):
        return self.email