from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LoginView, LogoutView
from django.conf import settings
from django.views.static import serve


urlpatterns = [
    path('admin/', admin.site.urls),
    path('file_management/', include('file_management.urls')),
    path('auth/', include('users.urls')),
    path('login/', LoginView.as_view(redirect_authenticated_user=True, next_page='/file_management/files/'), name='login'),
    # path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('payment/', include('payments.urls')),
    path('storage/', include('storage_management.urls')),
    path('voice/', include('voice_assistant.urls')),
    path('password_management/', include('password_management.urls')),
    path('coins/', include('coin_wallet.urls')),
    path('media/', serve, {'document_root': settings.MEDIA_ROOT}),
    path('weblinks/', include('weblinks.urls')),
    path('coupons/', include('coupons.urls')),


]

