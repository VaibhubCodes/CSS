from django.shortcuts import render
from django.http import JsonResponse
from .models import UserFile,OCRResult,FileCategory,CardDetails,ExpiryDetails
from .serializers import UserFileSerializer, FileCategorySerializer, OCRResultSerializer,FileUploadSerializer, FileSearchSerializer, AppSubscription, CardDetailsSerializer, AppSubscriptionSerializer, FilePasswordSerializer
from rest_framework.decorators import api_view, permission_classes
from .forms import FileUploadForm
import os, boto3, time, re
from django.core.files.storage import default_storage
from django.conf import settings
from voice_retrieval import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.views.decorators.http import require_http_methods
from rest_framework.response import Response
from django.db.models import Q
from .services import ExpiryManagementService
from datetime import date
from storage_management.utils import S3StorageManager
from django.db import transaction, models
from django.core.exceptions import ValidationError

textract_client = boto3.client(
    'textract',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_S3_REGION_NAME
)


# def file_upload_view(request):
#     if request.method == 'POST':
#         form = FileUploadForm(request.POST, request.FILES)
#         if form.is_valid():
#             user_file = form.save()
#             return JsonResponse({
#                 "message": "File uploaded successfully",
#                 "file_url": user_file.file.url
#             })
#     else:
#         form = FileUploadForm()
#     return render(request, 'file_management/upload.html', {'form': form})

# @login_required
# def file_upload_view(request):
#     if request.method == 'POST':
#         form = FileUploadForm(request.POST, request.FILES)
#         if form.is_valid():
#             try:
#                 file_obj = request.FILES['file']
#                 storage_manager = S3StorageManager(request.user)
                
#                 # Check storage limit
#                 if not storage_manager.check_storage_limit(file_obj.size):
#                     return JsonResponse({
#                         'error': 'Storage limit would be exceeded'
#                     }, status=400)
                
#                 # Create file in memory
#                 file_content = file_obj.read()
#                 in_memory_file = io.BytesIO(file_content)
#                 in_memory_file.name = file_obj.name
                
#                 # Upload file to S3
#                 file_key = storage_manager.upload_file(
#                     in_memory_file,
#                     file_obj.name
#                 )
                
#                 # Create UserFile record
#                 user_file = form.save(commit=False)
#                 user_file.user = request.user
#                 user_file.file.name = file_key
#                 user_file.save()
                
#                 # Get updated storage info
#                 storage_info = storage_manager.get_user_storage_info()
                
#                 return JsonResponse({
#                     'message': 'File uploaded successfully',
#                     'file_url': user_file.file.url,
#                     'storage_info': storage_info
#                 })
                
#             except Exception as e:
#                 return JsonResponse({
#                     'error': str(e)
#                 }, status=500)
#     else:
#         form = FileUploadForm()
    
#     return render(request, 'file_management/upload.html', {'form': form})

# def file_list_view(request):
#     # Get all user files
#     files = UserFile.objects.filter(user=request.user)
    
#     # Initialize expiry service
#     expiry_service = ExpiryManagementService()
#     today = date.today()

#     # Get regular category counts
#     category_counts = {}
#     for category in FileCategory.objects.all():
#         if category.name == 'EXPIRED_DOCS':
#             # Count all expired items
#             expired_count = ExpiryDetails.objects.filter(
#                 Q(document__user=request.user) |
#                 Q(card__user=request.user) |
#                 Q(subscription__user=request.user)
#             ).count()
#             category_counts[category.name] = expired_count
#         else:
#             # Count active files in each category
#             count = files.filter(category=category).count()
#             category_counts[category.name] = count

#     # Prepare regular categories
#     categories = [
#         {
#             'name': category.name,
#             'count': category_counts.get(category.name, 0),
#             'type': 'expired' if category.name == 'EXPIRED_DOCS' else 'regular'
#         } for category in FileCategory.objects.all()
#     ]

#     # Get cards with expiry status
#     cards = CardDetails.objects.filter(user=request.user)
#     active_cards = cards.filter(
#         Q(expiry_year__gt=today.year) |
#         (Q(expiry_year=today.year) & Q(expiry_month__gte=today.month))
#     )

#     # Get subscriptions with expiry status
#     subscriptions = AppSubscription.objects.filter(user=request.user)
#     active_subscriptions = subscriptions.filter(
#         Q(end_date__gte=today) |
#         Q(auto_renewal=True)
#     )

#     # Add special categories
#     special_categories = [
#         {
#             'name': 'Cards',
#             'type': 'special',
#             'count': active_cards.count(),
#             'total_count': cards.count(),
#             'expired_count': cards.count() - active_cards.count()
#         },
#         {
#             'name': 'Subscriptions',
#             'type': 'special',
#             'count': active_subscriptions.count(),
#             'total_count': subscriptions.count(),
#             'expired_count': subscriptions.count() - active_subscriptions.count()
#         }
#     ]

#     # Get all expired items for preview
#     expired_items = {
#         'documents': files.filter(category__name='EXPIRED_DOCS'),
#         'cards': cards.exclude(
#             Q(expiry_year__gt=today.year) |
#             (Q(expiry_year=today.year) & Q(expiry_month__gte=today.month))
#         ),
#         'subscriptions': subscriptions.filter(
#             end_date__lt=today,
#             auto_renewal=False
#         )
#     }

#     # Return template with all context
#     return render(request, 'file_management/file_list.html', {
#         'files': files,
#         'categories': categories + special_categories,
#         'expired_items': expired_items,
#         'active_cards': active_cards,
#         'active_subscriptions': active_subscriptions,
#         'cards': cards,
#         'subscriptions': subscriptions,
#         'today': today,
#         'expired_category_exists': FileCategory.objects.filter(name='EXPIRED_DOCS').exists()
#     })
    
@login_required
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def delete_file(request, file_id):
    try:
        user_file = get_object_or_404(UserFile, id=file_id, user=request.user)
        
        try:
            # Use S3StorageManager to delete the file
            storage_manager = S3StorageManager(request.user)
            
            # Extract the filename from the s3_key or file.name
            file_key = user_file.s3_key
            if not file_key and user_file.file:
                file_key = user_file.file.name
                
            # If we have a full path, extract just the filename
            if file_key and '/' in file_key:
                file_name = file_key.split('/')[-1]
            else:
                file_name = file_key
                
            if file_name:
                try:
                    # Delete from S3 using the storage manager
                    storage_manager.delete_file(file_name)
                except Exception as s3_error:
                    print(f"S3 deletion error: {str(s3_error)}")
                    # Continue with database deletion even if S3 deletion fails
            
            # Delete the database record
            user_file.delete()
            
            return JsonResponse({
                'status': 'success',
                'message': 'File deleted successfully'
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error deleting file: {str(e)}'
            }, status=500)
            
    except UserFile.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'File not found'
        }, status=404)


def cleanup_local_files():
    local_folder = os.path.join(settings.MEDIA_ROOT, 'uploads/')
    if os.path.exists(local_folder):
        for file_name in os.listdir(local_folder):
            file_path = os.path.join(local_folder, file_name)
            default_storage.delete(file_path)  # deletes from local storage


# Initialize Boto3 client for Transcribe
transcribe_client = boto3.client(
    'transcribe',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_S3_REGION_NAME
)

'''
The feature to download the transcription would be handled at the frontend 
<script>
    async function startTranscription(fileName) {
        const response = await fetch(`/file_management/start_transcription/${fileName}/`);
        const data = await response.json();
        
        if (data.job_name) {
            checkTranscriptionStatus(data.job_name);
        } else {
            alert("Error starting transcription");
        }
    }

    async function checkTranscriptionStatus(jobName) {
        // Poll the server every 2 seconds to check the job status
        setTimeout(async () => {
            const statusResponse = await fetch(`/file_management/get_transcription_result/${jobName}/`);
            const statusData = await statusResponse.json();

            if (statusData.status === "completed") {
                window.location.href = statusData.transcript_url;  // Redirect to download the file
            } else if (statusData.status === "failed") {
                alert("Transcription job failed.");
            } else {
                checkTranscriptionStatus(jobName);  // Check again after 2 seconds
            }
        }, 2000);
    }
</script>

'''


def start_transcription(request, file_name):
    file_url = f"s3://{settings.AWS_STORAGE_BUCKET_NAME}/uploads/{file_name}"
    job_name = f"transcription-job-{int(time.time())}"


    try:
        # Start the transcription job
        response = transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': file_url},
            MediaFormat='mp3',  #to match your audio format
            LanguageCode='en-US',  #using a different language
            OutputBucketName=settings.AWS_STORAGE_BUCKET_NAME,
            OutputKey=f"transcriptions/{job_name}.json"
        )

        return JsonResponse({"message": "Transcription job started", "job_name": job_name})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def get_transcription_result(request, job_name):
    try:
        # Get the job status
        response = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
        status = response['TranscriptionJob']['TranscriptionJobStatus']

        if status == 'COMPLETED':
            transcript_url = response['TranscriptionJob']['Transcript']['TranscriptFileUri']
            return JsonResponse({"status": "completed", "transcript_url": transcript_url})
        elif status == 'FAILED':
            return JsonResponse({"status": "failed", "message": response['TranscriptionJob']['FailureReason']})

        return JsonResponse({"status": status})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


comprehend_client = boto3.client(
    'comprehend',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_S3_REGION_NAME
)

def text_analysis(request, job_name):
    try:
        # Retrieve the transcription result
        transcription_response = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
        if transcription_response['TranscriptionJob']['TranscriptionJobStatus'] != 'COMPLETED':
            return JsonResponse({"error": "Transcription job not completed yet."}, status=400)

        transcript_url = transcription_response['TranscriptionJob']['Transcript']['TranscriptFileUri']

        # Download and read the transcript file
        import requests
        transcript_data = requests.get(transcript_url).json()
        text = transcript_data['results']['transcripts'][0]['transcript']

        # Analyze text with Amazon Comprehend
        response = comprehend_client.detect_entities(Text=text, LanguageCode='en')
        entities = response.get('Entities', [])
        
        key_phrases_response = comprehend_client.detect_key_phrases(Text=text, LanguageCode='en')
        key_phrases = key_phrases_response.get('KeyPhrases', [])

        return JsonResponse({
            "transcript": text,
            "entities": entities,
            "key_phrases": key_phrases
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    

# from opensearchpy import OpenSearch

# Connect to OpenSearch
# opensearch_client = OpenSearch(
#     hosts=[{'host': settings.OPENSEARCH_HOST, 'port': settings.OPENSEARCH_PORT}],
#     http_auth=(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY),
#     use_ssl=True,
#     verify_certs=True
# )


# def index_document(doc_id, content, index_name='documents'):
#     # Define the document to index
#     document = {
#         "content": content
#     }
#     # Index the document
#     response = opensearch_client.index(index=index_name, id=doc_id, body=document)
#     return response


# def index_existing_document(request, doc_id):
#     # For demonstration, here is placeholder text as content
#     content = "This is the content of the document with ID " + doc_id
#     response = index_document(doc_id=doc_id, content=content)
#     return JsonResponse(response)


# def search_documents(request, job_name):
#     try:
#         # Call the text analysis endpoint to get entities and key phrases
#         response = text_analysis(request, job_name)
#         if 'error' in response:
#             return JsonResponse(response, status=500)

#         # Construct the search query
#         query_terms = [phrase['Text'] for phrase in response['key_phrases']]
#         search_query = {
#             "query": {
#                 "multi_match": {
#                     "query": " ".join(query_terms),
#                     "fields": ["content"]
#                 }
#             }
#         }

#         # Perform the search
#         search_response = opensearch_client.search(index='documents', body=search_query)
#         hits = search_response['hits']['hits']

#         return JsonResponse({
#             "status": "success",
#             "results": hits
#         })

#     except Exception as e:
#         return JsonResponse({"error": str(e)}, status=500)

import pandas as pd
import io
from .utils import extract_text_from_document
from .utils import FileCategorizationService


# def process_document_ocr(request, file_id):
#     try:
#         user_file = get_object_or_404(UserFile, id=file_id)
#         file_name = user_file.file.name
#         file_extension = file_name.split('.')[-1].lower()
        
#         # Set default category as Personal
#         default_category, _ = FileCategory.objects.get_or_create(
#             name='Personal',
#             defaults={'is_default': True}
#         )
#         user_file.category = default_category
#         user_file.save()

#         def categorize_file(text_content):
#             """Helper function to categorize the file based on extracted text."""
#             categorization_service = FileCategorizationService()
#             analysis = categorization_service.analyze_file_content(text_content)
            
#             if analysis['confidence'] >= 40:
#                 category, _ = FileCategory.objects.get_or_create(
#                     name=analysis['category'],
#                     defaults={'is_default': True}
#                 )
#                 user_file.category = category
#                 user_file.save()
#                 return category.name, analysis
#             return 'Personal', analysis

#         # Handle text-based files (txt, docx, md)
#         if file_extension in ['txt', 'docx', 'md']:
#             try:
#                 file_content = extract_text_from_document(user_file.file, file_extension)
#                 if file_content:
#                     category_name, analysis = categorize_file(file_content)
#                     ocr_result, created = OCRResult.objects.update_or_create(
#                         file=user_file,
#                         defaults={
#                             'status': 'completed',
#                             'text_content': file_content
#                         }
#                     )
#                     return JsonResponse({
#                         'status': 'completed',
#                         'text': file_content.split('\n'),
#                         'category': category_name,
#                         'analysis': analysis
#                     })
#             except Exception as e:
#                 return JsonResponse({
#                     'error': f'Error processing file: {str(e)}',
#                     'category': 'Personal'
#                 }, status=500)

#         # Initialize AWS Textract client
#         textract_client = boto3.client(
#             'textract',
#             aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
#             aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
#             region_name=settings.AWS_S3_REGION_NAME
#         )

#         document_path = user_file.file.name

#         try:
#             # Handle images (jpg, jpeg, png)
#             if file_extension in ['jpg', 'jpeg', 'png']:
#                 response = textract_client.detect_document_text(
#                     Document={
#                         'S3Object': {
#                             'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
#                             'Name': document_path
#                         }
#                     }
#                 )
                
#                 extracted_text = [item['Text'] for item in response['Blocks'] if item['BlockType'] == 'LINE']
#                 text_content = '\n'.join(extracted_text)
                
#                 # Categorize content
#                 category_name, analysis = categorize_file(text_content)
                
#                 ocr_result, created = OCRResult.objects.update_or_create(
#                     file=user_file,
#                     defaults={
#                         'status': 'completed',
#                         'text_content': text_content
#                     }
#                 )
                
#                 return JsonResponse({
#                     'status': 'completed',
#                     'text': extracted_text,
#                     'category': category_name,
#                     'analysis': analysis
#                 })

#             # Handle PDFs
#             elif file_extension == 'pdf':
#                 response = textract_client.start_document_analysis(
#                     DocumentLocation={
#                         'S3Object': {
#                             'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
#                             'Name': document_path
#                         }
#                     },
#                     FeatureTypes=['TABLES', 'FORMS']
#                 )
                
#                 job_id = response['JobId']
                
#                 # Create or update OCR result
#                 ocr_result, created = OCRResult.objects.update_or_create(
#                     file=user_file,
#                     defaults={
#                         'status': 'processing',
#                         'job_id': job_id
#                     }
#                 )
                
#                 return JsonResponse({
#                     'status': 'processing',
#                     'job_id': job_id
#                 })
            
#             else:
#                 return JsonResponse({
#                     'error': 'Unsupported file type',
#                     'category': 'Personal'
#                 }, status=400)

#         except textract_client.exceptions.InvalidS3ObjectException:
#             return JsonResponse({
#                 'error': 'File not accessible in S3',
#                 'category': 'Personal'
#             }, status=400)
#         except textract_client.exceptions.UnsupportedDocumentException:
#             return JsonResponse({
#                 'error': 'Document format not supported',
#                 'category': 'Personal'
#             }, status=400)
#         except Exception as e:
#             return JsonResponse({
#                 'error': str(e),
#                 'category': 'Personal'
#             }, status=500)

#     except Exception as e:
#         return JsonResponse({
#             'error': str(e),
#             'category': 'Personal'
#         }, status=500)
    
def get_ocr_result(request, job_id):
    try:
        # Fetch the OCR result and associated file
        ocr_result = get_object_or_404(OCRResult, job_id=job_id)
        user_file = ocr_result.file

        # Get the original category name
        original_category = user_file.category
        original_category_name = original_category.name if original_category else 'Miscellaneous'
        
        # Check if this is a user-selected category (not Miscellaneous)
        is_user_selected = original_category_name != 'Miscellaneous'

        # Return the result if already completed
        if ocr_result.status == 'completed' and ocr_result.text_content:
            category_name = user_file.category.name if user_file.category else 'Miscellaneous'
            return JsonResponse({
                'status': 'completed',
                'text': ocr_result.text_content.split('\n'),
                'category': category_name,
                'file_id': user_file.id,
                'original_category': original_category_name
            })

        # Set up AWS Textract client
        textract_client = boto3.client(
            'textract',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )

        # Get OCR processing status and response
        try:
            response = textract_client.get_document_analysis(JobId=job_id)

            if response['JobStatus'] == 'SUCCEEDED':
                # Extract text from response
                extracted_text = [
                    block['Text'] for block in response['Blocks']
                    if block['BlockType'] == 'LINE'
                ]
                text_content = '\n'.join(extracted_text)

                # Update OCR result in the database
                ocr_result.text_content = text_content
                ocr_result.status = 'completed'
                ocr_result.save()

                # Categorize the content only if not user-selected
                categorization_service = FileCategorizationService()
                analysis = categorization_service.analyze_file_content(text_content)
                
                # Only change category if analysis is confident and it's not a user-selected category
                category_changed = False
                if analysis['confidence'] >= 40 and not is_user_selected:
                    category, _ = FileCategory.objects.get_or_create(
                        name=analysis['category'],
                        defaults={'is_default': True}
                    )
                    
                    # If category changed, update and notify user
                    if original_category and category.id != original_category.id:
                        user_file.category = category
                        user_file.save()
                        category_changed = True
                        
                        # Send notification to user
                        try:
                            from django.core.mail import send_mail
                            
                            send_mail(
                                'File Category Changed',
                                f'Your file "{user_file.original_filename}" has been moved from "{original_category_name}" to "{category.name}" category based on its content.',
                                settings.DEFAULT_FROM_EMAIL,
                                [user_file.user.email],
                                fail_silently=True,
                            )
                        except Exception as notification_error:
                            print(f"Failed to send notification: {str(notification_error)}")
                
                category_name = user_file.category.name if user_file.category else 'Miscellaneous'

                return JsonResponse({
                    'status': 'completed',
                    'text': extracted_text,
                    'category': category_name,
                    'category_changed': category_changed,
                    'original_category': original_category_name,
                    'file_id': user_file.id
                })

            elif response['JobStatus'] == 'FAILED':
                ocr_result.status = 'failed'
                ocr_result.save()
                return JsonResponse({
                    'status': 'failed',
                    'error': response.get('StatusMessage', 'OCR processing failed'),
                    'category': original_category_name
                }, status=400)

            # Return in-progress status
            return JsonResponse({
                'status': response['JobStatus'],
                'progress': response.get('Progress', 0),
                'category': original_category_name
            })

        except textract_client.exceptions.InvalidJobIdException:
            ocr_result.status = 'failed'
            ocr_result.save()
            return JsonResponse({
                'error': 'Invalid or expired job ID',
                'category': original_category_name
            }, status=400)

    except Exception as e:
        return JsonResponse({   
            'error': str(e),
            'category': 'Miscellaneous'
        }, status=500)
    
from storage_management.utils import S3StorageManager
from storage_management.models import UserStorage
from django.http import JsonResponse
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.decorators import method_decorator

def file_upload_view(request):
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                file_obj = request.FILES['file']
                storage_manager = S3StorageManager(request.user)
                
                # Check storage limit
                if not storage_manager.check_storage_limit(file_obj.size):
                    return JsonResponse({
                        'error': 'Storage limit would be exceeded'
                    }, status=400)
                
                # Create file in memory
                file_content = file_obj.read()
                in_memory_file = io.BytesIO(file_content)
                in_memory_file.name = file_obj.name
                
                # Upload file to S3
                file_key = storage_manager.upload_file(
                    in_memory_file,
                    file_obj.name
                )
                
                # Create UserFile record
                user_file = form.save(commit=False)
                user_file.user = request.user
                user_file.file.name = file_key
                user_file.save()
                
                # Get updated storage info
                storage_info = storage_manager.get_user_storage_info()
                
                return JsonResponse({
                    'message': 'File uploaded successfully',
                    'file_url': user_file.file.url,
                    'storage_info': storage_info
                })
                
            except Exception as e:
                return JsonResponse({
                    'error': str(e)
                }, status=500)
    else:
        form = FileUploadForm()
    
    return render(request, 'file_management/upload.html', {'form': form})

# Signal to update storage limit when subscription changes
@receiver(post_save, sender='payments.Subscription')
def update_storage_limit(sender, instance, created, **kwargs):
    if instance.status == 'active':
        storage, created = UserStorage.objects.get_or_create(user=instance.user)
        
        # Update storage limit based on plan
        if instance.plan == 'basic':
            storage.storage_limit = 5 * 1024 * 1024 * 1024  # 5GB
        elif instance.plan == 'premium':
            storage.storage_limit = 20 * 1024 * 1024 * 1024  # 20GB
        elif instance.plan == 'enterprise':
            storage.storage_limit = 50 * 1024 * 1024 * 1024  # 50GB
        
        storage.save()


# Custom category creation view
@login_required
def create_custom_category(request):
    if request.method == 'POST':
        category_name = request.POST.get('name')
        description = request.POST.get('description', '')
        
        try:
            category = FileCategory.objects.create(
                name=category_name,
                description=description,
                is_default=False,
                created_by=request.user
            )
            
            return JsonResponse({
                'status': 'success',
                'category': {
                    'id': category.id,
                    'name': category.name,
                    'description': category.description
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

class CardDetailsViewSet(viewsets.ModelViewSet):

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    serializer_class = CardDetailsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CardDetails.objects.filter(user=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    @action(detail=False, methods=['post'])
    def extract_from_document(self, request):
        file_id = request.data.get('file_id')
        if not file_id:
            return Response({'error': 'File ID is required'}, 
                        status=status.HTTP_400_BAD_REQUEST)

        try:
            user_file = UserFile.objects.get(id=file_id, user=request.user)
            ocr_result = OCRResult.objects.get(file=user_file)
            
            text_content = ocr_result.text_content
            
            # Card number pattern (16 digits, may be space/dash separated)
            card_pattern = r'\b(?:\d[ -]*?){13,16}\b'
            # Expiry date pattern (MM/YY or MM/YYYY)
            expiry_pattern = r'\b(0[1-9]|1[0-2])/([0-9]{2}|2[0-9]{3})\b'
            # Cardholder name pattern (usually in caps)
            name_pattern = r'\b[A-Z][A-Z\s]{2,}\b'

            # Find patterns in text
            card_numbers = re.findall(card_pattern, text_content)
            expiry_dates = re.findall(expiry_pattern, text_content)
            possible_names = re.findall(name_pattern, text_content)

            cards_found = []
            for card_number in card_numbers:
                # Clean the card number
                clean_number = ''.join(filter(str.isdigit, card_number))
                
                if len(clean_number) in [15, 16]:  # Valid card length
                    card = {
                        'card_number': clean_number,
                        'card_type': 'credit',  # Default to credit
                        'bank_name': 'Unknown Bank',  # Default bank name
                    }
                    
                    # Add expiry date if found
                    if expiry_dates:
                        month, year = expiry_dates[0]
                        card['expiry_month'] = month
                        card['expiry_year'] = '20' + year if len(year) == 2 else year
                    
                    # Add cardholder name if found
                    if possible_names:
                        card['card_holder'] = possible_names[0]
                    
                    cards_found.append(card)

            return Response({
                'cards_found': cards_found,
                'message': f'Found {len(cards_found)} potential card(s)'
            })

        except UserFile.DoesNotExist:
            return Response({'error': 'File not found'}, 
                        status=status.HTTP_404_NOT_FOUND)
        except OCRResult.DoesNotExist:
            return Response({'error': 'OCR result not found'}, 
                        status=status.HTTP_404_NOT_FOUND)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AppSubscriptionViewSet(viewsets.ModelViewSet):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    serializer_class = AppSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return AppSubscription.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'])
    def extract_from_document(self, request):
        file_id = request.data.get('file_id')
        if not file_id:
            return Response({'error': 'File ID is required'}, 
                        status=status.HTTP_400_BAD_REQUEST)

        try:
            user_file = UserFile.objects.get(id=file_id, user=request.user)
            ocr_result = OCRResult.objects.get(file=user_file)
            
            text_content = ocr_result.text_content.lower()
            
            # Common subscription services and their patterns
            services = {
                'netflix': {
                    'pattern': r'netflix.*?(\$|₹)(\d+\.?\d*)',
                    'types': ['Basic', 'Standard', 'Premium']
                },
                'amazon prime': {
                    'pattern': r'prime.*?(\$|₹)(\d+\.?\d*)',
                    'types': ['Monthly', 'Annual']
                },
                'spotify': {
                    'pattern': r'spotify.*?(\$|₹)(\d+\.?\d*)',
                    'types': ['Individual', 'Family', 'Student']
                },
                'disney+': {
                    'pattern': r'disney\+.*?(\$|₹)(\d+\.?\d*)',
                    'types': ['Monthly', 'Annual']
                }
            }

            subs_found = []
            for service, info in services.items():
                matches = re.findall(info['pattern'], text_content)
                if matches:
                    # Find dates in the text nearby
                    date_pattern = r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}'
                    dates = re.findall(date_pattern, text_content)
                    
                    for match in matches:
                        sub = {
                            'app_name': service.title(),
                            'amount': float(match[1]),
                            'subscription_type': 'Monthly',  # Default
                            'auto_renewal': True,
                            'status': 'active'
                        }
                        
                        # Add dates if found
                        if len(dates) >= 2:
                            from datetime import datetime
                            try:
                                sub['start_date'] = datetime.strptime(dates[0], '%d/%m/%Y').date()
                                sub['end_date'] = datetime.strptime(dates[1], '%d/%m/%Y').date()
                            except ValueError:
                                # Default dates if parsing fails
                                from datetime import date, timedelta
                                sub['start_date'] = date.today()
                                sub['end_date'] = date.today() + timedelta(days=30)
                        else:
                            # Default dates
                            from datetime import date, timedelta
                            sub['start_date'] = date.today()
                            sub['end_date'] = date.today() + timedelta(days=30)
                        
                        subs_found.append(sub)

            return Response({
                'subscriptions_found': subs_found,
                'message': f'Found {len(subs_found)} potential subscription(s)'
            })

        except UserFile.DoesNotExist:
            return Response({'error': 'File not found'}, 
                          status=status.HTTP_404_NOT_FOUND)
        except OCRResult.DoesNotExist:
            return Response({'error': 'OCR result not found'}, 
                          status=status.HTTP_404_NOT_FOUND)

    def destroy(self, request, *args, **kwargs):
        subscription = self.get_object()
        subscription.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# from django.http import HttpResponseForbidden
# @login_required
# def card_list_view(request):
#     if request.user.is_authenticated:
#         cards = CardDetails.objects.filter(user=request.user)
#         files = UserFile.objects.filter(user=request.user)
#         return render(request, 'file_management/cards/card_list.html', {
#             'cards': cards,
#             'files': files
#         })
#     else:
#         return HttpResponseForbidden("You are not authorized to view this page.")


# def subscription_list_view(request):
#     subscriptions = AppSubscription.objects.filter(user=request.user)
#     cards = CardDetails.objects.filter(user=request.user)
#     files = UserFile.objects.filter(user=request.user)
#     return render(request, 'file_management/subscriptions/subscription_list.html', {
#         'subscriptions': subscriptions,
#         'cards': cards,
#         'files': files
#     })

# def expired_items_view(request):
#     service = ExpiryManagementService()
#     expired_items = service.get_expired_items(request.user)
    
#     return render(request, 'file_management/expired_items.html', {
#         'expired_items': expired_items
#     })



class FileViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UserFileSerializer
    
    def get_queryset(self):
        return UserFile.objects.filter(user=self.request.user)

    def create(self, request):
        serializer = FileUploadSerializer(data=request.data)
        if serializer.is_valid():
            file_obj = serializer.validated_data['file']
            
            # Initialize storage manager
            storage_manager = S3StorageManager(request.user)
            
            # Check storage limit
            if not storage_manager.check_storage_limit(file_obj.size):
                return Response({
                    'error': 'Storage limit would be exceeded'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                # Upload file to S3
                s3_key = storage_manager.upload_file(file_obj, file_obj.name)
                
                # Create UserFile record
                user_file = UserFile.objects.create(
                    user=request.user,
                    file_type=serializer.validated_data['file_type'],
                    file=s3_key,
                    category_id=serializer.validated_data.get('category_id')
                )
                
                return Response(
                    UserFileSerializer(user_file).data,
                    status=status.HTTP_201_CREATED
                )
                
            except Exception as e:
                return Response({
                    'error': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def search(self, request):
        serializer = FileSearchSerializer(data=request.data)
        if serializer.is_valid():
            queryset = self.get_queryset()
            
            # Apply filters
            if query := serializer.validated_data.get('query'):
                queryset = queryset.filter(
                    Q(original_filename__icontains=query) |
                    Q(category__name__icontains=query)
                )
            
            if file_type := serializer.validated_data.get('file_type'):
                queryset = queryset.filter(file_type=file_type)
                
            if category := serializer.validated_data.get('category'):
                queryset = queryset.filter(category_id=category)
                
            if date_from := serializer.validated_data.get('date_from'):
                queryset = queryset.filter(upload_date__gte=date_from)
                
            if date_to := serializer.validated_data.get('date_to'):
                queryset = queryset.filter(upload_date__lte=date_to)
            
            return Response(
                UserFileSerializer(queryset, many=True).data
            )
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def ocr_status(self, request, pk=None):
        user_file = self.get_object()
        try:
            ocr_result = OCRResult.objects.get(file=user_file)
            return Response(OCRResultSerializer(ocr_result).data)
        except OCRResult.DoesNotExist:
            return Response({
                'status': 'not_started'
            })

    @action(detail=True, methods=['post'])
    def start_ocr(self, request, pk=None):
        user_file = self.get_object()
        # Reuse existing OCR processing logic
        response = process_document_ocr(request, user_file.id)
        return Response(response.json())

class CategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = FileCategorySerializer
    
    def get_queryset(self):
        # Return both default categories and user's custom categories
        return FileCategory.objects.filter(
            Q(is_default=True) | Q(created_by=self.request.user)
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['get'])
    def files(self, request, pk=None):
        category = self.get_object()
        files = UserFile.objects.filter(
            user=request.user,
            category=category
        )
        return Response(
            UserFileSerializer(files, many=True).data
        )

from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail

def process_document_ocr_async(request, file_id):
    """Process document OCR asynchronously"""
    try:
        # Create a new request object for the async task since the original may not be available
        print(f"[OCR Async] Starting OCR for file {file_id}")
        
        # Call OCR logic directly with user ID
        user_id = request.user.id
        result = process_document_ocr_logic(user_id, file_id)
        print(f"[OCR Async] OCR completed with result: {result}")
        return result
    except Exception as e:
        print(f"[OCR Async] Error in async OCR processing: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # On error, try to clear the pending flag directly
        try:
            file = UserFile.objects.get(id=file_id)
            if file.pending_auto_categorization:
                file.pending_auto_categorization = False
                # Ensure the file has a category
                if not file.category:
                    misc_category, _ = FileCategory.objects.get_or_create(
                        name='Miscellaneous',
                        defaults={'is_default': True}
                    )
                    file.category = misc_category
                file.save(update_fields=['pending_auto_categorization', 'category'])
                print(f"[OCR Async] Cleared pending flag for file {file_id} after error")
        except Exception as inner_e:
            print(f"[OCR Async] Failed to clear pending flag: {inner_e}")
        
        return {"status": "error", "error": str(e), "file_id": file_id}


# ============================================
# CENTRALIZED OCR & CATEGORIZATION LOGIC
# ============================================
def process_document_ocr_logic(user_id, file_id):
    """
    Handles OCR extraction, text analysis, categorization, and notifications.
    Designed to be run asynchronously after file upload or Textract completion.
    """
    text_content = None
    ocr_status = 'failed'
    ocr_result = None
    misc_category = None
    
    try:
        # Use user_id to fetch user if necessary, ensure file belongs to user
        user_file = UserFile.objects.select_related('category', 'user').get(id=file_id, user_id=user_id)
        user = user_file.user # Get user from the file object
        original_category = user_file.category
        original_category_name = original_category.name if original_category else "Miscellaneous" # Use Miscellaneous if None

        # Get or create Miscellaneous category for fallback
        misc_category, _ = FileCategory.objects.get_or_create(
            name='Miscellaneous',
            defaults={'is_default': True, 'description': 'Uncategorized files'}
        )

        file_name = user_file.file.name # This is the S3 key
        file_extension = user_file.original_filename.split('.')[-1].lower() if user_file.original_filename else ''

        print(f"[OCR Logic] Starting for file: {user_file.id}, original category: {original_category_name}, ext: {file_extension}")

        ocr_status = 'pending'
        job_id = None # For async Textract jobs

        # --- Step 1: Extract Text ---
        # Check if OCR result already exists and has content (e.g., from async job)
        existing_ocr = OCRResult.objects.filter(file=user_file).first()
        if existing_ocr and existing_ocr.status == 'completed' and existing_ocr.text_content:
            print(f"[OCR Logic] Using existing OCR text for file {user_file.id}")
            text_content = existing_ocr.text_content
            ocr_status = 'completed'
        elif file_extension in ['txt', 'docx', 'md']:
             print(f"[OCR Logic] Extracting text directly for file {user_file.id}")
             try:
                 # Assuming user_file.file is FieldFile pointing to S3
                 storage = default_storage # Or your specific S3 storage backend
                 with storage.open(user_file.file.name, 'rb') as file_obj:
                    text_content = extract_text_from_document(file_obj, file_extension)
                 ocr_status = 'completed' if text_content is not None else 'failed'
             except Exception as extraction_error:
                 print(f"[OCR Logic] Error extracting text directly: {extraction_error}")
                 ocr_status = 'failed'
                 text_content = f"Error during text extraction: {extraction_error}"
        elif file_extension in ['jpg', 'jpeg', 'png']:
            print(f"[OCR Logic] Processing image with Textract synchronously for file {user_file.id}")
            try:
                textract_client = boto3.client(
                    'textract',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_S3_REGION_NAME
                )
                response = textract_client.detect_document_text(
                    Document={'S3Object': {'Bucket': settings.AWS_STORAGE_BUCKET_NAME, 'Name': user_file.file.name}}
                )
                extracted_lines = [item['Text'] for item in response['Blocks'] if item['BlockType'] == 'LINE']
                text_content = '\n'.join(extracted_lines)
                ocr_status = 'completed'
            except Exception as textract_error:
                print(f"[OCR Logic] Textract sync error: {textract_error}")
                ocr_status = 'failed'
                text_content = f"Error during synchronous Textract processing: {textract_error}"
        elif file_extension == 'pdf':
            print(f"[OCR Logic] Starting async Textract job for PDF file {user_file.id}")
            try:
                textract_client = boto3.client(
                    'textract',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_S3_REGION_NAME
                )
                # Check if a job is already running for this file
                if existing_ocr and existing_ocr.status == 'processing' and existing_ocr.job_id:
                     print(f"[OCR Logic] Async job {existing_ocr.job_id} already in progress.")
                     # For admin panel, we want to wait and get results rather than return early
                     # Try to check the job status
                     try:
                         response = textract_client.get_document_analysis(JobId=existing_ocr.job_id)
                         job_status = response['JobStatus']
                         if job_status == 'SUCCEEDED':
                             print(f"[OCR Logic] Previous job {existing_ocr.job_id} succeeded, retrieving results")
                             blocks = response.get('Blocks', [])
                             extracted_lines = [block['Text'] for block in blocks if block.get('BlockType') == 'LINE']
                             if extracted_lines:
                                 text_content = '\n'.join(extracted_lines)
                                 ocr_status = 'completed'
                                 # Update the OCR result
                                 existing_ocr.status = 'completed'
                                 existing_ocr.text_content = text_content
                                 existing_ocr.save()
                         else:
                             print(f"[OCR Logic] Job {existing_ocr.job_id} status: {job_status}, not ready yet")
                             return {
                                 'status': 'processing',
                                 'job_id': existing_ocr.job_id,
                                 'message': f"Textract job is still {job_status.lower()}"
                             }
                     except Exception as job_check_error:
                         print(f"[OCR Logic] Error checking job {existing_ocr.job_id}: {job_check_error}")
                         # Continue with starting a new job
                
                # Start a new job if needed
                if ocr_status != 'completed':  # If previous steps didn't complete OCR
                    response = textract_client.start_document_analysis(
                        DocumentLocation={'S3Object': {'Bucket': settings.AWS_STORAGE_BUCKET_NAME, 'Name': user_file.file.name}},
                        FeatureTypes=['TABLES', 'FORMS'] # Adjust as needed
                    )
                    job_id = response['JobId']
                    ocr_status = 'processing'
                    # Save job_id immediately
                    ocr_result, _ = OCRResult.objects.update_or_create(
                        file=user_file,
                        defaults={'status': ocr_status, 'job_id': job_id, 'text_content': None}
                    )
                    print(f"[OCR Logic] Async job {job_id} started.")
                    
                    # For PDF files in admin, we need to inform that OCR is still in progress
                    # but we need to clear the pending flag to avoid endless attempts
                    if user_file.pending_auto_categorization:
                        print(f"[OCR Logic] Clearing pending flag for file {user_file.id} since PDF OCR is in progress")
                        user_file.pending_auto_categorization = False
                        user_file.save(update_fields=['pending_auto_categorization'])
                    
                    return {
                        'status': 'processing', 
                        'job_id': job_id,
                        'message': "PDF document OCR is processing in the background. Check the file details later."
                    }
            except Exception as textract_error:
                print(f"[OCR Logic] Textract async start error: {textract_error}")
                import traceback
                traceback.print_exc()
                ocr_status = 'failed'
                text_content = f"Error starting asynchronous Textract job: {textract_error}"
        else:
            print(f"[OCR Logic] File type '{file_extension}' not supported for OCR.")
            ocr_status = 'not_applicable' # Or 'unsupported'
            
            # Even for unsupported files, clear the pending flag
            if user_file.pending_auto_categorization:
                user_file.pending_auto_categorization = False
                user_file.save(update_fields=['pending_auto_categorization'])

        # --- Step 2: Update OCRResult Model ---
        ocr_defaults = {'status': ocr_status}
        if text_content is not None:
             ocr_defaults['text_content'] = text_content
        if job_id: # Should not happen here anymore for async, but safe check
             ocr_defaults['job_id'] = job_id

        ocr_result, created = OCRResult.objects.update_or_create(
            file=user_file,
            defaults=ocr_defaults
        )
        print(f"[OCR Logic] OCRResult updated/created for file {user_file.id} with status: {ocr_status}")

        # --- Step 3: Categorize if applicable ---
        category_changed = False
        final_category = original_category
        new_category_name = original_category_name # Initialize with original

        # Only attempt categorization if OCR completed and text was extracted
        if ocr_status == 'completed' and text_content:
            # Check if this file needs auto-categorization (either pending_auto_categorization is True OR it's in Miscellaneous)
            # Auto-categorize if pending flag is set OR if category is Miscellaneous
            should_auto_categorize = user_file.pending_auto_categorization or (original_category and original_category.id == misc_category.id)
            
            if should_auto_categorize:
                print(f"[OCR Logic] Attempting auto-categorization for file {user_file.id}")
                categorization_service = FileCategorizationService()
                analysis = categorization_service.analyze_file_content(text_content)
                print(f"[OCR Logic] Category analysis: {analysis['category']} with confidence {analysis['confidence']}%")

                if analysis['confidence'] >= 40: # Confidence threshold
                    suggested_category_name = analysis['category']
                    # Check if suggested category is different from the original one
                    if suggested_category_name != original_category_name:
                        new_category, _ = FileCategory.objects.get_or_create(
                            name=suggested_category_name,
                            defaults={'is_default': True} # Assuming auto-categories are default type
                        )
                        user_file.category = new_category
                        final_category = new_category
                        new_category_name = new_category.name
                        category_changed = True
                        
                        # Turn off the pending flag, now that we've categorized it
                        if user_file.pending_auto_categorization:
                            user_file.pending_auto_categorization = False
                        
                        # Save the category change
                        user_file.save(update_fields=['category', 'pending_auto_categorization'])
                        print(f"[OCR Logic] Category changed for file {user_file.id} from '{original_category_name}' to '{new_category_name}'")
                    else:
                        print(f"[OCR Logic] Suggested category '{suggested_category_name}' matches original '{original_category_name}'. No change.")
                        # Turn off the pending flag even if we didn't change the category
                        if user_file.pending_auto_categorization:
                            user_file.pending_auto_categorization = False
                            user_file.save(update_fields=['pending_auto_categorization'])
                else:
                    print(f"[OCR Logic] Analysis confidence too low ({analysis['confidence']}%). Keeping original category.")
                    # Turn off the pending flag even if confidence is too low
                    if user_file.pending_auto_categorization:
                        user_file.pending_auto_categorization = False
                        user_file.save(update_fields=['pending_auto_categorization'])
            else:
                print(f"[OCR Logic] Auto-categorization skipped for file {user_file.id} - user-selected category")
                # Make sure pending flag is cleared
                if user_file.pending_auto_categorization:
                    user_file.pending_auto_categorization = False
                    user_file.save(update_fields=['pending_auto_categorization'])
        else:
            # If OCR failed or had no text, clear the pending flag and keep in Miscellaneous
            if user_file.pending_auto_categorization:
                print(f"[OCR Logic] OCR status is '{ocr_status}' - clearing pending flag and keeping in Miscellaneous")
                user_file.pending_auto_categorization = False
                user_file.save(update_fields=['pending_auto_categorization'])

        # --- Return result information ---
        return {
            'status': ocr_status,
            'original_category': original_category_name,
            'final_category': new_category_name,
            'category_changed': category_changed,
            'ocr_id': ocr_result.id if ocr_result else None,
            'text_length': len(text_content) if text_content else 0
        }
        
    except Exception as e:
        print(f"[OCR Logic] Error processing file {file_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Attempt to clear the pending flag even if the main process fails
        try:
            if 'user_file' in locals() and user_file.pending_auto_categorization:
                # If we have a reference to the user_file, clear its pending flag
                user_file.pending_auto_categorization = False
                if misc_category:
                    user_file.category = misc_category
                user_file.save(update_fields=['pending_auto_categorization', 'category'])
                print(f"[OCR Logic] Cleared pending flag for file {file_id} after error")
            else:
                # If we don't have a user_file reference, try to get it directly
                try:
                    direct_user_file = UserFile.objects.get(id=file_id)
                    if direct_user_file.pending_auto_categorization:
                        direct_user_file.pending_auto_categorization = False
                        # Create Miscellaneous category if needed
                        misc_cat, _ = FileCategory.objects.get_or_create(
                            name='Miscellaneous',
                            defaults={'is_default': True}
                        )
                        direct_user_file.category = misc_cat
                        direct_user_file.save(update_fields=['pending_auto_categorization', 'category'])
                        print(f"[OCR Logic] Cleared pending flag for file {file_id} via direct DB query after error")
                except Exception as inner_e:
                    print(f"[OCR Logic] Could not clear pending flag via direct DB query: {inner_e}")
        except Exception as flag_e:
            print(f"[OCR Logic] Failed to clear pending flag: {flag_e}")
        
        return {
            'status': 'error',
            'error': str(e),
            'file_id': file_id
        }


#view functions to REST API views
@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def file_upload_view(request):
    """Fixed file upload with proper OCR triggering"""
    if request.method == 'POST':
        try:
            file_obj = request.FILES.get('file')
            file_type = request.data.get('file_type')
            
            if not file_obj or not file_type:
                return Response({
                    'success': False,
                    'error': 'File and file type are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            category_id = request.data.get('category_id') or request.data.get('category')
            
            # Initialize storage manager
            storage_manager = S3StorageManager(request.user)
            
            # Check storage limit
            if not storage_manager.check_storage_limit(file_obj.size):
                return Response({
                    'success': False,
                    'error': 'Storage limit would be exceeded'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Upload file to S3
            file_key = storage_manager.upload_file(file_obj, file_obj.name)
            
            # Determine category
            category = None
            should_auto_categorize = True
            
            if category_id:
                try:
                    category = FileCategory.objects.get(id=category_id)
                    should_auto_categorize = False
                except FileCategory.DoesNotExist:
                    pass
            
            if not category:
                misc_category, _ = FileCategory.objects.get_or_create(
                    name='Miscellaneous',
                    defaults={'is_default': True, 'description': 'Uncategorized files'}
                )
                category = misc_category
            
            # Create UserFile record
            user_file = UserFile.objects.create(
                user=request.user,
                file_type=file_type,
                file=file_key,
                s3_key=file_key,  # Ensure s3_key is set
                original_filename=file_obj.name,
                file_size=file_obj.size,
                category=category,
                pending_auto_categorization=should_auto_categorize
            )
            
            # Get updated storage info
            storage_info = storage_manager.get_user_storage_info()
            
            # Start OCR processing for document and image files
            ocr_result = {'status': 'not_applicable'}
            if file_type in ['document', 'image']:
                try:
                    from .services import OCRService
                    ocr_service = OCRService()
                    ocr_result = ocr_service.process_file(user_file)
                    print(f"[Upload] OCR result: {ocr_result}")
                except Exception as ocr_error:
                    print(f"[Upload] OCR error: {str(ocr_error)}")
                    ocr_result = {'status': 'error', 'error': str(ocr_error)}
            
            return Response({
                'success': True,
                'message': 'File uploaded successfully',
                'file': UserFileSerializer(user_file).data,
                'storage_info': storage_info,
                'ocr_result': ocr_result
            }, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # GET method for form data
    return Response({
        'file_types': dict(UserFile.FILE_TYPES),
        'categories': FileCategorySerializer(FileCategory.objects.all(), many=True).data
    })

@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def file_list_view(request):
    # Get query parameters for filtering
    category = request.query_params.get('category')
    file_type = request.query_params.get('file_type')
    search = request.query_params.get('search')
    show_hidden = request.query_params.get('show_hidden', 'false').lower() == 'true'
    favorites_only = request.query_params.get('favorites_only', 'false').lower() == 'true'
    
    # Filter files
    files = UserFile.objects.filter(user=request.user)
    
    # Apply hidden filter
    if not show_hidden:
        files = files.filter(is_hidden=False)

    # Apply favorites filter
    if favorites_only:
        files = files.filter(is_favorite=True)

    if category and category != 'all':
        files = files.filter(category__name=category)
    
    if file_type:
        files = files.filter(file_type=file_type)
    
    if search:
        files = files.filter(
            Q(original_filename__icontains=search) |
            Q(category__name__icontains=search)
        )
    
    # Get categories with counts for filters
    categories = []
    for category in FileCategory.objects.all():
        count = UserFile.objects.filter(user=request.user, category=category).count()
        categories.append({
            'id': category.id,
            'name': category.name,
            'count': count,
            'type': 'expired' if category.name == 'EXPIRED_DOCS' else 'regular'
        })
    # Added special counts
    favorite_count = UserFile.objects.filter(user=request.user, is_favorite=True).count()
    hidden_count = UserFile.objects.filter(user=request.user, is_hidden=True).count()
    locked_count = UserFile.objects.filter(user=request.user, locked=True).count()
    
    
    # Special categories counts (cards, subscriptions)
    today = date.today()
    cards = CardDetails.objects.filter(user=request.user)
    active_cards = cards.filter(
        Q(expiry_year__gt=today.year) |
        (Q(expiry_year=today.year) & Q(expiry_month__gte=today.month))
    )
    
    subscriptions = AppSubscription.objects.filter(user=request.user)
    active_subscriptions = subscriptions.filter(
        Q(end_date__gte=today) |
        Q(auto_renewal=True)
    )
    
    special_categories = [
        {
            'name': 'Cards',
            'type': 'special',
            'count': active_cards.count(),
            'total_count': cards.count(),
            'expired_count': cards.count() - active_cards.count()
        },
        {
            'name': 'Subscriptions',
            'type': 'special',
            'count': active_subscriptions.count(),
            'total_count': subscriptions.count(),
            'expired_count': subscriptions.count() - active_subscriptions.count()
        }
    ]
    
    # Get expired items
    expired_items = {
        'documents': UserFileSerializer(files.filter(category__name='EXPIRED_DOCS'), many=True).data,
        'cards': CardDetailsSerializer(cards.exclude(
            Q(expiry_year__gt=today.year) |
            (Q(expiry_year=today.year) & Q(expiry_month__gte=today.month))
        ), many=True).data,
        'subscriptions': AppSubscriptionSerializer(subscriptions.filter(
            end_date__lt=today,
            auto_renewal=False
        ), many=True).data
    }
    
    return Response({
        'files': UserFileSerializer(files, many=True).data,
        'categories': categories + special_categories,
        'expired_items': expired_items,
        'active_cards': CardDetailsSerializer(active_cards, many=True).data,
        'active_subscriptions': AppSubscriptionSerializer(active_subscriptions, many=True).data,
        'counts': {
            'favorites': favorite_count,
            'hidden': hidden_count,
            'locked': locked_count,
            'total': UserFile.objects.filter(user=request.user).count()
        },
    })

@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def card_list_view(request):
    cards = CardDetails.objects.filter(user=request.user)
    files = UserFile.objects.filter(user=request.user)
    
    return Response({
        'cards': CardDetailsSerializer(cards, many=True).data,
        'files': UserFileSerializer(files, many=True).data
    })

@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def subscription_list_view(request):
    subscriptions = AppSubscription.objects.filter(user=request.user)
    cards = CardDetails.objects.filter(user=request.user)
    files = UserFile.objects.filter(user=request.user)
    
    return Response({
        'subscriptions': AppSubscriptionSerializer(subscriptions, many=True).data,
        'cards': CardDetailsSerializer(cards, many=True).data,
        'files': UserFileSerializer(files, many=True).data
    })

@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def expired_items_view(request):
    service = ExpiryManagementService()
    expired_items = service.get_expired_items(request.user)
    
    # Organize expired items by type
    result = {
        'documents': [],
        'cards': [],
        'subscriptions': []
    }
    
    for item in expired_items:
        if item.document:
            result['documents'].append({
                'id': item.document.id,
                'name': item.document.original_filename,
                'category': item.original_category,
                'expiry_date': item.expiry_date
            })
        elif item.card:
            result['cards'].append({
                'id': item.card.id,
                'bank': item.card.bank_name,
                'card_number': f"**** {item.card.card_number[-4:]}",
                'expiry_date': item.expiry_date
            })
        elif item.subscription:
            result['subscriptions'].append({
                'id': item.subscription.id,
                'app_name': item.subscription.app_name,
                'subscription_type': item.subscription.subscription_type,
                'expiry_date': item.expiry_date
            })
    
    return Response(result)

@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def file_detail_view(request, file_id):
    try:
        file = get_object_or_404(UserFile, id=file_id, user=request.user)
        ocr_result = None
        
        try:
            if file.file_type == 'document':
                ocr_result = OCRResult.objects.get(file=file)
        except OCRResult.DoesNotExist:
            pass
        
        data = UserFileSerializer(file).data
        if ocr_result and ocr_result.text_content:
            data['ocr_text'] = ocr_result.text_content
            data['ocr_status'] = ocr_result.status
        
        return Response(data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

from voice_retrieval.utils import mobile_api_view
from .serializers import MobileFileUploadSerializer


from voice_retrieval.utils import mobile_api_view
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from .models import UserFile, FileCategory
from .serializers import UserFileSerializer

@mobile_api_view
@csrf_exempt
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def mobile_file_list(request):
    """
    Mobile-optimized file list endpoint.
    Supports filters: category, file_type, search, favorites_only, show_hidden.
    """
    # GET: list files
    if request.method == 'GET':
        category       = request.query_params.get('category')
        file_type      = request.query_params.get('file_type')
        search         = request.query_params.get('search')
        favorites_only = request.query_params.get('favorites_only')
        show_hidden    = request.query_params.get('show_hidden')

        # Base queryset: only files belonging to current user
        files = UserFile.objects.filter(user=request.user)

        # Filter hidden vs visible
        if show_hidden in ['true', '1']:
            files = files.filter(is_hidden=True)
        else:
            files = files.filter(is_hidden=False)

        # Favorites filter
        if favorites_only in ['true', '1']:
            files = files.filter(is_favorite=True)

        # Category filter
        if category and category.lower() != 'all':
            files = files.filter(category__name__iexact=category)

        # File-type filter
        if file_type:
            files = files.filter(file_type__iexact=file_type)

        # Search filter
        if search:
            files = files.filter(
                Q(original_filename__icontains=search) |
                Q(category__name__icontains=search)
            )

        # Build category counts for filter UI
        categories = []
        for cat in FileCategory.objects.all():
            count = UserFile.objects.filter(user=request.user, category=cat).count()
            categories.append({ 'id': cat.id, 'name': cat.name, 'count': count })

        # Serialize
        payload = {
            'files': UserFileSerializer(files, many=True, context={'request': request}).data,
            'categories': categories
        }
        return Response({'success': True, 'data': payload}, status=status.HTTP_200_OK)

    # POST: upload file
    if request.method == 'POST':
        file_obj  = request.FILES.get('file')
        file_type = request.data.get('file_type')

        if not file_obj or not file_type:
            return Response({'success': False, 'error': 'File and file type are required'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            storage_manager = S3StorageManager(request.user)
            if not storage_manager.check_storage_limit(file_obj.size):
                return Response({'success': False, 'error': 'Storage limit exceeded'},
                                status=status.HTTP_400_BAD_REQUEST)

            # Upload
            file_key = storage_manager.upload_file(file_obj, file_obj.name)
            user_file = UserFile.objects.create(
                user=request.user,
                file_type=file_type,
                file=file_key,
                original_filename=file_obj.name,
                file_size=file_obj.size
            )
            storage_info = storage_manager.get_user_storage_info()

            payload = {
                'file': UserFileSerializer(user_file, context={'request': request}).data,
                'storage_info': storage_info
            }
            return Response({'success': True, 'data': payload}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'success': False, 'error': str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)     
@csrf_exempt
@api_view(['GET', 'DELETE'])
@permission_classes([IsAuthenticated])
@mobile_api_view
def mobile_file_detail(request, file_id):
    """Mobile-optimized file detail endpoint for viewing and deleting files"""
    try:
        user_file = get_object_or_404(UserFile, id=file_id, user=request.user)
        
        if request.method == 'GET':
            # Return file details
            serializer = UserFileSerializer(user_file)
            
            # Get OCR result if it exists for documents
            ocr_text = None
            ocr_status = None
            
            if user_file.file_type == 'document':
                try:
                    ocr_result = OCRResult.objects.get(file=user_file)
                    ocr_text = ocr_result.text_content
                    ocr_status = ocr_result.status
                except OCRResult.DoesNotExist:
                    pass
            
            data = serializer.data
            if ocr_text:
                data['ocr_text'] = ocr_text
                data['ocr_status'] = ocr_status
                
            return data
            
        elif request.method == 'DELETE':
            # Delete the file
            try:
                # Get the full S3 key
                file_key = user_file.file.name
                
                # Delete from S3
                storage_manager = S3StorageManager(request.user)
                
                try:
                    # Try to delete from S3
                    s3_client = boto3.client(
                        's3',
                        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                        region_name=settings.AWS_S3_REGION_NAME
                    )
                    
                    # Delete the object directly
                    s3_client.delete_object(
                        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                        Key=file_key
                    )
                except Exception as s3_error:
                    print(f"S3 deletion error: {str(s3_error)}")
                    # Continue with database deletion even if S3 deletion fails
                
                # Delete the database record
                user_file.delete()
                
                return {
                    'message': 'File deleted successfully'
                }
                
            except Exception as e:
                return Response({
                    'success': False,
                    'error': f'Error deleting file: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
    except UserFile.DoesNotExist:
        return Response({
            'success': False,
            'error': 'File not found'
        }, status=status.HTTP_404_NOT_FOUND)
    

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_document_ocr(request, file_id):
    """Manually trigger OCR processing"""
    try:
        user_file = get_object_or_404(UserFile, id=file_id, user=request.user)
        
        # Use OCR service
        from .services import OCRService
        ocr_service = OCRService()
        result = ocr_service.process_file(user_file)
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'category': 'Miscellaneous'
        }, status=500)

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mobile_file_upload(request):
    """Fixed mobile file upload with OCR"""
    serializer = MobileFileUploadSerializer(data=request.data)

    if not serializer.is_valid():
        return Response({'success': False, 'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    try:
        file_obj = request.FILES.get('file')
        file_type = serializer.validated_data['file_type']
        category_id = serializer.validated_data.get('category_id')

        if not file_obj:
             return Response({'success': False, 'error': 'File not provided'}, status=status.HTTP_400_BAD_REQUEST)

        storage_manager = S3StorageManager(request.user)

        if not storage_manager.check_storage_limit(file_obj.size):
            return Response({'success': False, 'error': 'Storage limit would be exceeded'}, status=status.HTTP_400_BAD_REQUEST)

        # Upload file to S3
        s3_key = storage_manager.upload_file(file_obj, file_obj.name)
        
        # Determine category
        category = None
        should_auto_categorize = True
        
        if category_id:
            try:
                category = FileCategory.objects.get(id=category_id)
                should_auto_categorize = False
            except FileCategory.DoesNotExist:
                pass
        
        if not category:
            misc_category, _ = FileCategory.objects.get_or_create(
                name='Miscellaneous',
                defaults={'is_default': True, 'description': 'Uncategorized files'}
            )
            category = misc_category

        # Create UserFile record
        user_file = UserFile.objects.create(
            user=request.user,
            file_type=file_type,
            file=s3_key,
            s3_key=s3_key,
            original_filename=file_obj.name,
            file_size=file_obj.size,
            category=category,
            pending_auto_categorization=should_auto_categorize
        )
        
        # Get updated storage info
        storage_info = storage_manager.get_user_storage_info()
        
        # Start OCR processing for document and image files
        ocr_result = {'status': 'not_applicable'}
        if file_type in ['document', 'image']:
            try:
                from .services import OCRService
                ocr_service = OCRService()
                ocr_result = ocr_service.process_file(user_file)
                print(f"[Mobile Upload] OCR result: {ocr_result}")
            except Exception as ocr_error:
                print(f"[Mobile Upload] OCR error: {str(ocr_error)}")
                ocr_result = {'status': 'error', 'error': str(ocr_error)}
        
        return Response({
            'success': True,
            'message': 'File uploaded successfully',
            'file': UserFileSerializer(user_file).data,
            'storage_info': storage_info,
            'ocr_result': ocr_result
        }, status=status.HTTP_201_CREATED)
            
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def move_file(request, file_id):
    try:
        user_file = get_object_or_404(UserFile, id=file_id, user=request.user)
        category_id = request.data.get('category_id')
        
        if not category_id:
            return Response({
                'success': False,
                'error': 'Category ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            category = FileCategory.objects.get(id=category_id)
            
            # Update file category
            user_file.category = category
            user_file.save()
            
            return Response({
                'success': True,
                'message': 'File moved successfully',
                'file': UserFileSerializer(user_file).data
            })
        except FileCategory.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Category not found'
            }, status=status.HTTP_404_NOT_FOUND)
            
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def share_file(request, file_id):
    try:
        user_file = get_object_or_404(UserFile, id=file_id, user=request.user)
        
        # Set file as public
        user_file.is_public = True
        user_file.save()
        
        # Generate sharing URL
        storage_manager = S3StorageManager(request.user)
        share_url = storage_manager.get_file_url(user_file.s3_key, expiry=604800)  # 1 week expiry
        
        return Response({
            'success': True,
            'message': 'File shared successfully',
            'share_url': share_url,
            'expires_in': '7 days'
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def lock_file(request, file_id):
    """ENHANCED: Lock file with improved password validation"""
    try:
        user_file = get_object_or_404(UserFile, id=file_id, user=request.user)
        
        # Validate input
        serializer = FilePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        password = serializer.validated_data['password']
        
        # Lock the file
        user_file.lock_with_password(password, request.user)
        
        return Response({
            'success': True,
            'message': 'File locked successfully',
            'locked_at': user_file.locked_at
        })
        
    except ValidationError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def unlock_file(request, file_id):
    """ENHANCED: Unlock file with improved validation"""
    try:
        user_file = get_object_or_404(UserFile, id=file_id, user=request.user)
        
        if not user_file.locked:
            return Response({
                'success': False,
                'error': 'File is not locked'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        password = request.data.get('password')
        if not password:
            return Response({
                'success': False,
                'error': 'Password is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Attempt to unlock
        if user_file.unlock_with_password(password):
            return Response({
                'success': True,
                'message': 'File unlocked successfully'
            })
        else:
            return Response({
                'success': False,
                'error': 'Incorrect password'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rename_file(request, file_id):
    try:
        user_file = get_object_or_404(UserFile, id=file_id, user=request.user)
        new_name = request.data.get('new_name')
        
        if not new_name:
            return Response({
                'success': False,
                'error': 'New name is required'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        # Update file name
        user_file.original_filename = new_name
        user_file.save()
        
        return Response({
            'success': True,
            'message': 'File renamed successfully',
            'file': UserFileSerializer(user_file).data
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from file_management.models import OCRPreference

@csrf_exempt # If needed based on auth setup
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def ocr_preferences(request):
    ocr_pref, created = OCRPreference.objects.get_or_create(user=request.user)

    if request.method == 'GET':
        return Response({
            'success': True,
            'preference': ocr_pref.preference,
            'display': ocr_pref.get_preference_display()
        })
    elif request.method == 'POST':
        preference = request.data.get('preference')

        if preference not in dict(OCRPreference.OCR_CHOICES).keys(): # Validate against choices
            return Response({
                'success': False,
                'error': 'Invalid preference value.'
            }, status=status.HTTP_400_BAD_REQUEST)

        ocr_pref.preference = preference
        ocr_pref.save()

        return Response({
            'success': True,
            'message': 'OCR preferences updated.',
            'preference': ocr_pref.preference,
            'display': ocr_pref.get_preference_display()
        })
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_document_ocr_view(request, file_id):
    """
    API endpoint to manually trigger or re-trigger OCR processing for a file.
    """
    try:
        # Ensure the file exists and belongs to the user
        user_file = get_object_or_404(UserFile, id=file_id, user=request.user)

        # Check OCR Preference
        ocr_pref, _ = OCRPreference.objects.get_or_create(user=request.user)
        if ocr_pref.preference == 'none':
            return Response({
                'status': 'skipped',
                'message': 'OCR processing is disabled in user preferences.'
             }, status=status.HTTP_400_BAD_REQUEST)
        # If preference is 'selected', this explicit call allows processing.

        print(f"Manual OCR trigger requested for file {file_id}")
        # Set status to pending before triggering async task
        OCRResult.objects.update_or_create(
            file=user_file,
            defaults={'status': 'pending', 'job_id': None, 'text_content': None}
        )

        # Trigger the main logic asynchronously
        user_id = request.user.id
        transaction.on_commit(lambda: process_document_ocr_logic(user_id, file_id))

        return Response({
            'status': 'processing_scheduled',
            'message': 'OCR processing has been scheduled for the file.'
        })

    except UserFile.DoesNotExist:
        return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"Error triggering manual OCR for file {file_id}: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def access_locked_file(request, file_id):
    """Access locked file with password"""
    try:
        user_file = get_object_or_404(UserFile, id=file_id, user=request.user)
        password = request.data.get('password')
        
        if user_file.is_accessible_by_user(request.user, password):
            # Generate temporary access URL
            storage_manager = S3StorageManager(request.user)
            access_url = storage_manager.get_file_url(
                user_file.s3_key, 
                expiry=3600  # 1 hour access
            )
            
            return Response({
                'success': True,
                'access_url': access_url,
                'expires_in': 3600,
                'file': UserFileSerializer(user_file, context={'request': request}).data
            })
        else:
            return Response({
                'success': False,
                'error': 'Access denied. Incorrect password or insufficient permissions.'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_ocr_result(request, job_id):
    """Get OCR result by job ID"""
    try:
        ocr_result = get_object_or_404(OCRResult, job_id=job_id, file__user=request.user)
        user_file = ocr_result.file

        if ocr_result.status == 'completed':
            return JsonResponse({
                'status': 'completed',
                'text': ocr_result.text_content.split('\n') if ocr_result.text_content else [],
                'category': user_file.category.name if user_file.category else 'Miscellaneous',
                'file_id': user_file.id
            })
        elif ocr_result.status == 'failed':
            return JsonResponse({
                'status': 'failed',
                'error': ocr_result.text_content or 'OCR processing failed',
                'category': user_file.category.name if user_file.category else 'Miscellaneous'
            }, status=400)
        elif ocr_result.status == 'processing':
            # Check if job completed
            from .services import OCRService
            ocr_service = OCRService()
            result = ocr_service._complete_pdf_processing(user_file, ocr_result)
            
            if result['status'] == 'completed':
                return JsonResponse({
                    'status': 'completed',
                    'text': ocr_result.text_content.split('\n') if ocr_result.text_content else [],
                    'category': user_file.category.name if user_file.category else 'Miscellaneous',
                    'file_id': user_file.id
                })
            else:
                return JsonResponse({
                    'status': 'processing',
                    'message': 'OCR processing is still in progress'
                })
        else:
            return JsonResponse({
                'status': ocr_result.status,
                'message': f'OCR status: {ocr_result.status}'
            })

    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'category': 'Miscellaneous'
        }, status=500)

def award_coins_for_upload(user, user_file):
    """Award coins for file uploads - utility function for direct API calls"""
    try:
        from coin_wallet.models import CoinWallet, CoinTransaction
        import math
        
        # Calculate coins (1 coin per MB, minimum 1 coin)
        file_size_mb = math.ceil(user_file.file_size / (1024 * 1024))
        if file_size_mb < 1:
            file_size_mb = 1
        
        # Check if coins were already awarded
        if user_file.coins_awarded:
            return {"awarded": False, "reason": "Already awarded", "amount": 0}
        
        # Get or create the user's wallet
        wallet, created = CoinWallet.objects.get_or_create(user=user)
        
        # Check if a transaction already exists
        existing_transaction = CoinTransaction.objects.filter(
            wallet=wallet,
            transaction_type='upload',
            related_file=user_file
        ).exists()
        
        if existing_transaction:
            return {"awarded": False, "reason": "Transaction exists", "amount": 0}
        
        # Award coins
        wallet.add_coins(
            amount=file_size_mb,
            transaction_type='upload',
            source=f'File upload: {user_file.original_filename}'
        )
        
        # Update the transaction with the related file
        transaction = CoinTransaction.objects.filter(
            wallet=wallet,
            transaction_type='upload'
        ).latest('created_at')
        transaction.related_file = user_file
        transaction.save()
        
        # Mark coins as awarded
        user_file.coins_awarded = True
        user_file.save(update_fields=['coins_awarded'])
        
        return {"awarded": True, "amount": file_size_mb}
    except Exception as e:
        print(f"Error awarding coins: {str(e)}")
        return {"awarded": False, "reason": str(e), "amount": 0}
        
# Add after the ocr_preferences function

@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mobile_ocr_status(request, file_id):
    """Mobile-optimized endpoint for getting OCR status and text content."""
    try:
        user_file = get_object_or_404(UserFile, id=file_id, user=request.user)
        
        try:
            ocr_result = OCRResult.objects.get(file=user_file)
            
            return Response({
                'success': True,
                'ocr_status': ocr_result.status,
                'ocr_text': ocr_result.text_content if ocr_result.text_content else None,
                'category': user_file.category.name if user_file.category else 'Miscellaneous',
                'file_id': user_file.id
            })
        except OCRResult.DoesNotExist:
            return Response({
                'success': True,
                'ocr_status': 'not_started',
                'message': 'OCR has not been initiated for this file'
            })
    except UserFile.DoesNotExist:
        return Response({
            'success': False,
            'error': 'File not found.'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@mobile_api_view
def mobile_process_ocr(request, file_id):
    """Mobile-optimized endpoint for triggering OCR processing"""
    try:
        user_file = get_object_or_404(UserFile, id=file_id, user=request.user)
        
        # Check if file type is document
        if user_file.file_type != 'document':
            return {
                'success': False,
                'error': 'OCR processing is only available for document files'
            }
            
        # Set status to pending
        OCRResult.objects.update_or_create(
            file=user_file,
            defaults={'status': 'pending', 'job_id': None}
        )
        
        # Trigger OCR processing asynchronously
        user_id = request.user.id
        # Use transaction.on_commit for async processing
        from django.db import transaction
        transaction.on_commit(lambda: process_document_ocr_logic(user_id, file_id))
        
        return {
            'success': True,
            'message': 'OCR processing has been initiated',
            'ocr_status': 'pending'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


# file: file_management/views.py

from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import UserFile
from .serializers import UserFileSerializer

@api_view(['POST'])
@authentication_classes([JWTAuthentication, SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def create_document_pair(request):
    """
    Pair two uploaded UserFile objects (front/back) under a common document_type_name.
    """
    user = request.user
    # 1) Validate payload
    front_id = request.data.get('front_file_id')
    back_id  = request.data.get('back_file_id')
    doc_type = request.data.get('document_type_name', '').strip()

    if not front_id or not back_id:
        return Response(
            {"success": False, "error": "Both front_file_id and back_file_id are required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 2) Fetch both files, confirm they belong to this user
    front_file = get_object_or_404(UserFile, id=front_id, user=user)
    back_file  = get_object_or_404(UserFile, id=back_id,  user=user)

    # 3) Update only the fields that change
    front_file.document_side        = 'front'
    front_file.paired_document      = back_file
    front_file.document_type_name   = doc_type
    front_file.save(
        update_fields=['document_side', 'paired_document', 'document_type_name']
    )

    back_file.document_side         = 'back'
    back_file.paired_document       = front_file
    back_file.document_type_name    = doc_type
    back_file.save(
        update_fields=['document_side', 'paired_document', 'document_type_name']
    )

    # 4) Serialize with context so any URL/user fields still work
    serializer = UserFileSerializer(
        [front_file, back_file],
        many=True,
        context={'request': request}
    )
    front_data, back_data = serializer.data

    return Response({
        "success": True,
        "message": "Document pair created successfully",
        "front_file": front_data,
        "back_file": back_data
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def break_document_pair(request, file_id):
    """Break a document pair relationship"""
    try:
        user_file = get_object_or_404(UserFile, id=file_id, user=request.user)
        
        if not user_file.has_pair():
            return Response({
                'success': False,
                'error': 'Document is not paired'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        paired_file = user_file.paired_document
        
        # Reset both files
        user_file.document_side = 'single'
        user_file.paired_document = None
        user_file.save()
        
        if paired_file:
            paired_file.document_side = 'single'
            paired_file.paired_document = None
            paired_file.save()
        
        return Response({
            'success': True,
            'message': 'Document pair broken successfully'
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_paired_documents(request):
    """Get all paired documents for the user"""
    try:
        paired_docs = UserFile.objects.filter(
            user=request.user,
            document_side__in=['front', 'back']
        ).select_related('paired_document')
        
        # Group by document type
        grouped_docs = {}
        processed_ids = set()
        
        for doc in paired_docs:
            if doc.id in processed_ids:
                continue
                
            doc_type = doc.document_type_name or 'Unknown Document'
            if doc_type not in grouped_docs:
                grouped_docs[doc_type] = []
            
            pair_data = {
                'document_type': doc_type,
                'front': None,
                'back': None
            }
            
            if doc.document_side == 'front':
                pair_data['front'] = UserFileSerializer(doc).data
                if doc.paired_document:
                    pair_data['back'] = UserFileSerializer(doc.paired_document).data
                    processed_ids.add(doc.paired_document.id)
            elif doc.document_side == 'back':
                pair_data['back'] = UserFileSerializer(doc).data
                if doc.paired_document:
                    pair_data['front'] = UserFileSerializer(doc.paired_document).data
                    processed_ids.add(doc.paired_document.id)
            
            grouped_docs[doc_type].append(pair_data)
            processed_ids.add(doc.id)
        
        return Response({
            'success': True,
            'paired_documents': grouped_docs
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_pending_ocr_jobs(request):
    """Manually check pending OCR jobs"""
    try:
        from .services import OCRService
        ocr_service = OCRService()
        ocr_service.check_pending_jobs()
        return Response({'success': True, 'message': 'Checked pending OCR jobs'})
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_file_ocr_status(request, file_id):
    """Get OCR status for a specific file"""
    try:
        user_file = get_object_or_404(UserFile, id=file_id, user=request.user)
        
        try:
            ocr_result = OCRResult.objects.get(file=user_file)
            return Response({
                'success': True,
                'ocr_status': ocr_result.status,
                'has_text': bool(ocr_result.text_content),
                'text_length': len(ocr_result.text_content) if ocr_result.text_content else 0
            })
        except OCRResult.DoesNotExist:
            return Response({
                'success': True,
                'ocr_status': 'not_started',
                'has_text': False,
                'text_length': 0
            })
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=500)
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_favorite(request, file_id):
    """Toggle file favorite status"""
    try:
        user_file = get_object_or_404(UserFile, id=file_id, user=request.user)
        is_favorite = user_file.toggle_favorite()
        
        return Response({
            'success': True,
            'is_favorite': is_favorite,
            'message': f'File {"added to" if is_favorite else "removed from"} favorites'
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_hidden(request, file_id):
    """Toggle file hidden status"""
    try:
        user_file = get_object_or_404(UserFile, id=file_id, user=request.user)
        is_hidden = user_file.toggle_hidden()
        
        return Response({
            'success': True,
            'is_hidden': is_hidden,
            'message': f'File {"hidden" if is_hidden else "shown"}'
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

