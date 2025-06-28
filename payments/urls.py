from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'subscriptions', views.SubscriptionViewSet, basename='subscription')
router.register(r'transactions', views.PaymentTransactionViewSet, basename='transaction')
router.register(r'plans', views.SubscriptionPlanViewSet, basename='plans')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/verify-payment/', views.verify_payment, name='verify_payment'),
    path('plans/', views.get_subscription_plans, name='subscription_plans'),
    path('subscribe/<str:plan_code>/', views.create_subscription, name='create_subscription'),
    path('payment/callback/', views.payment_callback, name='payment_callback'),
    path('api/mobile/plans/', views.mobile_subscription_plans, name='mobile_subscription_plans'),
    path('api/mobile/subscribe/', views.mobile_create_subscription, name='mobile_create_subscription'),
    path('api/user/subscription-info/', views.get_user_subscription_info, name='user_subscription_info'),
]