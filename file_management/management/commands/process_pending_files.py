from django.core.management.base import BaseCommand
from file_management.models import UserFile, FileCategory, OCRResult
from file_management.views import process_document_ocr_logic
import time

class Command(BaseCommand):
    help = 'Process files with pending auto-categorization'

    def handle(self, *args, **options):
        # Get all files with pending auto-categorization
        pending_files = UserFile.objects.filter(pending_auto_categorization=True)
        self.stdout.write(f"Found {pending_files.count()} files with pending auto-categorization")
        
        # Ensure Miscellaneous category exists
        misc_category, _ = FileCategory.objects.get_or_create(
            name='Miscellaneous',
            defaults={'is_default': True, 'description': 'Uncategorized files'}
        )
        
        for file in pending_files:
            self.stdout.write(f"Processing file {file.id}: {file.original_filename}")
            
            try:
                # Check if OCR already exists
                ocr_exists = OCRResult.objects.filter(file=file).exists()
                if ocr_exists:
                    self.stdout.write(f"  OCR result already exists for file {file.id}")
                
                # Process the file
                result = process_document_ocr_logic(file.user_id, file.id)
                self.stdout.write(f"  OCR result: {result}")
                
                # Sleep briefly to avoid overwhelming the system
                time.sleep(1)
                
                # Double-check the pending flag was cleared
                file.refresh_from_db()
                if file.pending_auto_categorization:
                    self.stdout.write(f"  Warning: Pending flag still set for file {file.id}, clearing manually")
                    file.pending_auto_categorization = False
                    file.save(update_fields=['pending_auto_categorization'])
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Error processing file {file.id}: {str(e)}"))
                
                # Clear the pending flag anyway
                try:
                    file.pending_auto_categorization = False
                    if not file.category:
                        file.category = misc_category
                    file.save(update_fields=['pending_auto_categorization', 'category'])
                    self.stdout.write(f"  Cleared pending flag for file {file.id} after error")
                except Exception as inner_e:
                    self.stdout.write(self.style.ERROR(f"  Failed to clear pending flag: {str(inner_e)}"))
        
        # Check if any files still have pending flags
        still_pending = UserFile.objects.filter(pending_auto_categorization=True).count()
        if still_pending > 0:
            self.stdout.write(self.style.WARNING(f"{still_pending} files still have pending auto-categorization flags"))
        else:
            self.stdout.write(self.style.SUCCESS("All pending auto-categorization flags have been cleared")) 