from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import test_password_decryption
router = DefaultRouter()
router.register(r'categories', views.PasswordCategoryViewSet, basename='password_category')
router.register(r'entries', views.PasswordEntryViewSet, basename='password_entry') # Authenticated CRUD

urlpatterns = [
    # Web UI routes
    path('', views.password_dashboard, name='password_dashboard'),
    path('list/', views.password_list, name='password_list'),
    path('detail/<uuid:password_id>/', views.password_detail, name='password_detail'),
    path('security/', views.password_security, name='password_security'),
    path('settings/', views.password_settings, name='security_settings'),
    
    # API routes
    path('api/', include(router.urls)), # Includes categories and entries (authenticated)
    path('api/security-settings/', views.SecuritySettingsView.as_view(), name='api_security_settings'),
    path('api/master-password/', views.MasterPasswordView.as_view(), name='master_password_setup_change'), # Renamed for clarity
    path('api/master-password/status/', views.MasterPasswordStatusView.as_view(), name='master_password_status'), # New
    path('api/master-password/verify/', views.VerifyMasterPasswordView.as_view(), name='master_password_verify'), # Renamed for clarity
    path('api/history/<uuid:password_entry_id>/', views.PasswordHistoryViewSet.as_view({'get': 'list'}), name='password_history'),
    path('api/create-password/', views.create_password, name='create_password'),
    path('api/web-create-password/', views.web_create_password, name='web_create_password'),
    path('api/mobile-create-password/', views.mobile_create_password, name='mobile_create_password'),
    path('api/generate-password/', views.generate_password_api, name='generate_password_api'),
    path('api/has-master-password/', views.has_master_password, name='has_master_password'),
    path('api/test-decrypt/<uuid:entry_id>/', test_password_decryption),
    # Mobile API routes
    path('api/mobile/entries/', views.MobilePasswordEntryView.as_view(), name='mobile_password_entries'),
] 