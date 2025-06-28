from celery import shared_task
import logging
import os
import requests
import pytesseract
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone
from .models import OCRResult

logger = logging.getLogger(__name__)

@shared_task
def process_ocr(ocr_id, file_url):
    """
    Process OCR on a document file
    
    Args:
        ocr_id (int): ID of the OCRResult object
        file_url (str): Presigned URL to download the file
    
    Returns:
        dict: Result of OCR processing
    """
    try:
        logger.info(f"Starting OCR processing for document ID: {ocr_id}")
        
        # Get OCR record
        try:
            ocr_record = OCRResult.objects.get(id=ocr_id)
        except OCRResult.DoesNotExist:
            logger.error(f"OCR record with ID {ocr_id} not found")
            return {"status": "error", "message": "OCR record not found"}
        
        # Download file
        try:
            response = requests.get(file_url)
            response.raise_for_status()
            file_content = BytesIO(response.content)
        except Exception as e:
            logger.error(f"Error downloading file for OCR: {str(e)}")
            ocr_record.status = "failed"
            ocr_record.error_message = f"Error downloading file: {str(e)}"
            ocr_record.completed_at = timezone.now()
            ocr_record.save()
            return {"status": "error", "message": f"Error downloading file: {str(e)}"}
        
        # Process OCR
        try:
            image = Image.open(file_content)
            text = pytesseract.image_to_string(image)
            
            # Update OCR record
            ocr_record.text_content = text
            ocr_record.status = "completed"
            ocr_record.completed_at = timezone.now()
            ocr_record.save()
            
            logger.info(f"OCR processing completed for document ID: {ocr_id}")
            return {"status": "success", "ocr_id": ocr_id, "text_length": len(text)}
            
        except Exception as e:
            logger.error(f"Error processing OCR: {str(e)}")
            ocr_record.status = "failed"
            ocr_record.error_message = f"Error processing OCR: {str(e)}"
            ocr_record.completed_at = timezone.now()
            ocr_record.save()
            return {"status": "error", "message": f"Error processing OCR: {str(e)}"}
            
    except Exception as e:
        logger.error(f"Unexpected error in OCR task: {str(e)}")
        return {"status": "error", "message": f"Unexpected error: {str(e)}"} 