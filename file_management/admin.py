from django.contrib import admin
from .models import UserFile, FileCategory, OCRResult, OCRPreference, CardDetails, AppSubscription, ExpiryDetails
from storage_management.utils import S3StorageManager
from django.db import transaction
from .views import process_document_ocr_logic
from .services import OCRService
from django.contrib import messages

@admin.register(UserFile)
class UserFileAdmin(admin.ModelAdmin):
    list_display = ('original_filename', 'user', 'file_type', 'category', 'upload_date', 'get_file_size_display', 'is_public', 'pending_auto_categorization')
    list_filter = ('file_type', 'category', 'is_public', 'upload_date', 'pending_auto_categorization')
    search_fields = ('original_filename', 'user__email')
    readonly_fields = ('s3_key', 'file_size', 'upload_date')
    
    # def get_s3_status(self, obj):
    #     """Check if file exists in S3"""
    #     try:
    #         if not obj.s3_key:
    #             return "❌ No S3 Key"
            
    #         storage_manager = S3StorageManager(obj.user)
            
    #         # Check multiple possible keys
    #         possible_keys = [
    #             obj.s3_key,
    #             obj.file.name if obj.file else None,
    #             f"uploads/{obj.original_filename}" if obj.original_filename else None,
    #             f"user_{obj.user.id}/{obj.original_filename}" if obj.original_filename else None,
    #         ]
            
    #         for key in possible_keys:
    #             if key and storage_manager.file_exists(key):
    #                 return f"✅ Found: {key}"
            
    #         return "❌ Not Found in S3"
            
    #     except Exception as e:
    #         return f"❌ Error: {str(e)}"
    
    # get_s3_status.short_description = 'S3 Status'
    
    # def get_s3_debug_info(self, obj):
    #     """Get detailed S3 debug information"""
    #     try:
    #         info = []
    #         info.append(f"S3 Key: {obj.s3_key}")
    #         info.append(f"File Name: {obj.file.name if obj.file else 'None'}")
    #         info.append(f"Original Filename: {obj.original_filename}")
            
    #         if obj.s3_key or obj.file:
    #             storage_manager = S3StorageManager(obj.user)
                
    #             # List all files for this user
    #             user_files = storage_manager.list_user_files_with_details()
    #             info.append(f"\nAll S3 files for user:")
    #             for file_info in user_files[:10]:  # Show first 10
    #                 info.append(f"  - {file_info['key']} ({file_info['size']} bytes)")
                
    #             if len(user_files) > 10:
    #                 info.append(f"  ... and {len(user_files) - 10} more files")
            
    #         return "\n".join(info)
            
    #     except Exception as e:
    #         return f"Error getting debug info: {str(e)}"
    
    # get_s3_debug_info.short_description = 'S3 Debug Info'
    
    def save_model(self, request, obj, form, change):
        """Override save_model to trigger OCR for new document files"""
        is_new = not obj.pk
        super().save_model(request, obj, form, change)
        
        # Only trigger OCR for new document/image files with pending auto-categorization
        if is_new and obj.file_type in ['document', 'image'] and obj.pending_auto_categorization:
            print(f"[Admin] Triggering OCR for new file {obj.id}")
            try:
                from .services import OCRService
                ocr_service = OCRService()
                result = ocr_service.process_file(obj)
                print(f"[Admin] OCR result: {result}")
            except Exception as e:
                print(f"[Admin] OCR error: {str(e)}")
                # Ensure pending flag is cleared on error
                try:
                    obj.pending_auto_categorization = False
                    if not obj.category:
                        misc_category, _ = FileCategory.objects.get_or_create(
                            name='Miscellaneous',
                            defaults={'is_default': True}
                        )
                        obj.category = misc_category
                    obj.save(update_fields=['pending_auto_categorization', 'category'])
                except Exception as inner_e:
                    print(f"[Admin] Error clearing pending flag: {inner_e}")

    def get_file_url(self, obj):
        """Generate temporary URL for admin preview"""
        storage_manager = S3StorageManager(obj.user)
        return storage_manager.get_file_url(obj.s3_key)
    
    get_file_url.short_description = 'File URL'

    def file_size_display(self, obj):
        size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
    file_size_display.short_description = 'File Size'


@admin.register(FileCategory)
class FileCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_default', 'created_by')
    list_filter = ('is_default',)
    search_fields = ('name',)


@admin.register(OCRResult)
class OCRResultAdmin(admin.ModelAdmin):
    list_display = ('file', 'status', 'processed_date')
    list_filter = ('status',)
    search_fields = ('file__original_filename',)


@admin.register(OCRPreference)
class OCRPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'preference')
    list_filter = ('preference',)


@admin.register(CardDetails)
class CardDetailsAdmin(admin.ModelAdmin):
    list_display = ('bank_name', 'card_type', 'card_holder', 'user')
    list_filter = ('card_type', 'bank_name')
    search_fields = ('card_holder', 'bank_name', 'user__email')


@admin.register(AppSubscription)
class AppSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('app_name', 'subscription_type', 'user', 'status')
    list_filter = ('subscription_type', 'status')
    search_fields = ('app_name', 'user__email')

@admin.action(description='Re-process OCR for selected files')
def reprocess_ocr(modeladmin, request, queryset):
    """Custom admin action to re-trigger OCR processing."""
    processed_count = 0
    ocr_service = OCRService()
    for file in queryset.filter(file_type__in=['document', 'image']):
        try:
            # Set the pending flag to ensure categorization is attempted
            file.pending_auto_categorization = True
            file.save(update_fields=['pending_auto_categorization'])
            
            # Trigger OCR processing
            ocr_service.process_file(file)
            processed_count += 1
        except Exception as e:
            modeladmin.message_user(request, f"Error processing file {file.id}: {e}", messages.ERROR)
            


@admin.register(ExpiryDetails)
class ExpiryDetailsAdmin(admin.ModelAdmin):
    """Admin view for ExpiryDetails, which is system-managed."""
    list_display = ('get_item_name', 'document_type', 'expiry_date', 'moved_to_expired')
    list_filter = ('document_type', 'moved_to_expired', 'expiry_date')
    readonly_fields = ('document', 'card', 'subscription', 'document_type', 'expiry_date', 'moved_to_expired', 'original_category', 'expired_s3_key')

    def get_item_name(self, obj):
        if obj.document:
            return obj.document.original_filename
        if obj.card:
            return f"Card: **** {obj.card.card_number[-4:]}"
        if obj.subscription:
            return f"Subscription: {obj.subscription.app_name}"
        return "N/A"
    get_item_name.short_description = 'Item'
    
    def has_add_permission(self, request):
        return False
        
    def has_change_permission(self, request, obj=None):
        return False
    
