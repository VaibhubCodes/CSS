from django.core.management.base import BaseCommand
from file_management.services import OCRService

class Command(BaseCommand):
    help = 'Check and complete pending OCR jobs'

    def handle(self, *args, **options):
        ocr_service = OCRService()
        ocr_service.check_pending_jobs()
        self.stdout.write(self.style.SUCCESS('Successfully checked pending OCR jobs'))
