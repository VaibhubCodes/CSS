from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'storage', views.StorageViewSet, basename='storage')
router.register(r'admin-logs', views.AdminAccessLogViewSet, basename='admin-logs')

urlpatterns = [
    path('api/', include(router.urls)),
    path('info/', views.get_storage_info, name='storage_info'),

]