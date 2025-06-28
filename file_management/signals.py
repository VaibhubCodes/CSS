from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings

from .models import OCRResult, UserFile, FileCategory

# @receiver(post_save, sender=OCRResult)
# def notify_category_change(sender, instance, created, **kwargs):
#     """
#     Send a notification when OCR completes and changes a file's category
#     """
#     # Only proceed if the result is completed and has text
#     if instance.status == 'completed' and instance.text_content:
#         try:
#             user_file = instance.file
            
#             # OCR processing has just been completed - check if categorization has changed
#             if hasattr(user_file, '_original_category_id') and user_file._original_category_id:
#                 original_category_id = user_file._original_category_id
#                 current_category_id = user_file.category_id if user_file.category else None
                
#                 # If category changed, notify user
#                 if original_category_id != current_category_id:
#                     try:
#                         original_category = FileCategory.objects.get(id=original_category_id)
#                         current_category = FileCategory.objects.get(id=current_category_id) if current_category_id else None
                        
#                         if current_category:
#                             # Send email notification
#                             send_mail(
#                                 'File Category Changed',
#                                 f'Your file "{user_file.original_filename}" has been moved from "{original_category.name}" to "{current_category.name}" based on its content.',
#                                 settings.DEFAULT_FROM_EMAIL,
#                                 [user_file.user.email],
#                                 fail_silently=True,
#                             )
#                     except Exception as e:
#                         print(f"Error in category change notification: {str(e)}")
#         except Exception as e:
#             print(f"Error in OCR result signal handler: {str(e)}")



from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from .models import UserFile

@receiver(post_save, sender=UserFile)
def trigger_ocr_for_paired_documents(sender, instance, created, **kwargs):
    """Trigger OCR when documents are paired"""
    if not created and instance.paired_document:
        # Check if both documents need OCR
        files_to_process = []
        
        # Check current file
        if instance.file_type in ['document', 'image']:
            try:
                from .models import OCRResult
                ocr_result = OCRResult.objects.get(file=instance)
                if ocr_result.status not in ['completed', 'processing']:
                    files_to_process.append(instance)
            except OCRResult.DoesNotExist:
                files_to_process.append(instance)
        
        # Check paired document
        paired_doc = instance.paired_document
        if paired_doc and paired_doc.file_type in ['document', 'image']:
            try:
                from .models import OCRResult
                ocr_result = OCRResult.objects.get(file=paired_doc)
                if ocr_result.status not in ['completed', 'processing']:
                    files_to_process.append(paired_doc)
            except OCRResult.DoesNotExist:
                files_to_process.append(paired_doc)
        
        # Process OCR for files that need it
        if files_to_process:
            try:
                from .services import OCRService
                ocr_service = OCRService()
                for file_obj in files_to_process:
                    print(f"[Signal] Triggering OCR for paired document: {file_obj.id}")
                    ocr_service.process_file(file_obj)
            except Exception as e:
                print(f"[Signal] Error processing paired document OCR: {str(e)}")
