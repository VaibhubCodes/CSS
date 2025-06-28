from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views


router = DefaultRouter()
router.register(r'files', views.FileViewSet, basename='file')
router.register(r'categories', views.CategoryViewSet, basename='category')
router.register(r'cards', views.CardDetailsViewSet, basename='card')
router.register(r'subscriptions', views.AppSubscriptionViewSet, basename='subscription')

urlpatterns = [
    path('upload/', views.file_upload_view, name='file_upload'),
    path('files/', views.file_list_view, name='file_list'),
    path('start_transcription/<str:file_name>/', views.start_transcription, name='start_transcription'),
    path('get_transcription_result/<str:job_name>/', views.get_transcription_result, name='get_transcription_result'),
    path('text_analysis/<str:job_name>/', views.text_analysis, name='text_analysis'),
    # path('index_document/<str:doc_id>/', views.index_existing_document, name='index_existing_document'),
    # path('search_documents/<str:job_name>/', views.search_documents, name='search_documents'),
    path('ocr/process/<int:file_id>/', views.process_document_ocr, name='process_ocr'),
    path('ocr/result/<str:job_id>/', views.get_ocr_result, name='get_ocr_result'),
    path('api/', include(router.urls)),
    path('cards/', views.card_list_view, name='card_list'),
    path('subscriptions/', views.subscription_list_view, name='subscription_list'),
    path('delete/<int:file_id>/', views.delete_file, name='delete_file'),
    path('api/files/', views.file_list_view, name='api_file_list'),
    path('api/files/<int:file_id>/', views.file_detail_view, name='api_file_detail'),
    path('api/upload/', views.file_upload_view, name='api_file_upload'),
    path('api/expired-items/', views.expired_items_view, name='api_expired_items'),
    path('api/mobile/files/', views.mobile_file_list, name='mobile_file_list'),
    path('api/mobile/files/<int:file_id>/', views.mobile_file_detail, name='mobile_file_detail'),
    path('api/mobile/files/<int:file_id>/move/', views.move_file, name='move_file'),
    path('api/mobile/files/<int:file_id>/share/', views.share_file, name='share_file'),
    path('api/mobile/files/<int:file_id>/lock/', views.lock_file, name='lock_file'),
    path('api/mobile/files/<int:file_id>/unlock/', views.unlock_file, name='unlock_file'),
    path('api/mobile/files/<int:file_id>/rename/', views.rename_file, name='rename_file'),
    path('api/mobile/files/<int:file_id>/ocr/', views.mobile_ocr_status, name='mobile_ocr_status'),
    path('api/mobile/files/<int:file_id>/process-ocr/', views.mobile_process_ocr, name='mobile_process_ocr'),
    path('api/mobile/ocr-preferences/', views.ocr_preferences, name='ocr_preferences'),
    path('api/mobile/upload/', views.mobile_file_upload, name='mobile_file_upload'),
    path('api/documents/create-pair/', views.create_document_pair, name='create_document_pair'),
    path('api/documents/<int:file_id>/break-pair/', views.break_document_pair, name='break_document_pair'),
    path('api/documents/paired/', views.get_paired_documents, name='get_paired_documents'),
    path('api/ocr/check-pending/', views.check_pending_ocr_jobs, name='check_pending_ocr'),
    path('api/ocr/status/<int:file_id>/', views.get_file_ocr_status, name='get_file_ocr_status'),
    path('api/files/<int:file_id>/toggle-favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('api/files/<int:file_id>/toggle-hidden/', views.toggle_hidden, name='toggle_hidden'),
    path('api/files/<int:file_id>/access-locked/', views.access_locked_file, name='access_locked_file'),    
]

