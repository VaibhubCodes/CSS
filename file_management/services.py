
from datetime import date
import boto3, time
from django.db import models
from django.conf import settings
from .models import ExpiryDetails, FileCategory, UserFile, CardDetails, AppSubscription, OCRResult, OCRPreference
from .utils import extract_text_from_document, FileCategorizationService

class ExpiryManagementService:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME

    def check_and_move_expired_items(self):
        today = date.today()
        expired_category, _ = FileCategory.objects.get_or_create(
            name='EXPIRED_DOCS',
            defaults={'is_default': True}
        )

        # Check cards
        expired_cards = CardDetails.objects.filter(
            expiry_year__lt=today.year,
            expiry_month__lt=today.month
        )
        for card in expired_cards:
            self._handle_expired_card(card, expired_category)

        # Check subscriptions
        expired_subscriptions = AppSubscription.objects.filter(
            end_date__lt=today,
            auto_renewal=False
        )
        for subscription in expired_subscriptions:
            self._handle_expired_subscription(subscription, expired_category)

    def _handle_expired_card(self, card, expired_category):
        if not ExpiryDetails.objects.filter(card=card).exists():
            # Create expiry record
            ExpiryDetails.objects.create(
                card=card,
                document_type='card',
                expiry_date=date(int(card.expiry_year), int(card.expiry_month), 1),
                original_category='Cards'
            )

    def _handle_expired_subscription(self, subscription, expired_category):
        if not ExpiryDetails.objects.filter(subscription=subscription).exists():
            # Create expiry record
            ExpiryDetails.objects.create(
                subscription=subscription,
                document_type='subscription',
                expiry_date=subscription.end_date,
                original_category='Subscriptions'
            )
            
            # Update subscription status
            subscription.status = 'expired'
            subscription.save()

    def move_file_to_expired_folder(self, s3_key, expired_category):
        """Move file to expired folder in S3"""
        new_key = f"expired/{s3_key}"
        try:
            # Copy the object to new location
            self.s3_client.copy_object(
                Bucket=self.bucket_name,
                CopySource={'Bucket': self.bucket_name, 'Key': s3_key},
                Key=new_key
            )
            # Delete the original
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return new_key
        except Exception as e:
            print(f"Error moving file to expired folder: {str(e)}")
            return None

    def get_expired_items(self, user):
        """Get all expired items for a user"""
        return ExpiryDetails.objects.filter(
            models.Q(document__user=user) |
            models.Q(card__user=user) |
            models.Q(subscription__user=user)
        )


class OCRService:
    def __init__(self):
        self.textract_client = boto3.client(
            'textract',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        self.categorization_service = FileCategorizationService()

    def _verify_s3_object_exists(self, s3_key):
        """Verify that the S3 object exists before processing"""
        try:
            print(f"[OCR Service] Checking S3 object: {s3_key}")
            print(f"[OCR Service] Bucket: {settings.AWS_STORAGE_BUCKET_NAME}")
            
            response = self.s3_client.head_object(
                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                Key=s3_key
            )
            
            print(f"[OCR Service] S3 object found - Size: {response['ContentLength']} bytes")
            return True
            
        except self.s3_client.exceptions.NoSuchKey:
            print(f"[OCR Service] S3 object not found: {s3_key}")
            return False
        except Exception as e:
            print(f"[OCR Service] Error checking S3 object: {str(e)}")
            return False

    def _normalize_s3_key(self, user_file):
        """Normalize and fix S3 key if needed"""
        original_key = user_file.s3_key
        
        # Try different possible S3 key formats
        possible_keys = [
            original_key,  # Original key
            user_file.file.name,  # File field name
            f"uploads/{user_file.original_filename}",  # uploads/ prefix
            f"user_{user_file.user.id}/{user_file.original_filename}",  # user prefix
            user_file.original_filename  # Just filename
        ]
        
        print(f"[OCR Service] Trying to find S3 object with these keys:")
        for i, key in enumerate(possible_keys):
            if key:  # Skip empty keys
                print(f"[OCR Service]   {i+1}. {key}")
                if self._verify_s3_object_exists(key):
                    if key != original_key:
                        print(f"[OCR Service] Found working S3 key: {key}")
                        # Update the file with the correct S3 key
                        user_file.s3_key = key
                        user_file.save(update_fields=['s3_key'])
                    return key
        
        raise Exception(f"S3 object not found with any key variation for file {user_file.id}")

    def process_file(self, user_file):
        """Main entry point for OCR processing with S3 debugging"""
        print(f"[OCR Service] Starting OCR for file: {user_file.id}")
        print(f"[OCR Service] File details:")
        print(f"  - Original filename: {user_file.original_filename}")
        print(f"  - File field: {user_file.file.name}")
        print(f"  - S3 key: {user_file.s3_key}")
        print(f"  - File type: {user_file.file_type}")
        
        try:
            # Check OCR preferences
            ocr_pref, _ = OCRPreference.objects.get_or_create(user=user_file.user)
            if ocr_pref.preference == 'none':
                print(f"[OCR Service] OCR disabled for user {user_file.user.id}")
                self._clear_pending_flag(user_file)
                return {'status': 'skipped', 'reason': 'OCR disabled by user'}

            # Verify and normalize S3 key
            try:
                s3_key = self._normalize_s3_key(user_file)
                print(f"[OCR Service] Using S3 key: {s3_key}")
            except Exception as s3_error:
                print(f"[OCR Service] S3 key error: {str(s3_error)}")
                self._handle_error(user_file, f"S3 access error: {str(s3_error)}")
                return {'status': 'error', 'error': str(s3_error)}

            # Create OCR result record
            ocr_result, created = OCRResult.objects.get_or_create(
                file=user_file,
                defaults={'status': 'pending'}
            )
            print(f"[OCR Service] OCR result {'created' if created else 'found'}: {ocr_result.id}")

            # Get file extension
            file_extension = self._get_file_extension(user_file)
            print(f"[OCR Service] Processing file type: {file_extension}")
            
            # Process based on file type
            if file_extension in ['txt', 'docx', 'md']:
                return self._process_text_file(user_file, ocr_result, file_extension)
            elif file_extension in ['jpg', 'jpeg', 'png']:
                return self._process_image_file(user_file, ocr_result)
            elif file_extension == 'pdf':
                return self._process_pdf_file(user_file, ocr_result)
            else:
                print(f"[OCR Service] Unsupported file type: {file_extension}")
                self._mark_as_not_applicable(user_file, ocr_result)
                return {'status': 'not_applicable', 'reason': 'Unsupported file type'}

        except Exception as e:
            print(f"[OCR Service] Error processing file {user_file.id}: {str(e)}")
            import traceback
            traceback.print_exc()
            self._handle_error(user_file, str(e))
            return {'status': 'error', 'error': str(e)}

    def _process_text_file(self, user_file, ocr_result, file_extension):
        """Process text-based files (txt, docx, md)"""
        try:
            print(f"[OCR Service] Processing text file: {file_extension}")
            text_content = extract_text_from_document(user_file.s3_key, file_extension)
            print(f"[OCR Service] Extracted text length: {len(text_content) if text_content else 0}")
            
            if text_content:
                # Update OCR result
                ocr_result.text_content = text_content
                ocr_result.status = 'completed'
                ocr_result.save()
                print(f"[OCR Service] OCR result updated to completed")
                
                # Categorize and update file
                category_result = self._categorize_file(user_file, text_content)
                print(f"[OCR Service] Categorization result: {category_result}")
                
                return {
                    'status': 'completed',
                    'text_length': len(text_content),
                    'category': user_file.category.name if user_file.category else 'Miscellaneous',
                    'category_changed': category_result.get('changed', False)
                }
            else:
                raise Exception("No text content extracted")
                
        except Exception as e:
            print(f"[OCR Service] Error processing text file: {str(e)}")
            import traceback
            traceback.print_exc()
            self._handle_error(user_file, str(e))
            return {'status': 'error', 'error': str(e)}

    def _process_image_file(self, user_file, ocr_result):
        """Process image files using Textract"""
        try:
            print(f"[OCR Service] Processing image file with Textract")
            
            response = self.textract_client.detect_document_text(
                Document={
                    'S3Object': {
                        'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                        'Name': user_file.s3_key
                    }
                }
            )
            
            # Extract text lines
            extracted_lines = [
                item['Text'] for item in response['Blocks'] 
                if item['BlockType'] == 'LINE'
            ]
            text_content = '\n'.join(extracted_lines)
            print(f"[OCR Service] Extracted text length: {len(text_content)}")
            
            # Update OCR result
            ocr_result.text_content = text_content
            ocr_result.status = 'completed'
            ocr_result.save()
            
            # Categorize and update file
            category_result = self._categorize_file(user_file, text_content)
            print(f"[OCR Service] Categorization result: {category_result}")
            
            return {
                'status': 'completed',
                'text_length': len(text_content),
                'category': user_file.category.name if user_file.category else 'Miscellaneous',
                'category_changed': category_result.get('changed', False)
            }
            
        except Exception as e:
            print(f"[OCR Service] Error processing image file: {str(e)}")
            import traceback
            traceback.print_exc()
            self._handle_error(user_file, str(e))
            return {'status': 'error', 'error': str(e)}

    def _process_pdf_file(self, user_file, ocr_result):
        """Process PDF files using async Textract"""
        try:
            print(f"[OCR Service] Starting async PDF processing")
            
            # Check if job already exists
            if ocr_result.job_id and ocr_result.status == 'processing':
                job_status = self._check_textract_job(ocr_result.job_id)
                if job_status == 'SUCCEEDED':
                    return self._complete_pdf_processing(user_file, ocr_result)
                elif job_status == 'FAILED':
                    raise Exception("Previous Textract job failed")
                else:
                    return {'status': 'processing', 'job_id': ocr_result.job_id}
            
            # Start new Textract job
            response = self.textract_client.start_document_analysis(
                DocumentLocation={
                    'S3Object': {
                        'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                        'Name': user_file.s3_key
                    }
                },
                FeatureTypes=['TABLES', 'FORMS']
            )
            
            job_id = response['JobId']
            
            # Update OCR result
            ocr_result.job_id = job_id
            ocr_result.status = 'processing'
            ocr_result.save()
            
            print(f"[OCR Service] Started Textract job: {job_id}")
            
            # Try to wait and complete immediately (for smaller PDFs)
            return self._wait_for_pdf_completion(user_file, ocr_result, max_wait=30)
            
        except Exception as e:
            print(f"[OCR Service] Error processing PDF file: {str(e)}")
            import traceback
            traceback.print_exc()
            self._handle_error(user_file, str(e))
            return {'status': 'error', 'error': str(e)}

    def _wait_for_pdf_completion(self, user_file, ocr_result, max_wait=30):
        """Wait for PDF processing to complete (up to max_wait seconds)"""
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                job_status = self._check_textract_job(ocr_result.job_id)
                print(f"[OCR Service] Job {ocr_result.job_id} status: {job_status}")
                
                if job_status == 'SUCCEEDED':
                    return self._complete_pdf_processing(user_file, ocr_result)
                elif job_status == 'FAILED':
                    raise Exception("Textract job failed")
                
                # Wait before checking again
                time.sleep(2)
                
            except Exception as e:
                print(f"[OCR Service] Error checking job status: {str(e)}")
                break
        
        # If we reach here, job is still processing
        return {'status': 'processing', 'job_id': ocr_result.job_id}

    def _check_textract_job(self, job_id):
        """Check status of Textract job"""
        try:
            response = self.textract_client.get_document_analysis(JobId=job_id)
            return response['JobStatus']
        except Exception as e:
            print(f"[OCR Service] Error checking job {job_id}: {str(e)}")
            return 'FAILED'

    def _complete_pdf_processing(self, user_file, ocr_result):
        """Complete PDF processing when Textract job succeeds"""
        try:
            print(f"[OCR Service] Completing PDF processing for job: {ocr_result.job_id}")
            response = self.textract_client.get_document_analysis(JobId=ocr_result.job_id)
            
            # Extract text from all pages
            text_content = ""
            blocks = response.get('Blocks', [])
            
            # Handle pagination
            page_count = 1
            while True:
                lines = [block['Text'] for block in blocks if block['BlockType'] == 'LINE']
                text_content += '\n'.join(lines) + '\n'
                print(f"[OCR Service] Processed page {page_count}, lines: {len(lines)}")
                
                # Check for more pages
                next_token = response.get('NextToken')
                if not next_token:
                    break
                    
                response = self.textract_client.get_document_analysis(
                    JobId=ocr_result.job_id,
                    NextToken=next_token
                )
                blocks = response.get('Blocks', [])
                page_count += 1
            
            text_content = text_content.strip()
            print(f"[OCR Service] Total text extracted: {len(text_content)} characters from {page_count} pages")
            
            # Update OCR result
            ocr_result.text_content = text_content
            ocr_result.status = 'completed'
            ocr_result.save()
            
            # Categorize and update file
            category_result = self._categorize_file(user_file, text_content)
            print(f"[OCR Service] Final categorization result: {category_result}")
            
            return {
                'status': 'completed',
                'text_length': len(text_content),
                'category': user_file.category.name if user_file.category else 'Miscellaneous',
                'category_changed': category_result.get('changed', False)
            }
            
        except Exception as e:
            print(f"[OCR Service] Error completing PDF processing: {str(e)}")
            import traceback
            traceback.print_exc()
            self._handle_error(user_file, str(e))
            return {'status': 'error', 'error': str(e)}

    def _categorize_file(self, user_file, text_content):
        """ENHANCED categorization with detailed logging"""
        try:
            original_category = user_file.category.name if user_file.category else 'None'
            print(f"\n[CATEGORIZATION] ===== Starting categorization =====")
            print(f"[CATEGORIZATION] File: {user_file.original_filename}")
            print(f"[CATEGORIZATION] Original category: {original_category}")
            print(f"[CATEGORIZATION] Pending auto-categorization: {user_file.pending_auto_categorization}")
            print(f"[CATEGORIZATION] Text content length: {len(text_content)}")
            
            # Show first 300 chars of text for debugging
            if text_content:
                preview_text = text_content[:300].replace('\n', ' ').strip()
                print(f"[CATEGORIZATION] Text preview: {preview_text}...")
            
            # ALWAYS attempt categorization if text exists and file is in Miscellaneous or has pending flag
            should_categorize = (
                text_content and 
                len(text_content.strip()) > 10 and  # Ensure meaningful text
                (
                    user_file.pending_auto_categorization or 
                    (user_file.category and user_file.category.name == 'Miscellaneous')
                )
            )
            
            print(f"[CATEGORIZATION] Should categorize: {should_categorize}")
            
            category_changed = False
            analysis = None
            
            if should_categorize:
                print(f"[CATEGORIZATION] Analyzing text for categorization...")
                analysis = self.categorization_service.analyze_file_content(text_content)
                
                print(f"[CATEGORIZATION] Analysis result:")
                print(f"  - Suggested category: {analysis['category']}")
                print(f"  - Confidence: {analysis['confidence']:.2f}%")
                print(f"  - Total matches found: {len(analysis.get('matches', {}))}")
                
                # Show detailed match breakdown
                if analysis.get('matches'):
                    print(f"[CATEGORIZATION] Match breakdown:")
                    for category, matches in analysis['matches'].items():
                        total_score = sum(match['count'] for match in matches)
                        exact_matches = sum(1 for match in matches if match['exact_match'])
                        print(f"    {category}: {total_score} total, {exact_matches} exact matches")
                        
                        # Show top keywords for debugging
                        top_matches = sorted(matches, key=lambda x: x['count'], reverse=True)[:3]
                        keywords = [f"{m['keyword']}({m['count']})" for m in top_matches]
                        print(f"      Top keywords: {', '.join(keywords)}")
                
                # Use lower confidence threshold (25% instead of 40%)
                confidence_threshold = 25
                print(f"[CATEGORIZATION] Confidence threshold: {confidence_threshold}%")
                
                if analysis['confidence'] >= confidence_threshold:
                    suggested_category_name = analysis['category']
                    
                    # Don't change if it's the same category
                    if suggested_category_name != original_category:
                        category, created = FileCategory.objects.get_or_create(
                            name=suggested_category_name,
                            defaults={'is_default': True}
                        )
                        
                        print(f"[CATEGORIZATION] ✓ CHANGING category from '{original_category}' to '{suggested_category_name}'")
                        user_file.category = category
                        category_changed = True
                        
                        # Send notification email (optional)
                        try:
                            from django.core.mail import send_mail
                            send_mail(
                                'File Auto-Categorized',
                                f'Your file "{user_file.original_filename}" has been automatically categorized as "{suggested_category_name}" based on its content.',
                                settings.DEFAULT_FROM_EMAIL,
                                [user_file.user.email],
                                fail_silently=True,
                            )
                            print(f"[CATEGORIZATION] ✓ Notification email sent")
                        except Exception as email_error:
                            print(f"[CATEGORIZATION] Email notification failed: {str(email_error)}")
                            
                    else:
                        print(f"[CATEGORIZATION] = Suggested category same as original, no change needed")
                        category_changed = False
                else:
                    print(f"[CATEGORIZATION] ✗ Confidence too low ({analysis['confidence']:.2f}%), keeping original category")
                    category_changed = False
            else:
                print(f"[CATEGORIZATION] - Auto-categorization skipped")
                if not text_content:
                    print(f"[CATEGORIZATION]   Reason: No text content")
                elif len(text_content.strip()) <= 10:
                    print(f"[CATEGORIZATION]   Reason: Text too short")
                elif not user_file.pending_auto_categorization and user_file.category.name != 'Miscellaneous':
                    print(f"[CATEGORIZATION]   Reason: User-selected category")
            
            # Always clear pending flag and save
            user_file.pending_auto_categorization = False
            user_file.save()
            print(f"[CATEGORIZATION] File saved with final category: {user_file.category.name}")
            print(f"[CATEGORIZATION] ===== Categorization complete =====\n")
            
            return {
                'changed': category_changed,
                'final_category': user_file.category.name if user_file.category else 'Miscellaneous',
                'analysis': analysis,
                'confidence': analysis['confidence'] if analysis else 0
            }
            
        except Exception as e:
            print(f"[CATEGORIZATION] ✗ Error categorizing file: {str(e)}")
            import traceback
            traceback.print_exc()
            self._clear_pending_flag(user_file)
            return {'changed': False, 'error': str(e)}

    def _handle_error(self, user_file, error_message):
        """Handle OCR processing errors"""
        try:
            print(f"[OCR Service] Handling error for file {user_file.id}: {error_message}")
            
            # Update or create OCR result
            ocr_result, created = OCRResult.objects.get_or_create(
                file=user_file,
                defaults={'status': 'failed', 'text_content': f'Error: {error_message}'}
            )
            if not created:
                ocr_result.status = 'failed'
                ocr_result.text_content = f'Error: {error_message}'
                ocr_result.save()
            
            # Clear pending flag and ensure file has category
            self._clear_pending_flag(user_file)
            
        except Exception as e:
            print(f"[OCR Service] Error handling error: {str(e)}")

    def _mark_as_not_applicable(self, user_file, ocr_result):
        """Mark file as not applicable for OCR"""
        ocr_result.status = 'not_applicable'
        ocr_result.text_content = 'OCR not applicable for this file type'
        ocr_result.save()
        self._clear_pending_flag(user_file)

    def _clear_pending_flag(self, user_file):
        """Clear pending flag and ensure file has category"""
        try:
            if not user_file.category:
                misc_category, _ = FileCategory.objects.get_or_create(
                    name='Miscellaneous',
                    defaults={'is_default': True}
                )
                user_file.category = misc_category
            
            user_file.pending_auto_categorization = False
            user_file.save()
            print(f"[OCR Service] Cleared pending flag for file {user_file.id}")
            
        except Exception as e:
            print(f"[OCR Service] Error clearing pending flag: {str(e)}")

    def _get_file_extension(self, user_file):
        """Get file extension from original filename"""
        if user_file.original_filename:
            return user_file.original_filename.split('.')[-1].lower()
        elif user_file.file.name:
            return user_file.file.name.split('.')[-1].lower()
        return ''

    def check_pending_jobs(self):
        """Check and complete pending PDF jobs"""
        print(f"[OCR Service] Checking pending jobs...")
        pending_jobs = OCRResult.objects.filter(
            status='processing',
            job_id__isnull=False
        ).select_related('file')
        
        print(f"[OCR Service] Found {pending_jobs.count()} pending jobs")
        
        for ocr_result in pending_jobs:
            try:
                job_status = self._check_textract_job(ocr_result.job_id)
                
                if job_status == 'SUCCEEDED':
                    result = self._complete_pdf_processing(ocr_result.file, ocr_result)
                    print(f"[OCR Service] Completed pending job: {ocr_result.job_id} - {result}")
                elif job_status == 'FAILED':
                    self._handle_error(ocr_result.file, "Textract job failed")
                    print(f"[OCR Service] Failed pending job: {ocr_result.job_id}")
                else:
                    print(f"[OCR Service] Job {ocr_result.job_id} still {job_status}")
                    
            except Exception as e:
                print(f"[OCR Service] Error checking pending job {ocr_result.job_id}: {str(e)}")
