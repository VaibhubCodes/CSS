from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'assistant', views.VoiceAssistantViewSet, basename='assistant')

urlpatterns = [
    path('api/', include(router.urls)),
    path('assistant/', views.assistant_view, name='assistant'),
    path('voice/process/', views.process_voice, name='process_voice'),
    path('api/process/', views.process_voice_api, name='process_voice_api'),
    path('api/open-file/', views.direct_file_open_api, name='direct_file_open_api')
]