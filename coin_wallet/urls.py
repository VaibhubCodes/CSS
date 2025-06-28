from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'wallet', views.CoinWalletViewSet, basename='coin-wallet')

urlpatterns = [
    # API URLs
    path('api/', include(router.urls)),
    path('api/award-coins/<int:file_id>/', views.award_coins_for_file, name='award-coins'),
    path('api/mobile-info/', views.mobile_wallet_info, name='mobile-wallet-info'),
    
    # Web template URLs
    path('dashboard/', views.coin_wallet_dashboard, name='coin-wallet-dashboard'),
    path('redeem/', views.redeem_coins, name='redeem-coins'),
] 