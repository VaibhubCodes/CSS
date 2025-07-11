# weblinks/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WebLinkViewSet, MeetingViewSet,NotificationViewSet

router = DefaultRouter()
router.register(r'weblinks', WebLinkViewSet, basename='weblink')
router.register(r'meetings', MeetingViewSet, basename='meeting')
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('api/', include(router.urls)),
]
