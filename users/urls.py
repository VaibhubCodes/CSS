from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

router = DefaultRouter()
router.register(r'profile', views.UserViewSet, basename='profile')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/register/', views.register_user, name='api_register'),
    path('api/verify-email/', views.verify_email, name='api_verify_email'),
    path('api/resend-verification/', views.resend_verification, name='api_resend_verification'),
    path('api/token/', views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/google/', views.google_auth, name='google_auth'),
    path('api/mobile/google/', views.google_mobile_auth, name='google_mobile_auth'),
    path('login/google/', views.google_login, name='google_login'),
    path('login/google/callback/', views.google_callback, name='google_callback'),
    path('signup/', views.signup, name='signup'),
    path('verify-email/', views.verify_email, name='verify_email'),
    path('', include(router.urls)),
    path('api/mobile/register/', views.mobile_signup, name='mobile_register'),
    path('api/mobile/verify-email/', views.mobile_verify_email, name='mobile_verify_email'),
    path('api/mobile/login/', views.mobile_login, name='mobile_login'),
    path('api/mobile/register/', views.mobile_register, name='mobile_register'),
    path('api/mobile/token/refresh/', views.mobile_token_refresh, name='mobile_token_refresh'),
]