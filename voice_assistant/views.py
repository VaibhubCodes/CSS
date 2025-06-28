from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from openai import OpenAI
import boto3
from django.conf import settings
import tempfile, json
from .models import VoiceInteraction
from django.shortcuts import render,get_object_or_404
from file_management.models import UserFile, FileCategory, OCRResult
from storage_management.utils import S3StorageManager
from datetime import datetime
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import tempfile, json, os, re
from datetime import datetime
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.utils import timezone
from .models import VoiceInteraction
from .serializers import (
    VoiceInteractionSerializer, VoiceCommandSerializer,
    CommandHistoryFilterSerializer, CommandSuggestionSerializer,
    AssistantSettingsSerializer
)
import uuid

import logging
logger = logging.getLogger(__name__)
client = OpenAI(api_key=settings.OPENAI_API_KEY)
s3_client = boto3.client(
    's3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_S3_REGION_NAME
)

def get_file_context(user):
    """Get more detailed context about user's files and storage for better AI responses"""
    storage_manager = S3StorageManager(user)
    storage_info = storage_manager.get_user_storage_info()
    
    # Get file statistics
    all_files = UserFile.objects.filter(user=user)
    file_count = all_files.count()
    
    # Get all categories and files per category
    categories_with_files = {}
    all_categories = FileCategory.objects.filter(
        userfile__user=user
    ).distinct()
    
    for category in all_categories:
        category_files = all_files.filter(category=category)
        categories_with_files[category.name] = {
            'count': category_files.count(),
            'files': [
                {
                    'name': f.original_filename, 
                    'type': f.file_type,
                    'id': f.id,
                    'upload_date': f.upload_date.strftime("%Y-%m-%d")
                } 
                for f in category_files.order_by('-upload_date')[:10]
            ]
        }
    
    # Get recent files
    recent_files = all_files.order_by('-upload_date')[:5]
    recent_file_details = [
        {
            'name': f.original_filename,
            'type': f.file_type,
            'category': f.category.name if f.category else 'Uncategorized',
            'id': f.id,
            'upload_date': f.upload_date.strftime("%Y-%m-%d")
        }
        for f in recent_files
    ]
    
    # Get files with OCR text
    files_with_ocr = []
    for ocr_result in OCRResult.objects.filter(file__user=user, status='completed').select_related('file'):
        if ocr_result.text_content:
            files_with_ocr.append({
                'id': ocr_result.file.id,
                'name': ocr_result.file.original_filename,
                'preview': ocr_result.text_content[:300] + '...' if len(ocr_result.text_content) > 300 else ocr_result.text_content
            })
    
    # Build detailed context string
    context = f"""
    Storage Information:
    - Used: {storage_info['used']} bytes ({(storage_info['used'] / storage_info['limit'] * 100):.1f}%)
    - Available: {storage_info['available']} bytes
    - Total Files: {file_count}
    
    Categories with File Counts:
    {', '.join([f"{cat}: {data['count']} files" for cat, data in categories_with_files.items()])}
    
    Recent Files:
    {', '.join([f"{f['name']} ({f['type']}, {f['category']})" for f in recent_file_details])}
    
    File Categories Structure:
    """
    
    # Add detailed category information
    for category, data in categories_with_files.items():
        context += f"\n{category} ({data['count']} files):"
        for file in data['files'][:5]:  # Show up to 5 files per category
            context += f"\n  - {file['name']} ({file['type']})"
        if len(data['files']) > 5:
            context += f"\n  - ... and {len(data['files']) - 5} more files"
    
    # Add OCR preview information
    if files_with_ocr:
        context += "\n\nFiles with OCR Content:"
        for file in files_with_ocr[:3]:  # Show up to 3 OCR previews
            context += f"\n  - {file['name']}: {file['preview']}"
    
    # Add capabilities info
    context += """
    
    As an AI assistant for this file management system, you can:
    1. Show files by category (e.g., "Show my Banking files")
    2. Display files in a specific format (e.g., "Show my files as bubbles")
    3. Summarize file contents (e.g., "Summarize my invoice from January")
    4. Search within files (e.g., "Find documents containing 'tax'")
    5. Provide storage information (e.g., "How much storage am I using?")
    6. Give file recommendations (e.g., "What should I do with my large files?")
    
    When showing files, always display them in a structured, easy-to-read format.
    For file searches or listings, group files by category when appropriate.
    """
    
    return context

@csrf_exempt
def process_voice(request):
    try:
        audio_file = request.FILES.get('audio')
        if not audio_file:
            return JsonResponse({'error': 'No audio file provided'}, status=400)

        # Process audio file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_audio:
            for chunk in audio_file.chunks():
                temp_audio.write(chunk)
            temp_audio_path = temp_audio.name

        try:
            # Transcribe audio
            with open(temp_audio_path, 'rb') as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en"
                )
            prompt_text = transcript.text

            # Append file context to user prompt
            file_context = get_file_context(request.user)
            assistant_prompt = f"""
            You are Sparkle, an intelligent assistant for a file management system. You're designed to help users manage, 
            find, and interact with their documents and files. REMEMBER:
            
            1. ALWAYS be detailed and specific about files.
            2. When asked to show files, do NOT just say 'Here are your files' - actually LIST the files by name, organized by category.
            3. When asked about storage, give precise numbers.
            4. When searching or summarizing files, mention specific file names in your response.
            5. Format your responses in a structured, easy-to-read way with proper organization.
            6. NEVER mention S3 or storage implementation details to the user. Always refer to files by their original names.
            7. When showing file lists, use bullet points and grouping by category.
            
            Here's the user's detailed file context:
            {file_context}

            User's request: {prompt_text}
            """

            # Get ChatGPT response with improved model
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are Sparkle, an intelligent file management assistant that gives detailed and specific answers about files."},
                    {"role": "user", "content": assistant_prompt}
                ],
                temperature=0.7,  # Slightly more creative but still focused
                max_tokens=1000   # Longer responses for more detail
            )
            response_text = response.choices[0].message.content

            # Generate speech
            speech_response = client.audio.speech.create(
                model="tts-1",
                voice="nova",
                input=response_text
            )

            # Save to temporary file first
            temp_response_path = f"/tmp/response_{datetime.now().timestamp()}.mp3"
            speech_response.stream_to_file(temp_response_path)

            # Upload to S3
            s3_key = f"media/voice_responses/response_{datetime.now().timestamp()}.mp3"
            s3_client.upload_file(
                temp_response_path,
                settings.AWS_STORAGE_BUCKET_NAME,
                s3_key
            )

            # Generate S3 URL
            presigned_url = s3_client.generate_presigned_url('get_object',
                Params={
                    'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                    'Key': s3_key
                },
                ExpiresIn=3600  # URL valid for 1 hour
            )

            # Clean up temporary response file
            os.remove(temp_response_path)

            # Save interaction to database
            VoiceInteraction.objects.create(
                user=request.user,
                prompt=prompt_text,
                response=response_text,
                audio_response_url=presigned_url
            )

            return JsonResponse({
                'status': 'success',
                'prompt': prompt_text,
                'response': response_text,
                'audio_url': presigned_url
            })

        finally:
            # Clean up temporary audio file
            os.remove(temp_audio_path)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def assistant_view(request):
    # Get storage information
    storage_manager = S3StorageManager(request.user)
    storage_info = storage_manager.get_user_storage_info()
    
    # Get file statistics
    files = UserFile.objects.filter(user=request.user)
    file_count = files.count()
    
    # Format storage sizes
    def format_size(size_in_bytes):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_in_bytes < 1024:
                return f"{size_in_bytes:.2f} {unit}"
            size_in_bytes /= 1024
        return f"{size_in_bytes:.2f} TB"
    
    context = {
        'storage_info': {
            'used': format_size(storage_info['used']),
            'available': format_size(storage_info['available']),
            'percentage': f"{storage_info['percentage_used']:.1f}%"
        },
        'file_count': file_count,
        'recent_files': files.order_by('-upload_date')[:5],
        'categories': FileCategory.objects.filter(userfile__user=request.user).distinct()
    }
    
    return render(request, 'assistant.html', context)

def update_reference_context(reference_context, file_obj):
    """
    Updates the reference context with a file that was just accessed.
    Returns an updated reference context dictionary.
    """
    if not reference_context:
        reference_context = {}
        
    if not file_obj:
        return reference_context
        
    # Create a standardized file reference
    file_reference = {
        'id': file_obj.id,
        'name': file_obj.original_filename,
        'type': getattr(file_obj, 'file_type', 'unknown')
    }
    
    # Update common reference terms
    reference_context['this'] = file_reference
    reference_context['it'] = file_reference
    reference_context['that'] = file_reference
    reference_context['this file'] = file_reference
    reference_context['that file'] = file_reference
    reference_context['the file'] = file_reference
    reference_context['the document'] = file_reference
    
    # If not already in numbered list, add as #1
    reference_context['1'] = file_reference
    
    return reference_context

class VoiceAssistantViewSet(viewsets.ModelViewSet):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    
    permission_classes = [IsAuthenticated]
    serializer_class = VoiceInteractionSerializer # Assuming this is for listing history

    def get_queryset(self):
        # Base queryset for listing interactions
        return VoiceInteraction.objects.filter(user=self.request.user).order_by('-created_at')
    

    @action(detail=False, methods=['post'])
    def process_command(self, request):
        serializer = VoiceCommandSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Process audio if provided
                if audio_file := serializer.validated_data.get('audio'):
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_audio:
                        for chunk in audio_file.chunks():
                            temp_audio.write(chunk)
                        temp_audio_path = temp_audio.name

                    # Transcribe audio
                    with open(temp_audio_path, 'rb') as audio:
                        transcript = client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio,
                            language="en"
                        )
                    prompt_text = transcript.text
                else:
                    prompt_text = serializer.validated_data['text']

                # Get file context
                file_context = self.get_file_context(request.user)
                assistant_prompt = self.format_assistant_prompt(prompt_text, file_context)

                # Get ChatGPT response
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful file management assistant."},
                        {"role": "user", "content": assistant_prompt}
                    ]
                )
                response_text = response.choices[0].message.content

                # Generate speech if settings allow
                audio_url = None
                if request.user.assistant_settings.get('include_audio_response', True):
                    speech_response = client.audio.speech.create(
                        model="tts-1",
                        voice=request.user.assistant_settings.get('voice_type', 'nova'),
                        input=response_text
                    )

                    # Save to temporary file
                    temp_response_path = f"/tmp/response_{datetime.now().timestamp()}.mp3"
                    speech_response.stream_to_file(temp_response_path)

                    # Upload to S3
                    s3_key = f"media/voice_responses/response_{datetime.now().timestamp()}.mp3"
                    s3_client.upload_file(
                        temp_response_path,
                        settings.AWS_STORAGE_BUCKET_NAME,
                        s3_key
                    )

                    # Generate presigned URL
                    audio_url = s3_client.generate_presigned_url(
                        'get_object',
                        Params={
                            'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                            'Key': s3_key
                        },
                        ExpiresIn=3600
                    )

                # Save interaction
                interaction = VoiceInteraction.objects.create(
                    user=request.user,
                    prompt=prompt_text,
                    response=response_text,
                    audio_response_url=audio_url
                )

                return Response(VoiceInteractionSerializer(interaction).data)

            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def command_history(self, request):
        queryset = self.get_queryset()
        serializer = CommandHistoryFilterSerializer(data=request.query_params)
        if serializer.is_valid():
            if start_date := serializer.validated_data.get('start_date'):
                queryset = queryset.filter(created_at__gte=start_date)

            if end_date := serializer.validated_data.get('end_date'):
                queryset = queryset.filter(created_at__lte=end_date)

            if keyword := serializer.validated_data.get('keyword'):
                queryset = queryset.filter(
                    Q(prompt__icontains=keyword) |
                    Q(response__icontains=keyword)
                )
        return Response(VoiceInteractionSerializer(queryset, many=True).data)

    @action(detail=False, methods=['get'])
    def suggestions(self, request):
        suggestions = [
            {'command': 'Show files', 'description': 'List files by category/type', 'examples': ['Show my banking documents', 'List all images']},
            {'command': 'Search files', 'description': 'Find files by keyword', 'examples': ['Search for invoice', 'Find resume file']},
            {'command': 'Summarize file', 'description': 'Get a summary of a specific file', 'examples': ['Summarize my report.pdf', 'What are the key points of meeting_notes.docx?']},
            {'command': 'Display file', 'description': 'Open/view a specific file', 'examples': ['Open presentation.pptx', 'Show file ID 123']},
            {'command': 'Rename file', 'description': 'Change a file\'s name', 'examples': ['Rename document.txt to final_report.txt']},
            {'command': 'Delete file', 'description': 'Permanently delete a file', 'examples': ['Delete old_draft.docx']},
            {'command': 'Move file', 'description': 'Move a file to another category', 'examples': ['Move contract.pdf to Professional category']},
            {'command': 'Share file', 'description': 'Get a temporary link to share a file', 'examples': ['Share my presentation.pptx']},
            {'command': 'Create folder', 'description': 'Create a new category', 'examples': ['Create a folder named Travel Photos']},
            {'command': 'Storage info', 'description': 'Check storage usage', 'examples': ['How much space am I using?']},
        ]
        serializer = CommandSuggestionSerializer(suggestions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get', 'patch'])
    def settings(self, request):
        user_settings, _ = request.user.assistant_settings, {}
        if request.method == 'GET':
            settings_data = user_settings or { # Provide defaults if null
                'voice_type': 'nova',
                'language': 'en',
                'response_length': 'concise',
                'include_audio_response': True
            }
            serializer = AssistantSettingsSerializer(settings_data)
            return Response(serializer.data)
        elif request.method == 'PATCH':
            serializer = AssistantSettingsSerializer(data=request.data, partial=True) # Allow partial updates
            if serializer.is_valid():
                updated_settings = {**(user_settings or {}), **serializer.validated_data}
                request.user.assistant_settings = updated_settings
                request.user.save(update_fields=['assistant_settings'])
                return Response(AssistantSettingsSerializer(updated_settings).data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_file_context(self, user):
        files = UserFile.objects.filter(user=user)
        categories = FileCategory.objects.filter(
            userfile__user=user
        ).distinct()
        recent_files = files.order_by('-upload_date')[:5]

        return {
            'file_count': files.count(),
            'categories': list(categories.values_list('name', flat=True)),
            'recent_files': list(recent_files.values_list('original_filename', flat=True))
        }

    def format_assistant_prompt(self, user_input, context):
        return f"""
        User's file context:
        - Total files: {context['file_count']}
        - Available categories: {', '.join(context['categories'])}
        - Recent files: {', '.join(context['recent_files'])}

        User's input: {user_input}
        """



# ============================================
# HELPER FUNCTIONS FOR SPARKLE (Function Calling Targets)
# ============================================


def find_file_by_name_or_id(user, file_name_or_id, operation_name="operation", reference_context=None, conversation_id=None):
    """
    Enhanced file finder with improved reference resolution and conversation history.
    
    Args:
        user: The user whose files to search
        file_name_or_id: The file name/ID or reference term like "this", "that", etc.
        operation_name: Name of the operation for logging
        reference_context: Dictionary of reference terms mapped to file names/IDs
        conversation_id: Optional conversation ID to check for recent file references
        
    Returns:
        UserFile object or None if not found
    """
    import logging
    from django.db.models import Q
    from file_management.models import UserFile
    import re
    

    logger.info(f"[{operation_name}] Finding file for user {user.id}: '{file_name_or_id}' (Conv ID: {conversation_id}) Context: {reference_context}")
    file_found = None
    
    # Handle empty or None input
    if not file_name_or_id:
        logger.warning(f"[{operation_name}] Empty or None file reference")
        return None
    reference_context = reference_context or {}
    # First check if this is a reference term ("this", "that", etc.)
    if isinstance(file_name_or_id, str):
        # Convert to lowercase for case-insensitive matching
        ref_term = file_name_or_id.lower().strip()
        
        # Try to match common reference terms like "this file", "that document", etc.
        if any(ref in ref_term for ref in ["this", "that", "it", "file", "document"]):
            # Extract possible reference keys
            potential_refs = []
            if "this" in ref_term or "this file" in ref_term or "this document" in ref_term:
                potential_refs.append("this")
            if "that" in ref_term or "that file" in ref_term or "that document" in ref_term:
                potential_refs.append("that")
            if "it" in ref_term or "the file" in ref_term or "the document" in ref_term:
                potential_refs.append("it")
                
            # Try each potential reference
            for ref in potential_refs:
                if ref in reference_context:
                    ref_value = reference_context[ref]
                    logger.info(f"[{operation_name}] Found reference term '{ref}' -> '{ref_value}'")
                    
                    # The reference could now be a dictionary with name and ID
                    if isinstance(ref_value, dict) and 'id' in ref_value:
                        # Return the file by ID directly - most reliable
                        file_id = ref_value['id']
                        logger.info(f"[{operation_name}] Reference resolves to file ID: {file_id}")
                        try:
                            user_file = UserFile.objects.filter(id=file_id, user=user).first()
                            if user_file:
                                return user_file
                        except Exception as e:
                            logger.warning(f"[{operation_name}] Error finding file by ID from reference: {e}")
                            # Fall back to using the name
                            if 'name' in ref_value:
                                logger.info(f"[{operation_name}] Falling back to file name: {ref_value['name']}")
                    
                    # The reference could be a direct filename or ID (old format)
                    elif isinstance(ref_value, (str, int)):
                        # Recursively call with the resolved reference
                        user_file = find_file_by_name_or_id(user, ref_value, operation_name)
                        if user_file:
                            return user_file
                    # Or it could be a list (for plural references like "these files")
                    elif isinstance(ref_value, list) and len(ref_value) > 0:
                        # Take the first item for singular operations
                        logger.info(f"[{operation_name}] Reference '{ref}' resolves to a list, using first item")
                        if isinstance(ref_value[0], dict) and 'id' in ref_value[0]:
                            file_id = ref_value[0]['id']
                            try:
                                user_file = UserFile.objects.filter(id=file_id, user=user).first()
                                if user_file:
                                    return user_file
                            except Exception as e:
                                logger.warning(f"[{operation_name}] Error finding file by ID from list reference: {e}")
                        else:
                            user_file = find_file_by_name_or_id(user, ref_value[0], operation_name)
                            if user_file:
                                return user_file
    
    # If no match found from reference_context, check conversation history
    if not file_found and conversation_id:
        try:
            from voice_assistant.models import VoiceInteraction
            # Get recent interactions for this conversation
            recent_interactions = VoiceInteraction.objects.filter(
                user=user,
                conversation_id=conversation_id
            ).order_by('-created_at')[:5]  # Get last 5 interactions
            
            # Check if any recent interaction has a referenced file
            for interaction in recent_interactions:
                if interaction.referenced_file_id:
                    logger.info(f"[{operation_name}] Found referenced file from conversation history: {interaction.referenced_file_id}")
                    file = UserFile.objects.filter(id=interaction.referenced_file_id, user=user).first()
                    if file:
                        return file
                        
                # Also check reference_context from recent interactions
                if interaction.reference_context:
                    # Try common keys in the stored reference_context
                    for key in ['this', 'that', 'it', '1']:
                        if key in interaction.reference_context:
                            ref_data = interaction.reference_context[key]
                            if isinstance(ref_data, dict) and 'id' in ref_data:
                                file_id = ref_data['id']
                                file = UserFile.objects.filter(id=file_id, user=user).first()
                                if file:
                                    logger.info(f"[{operation_name}] Found file from conversation history reference_context: {file.id}")
                                    return file
        except Exception as e:
            logger.warning(f"[{operation_name}] Error checking conversation history: {e}")
    
    # Continue with direct name matching, etc.
    # (Keeping the existing file matching logic from the original function)
    file_found = None  # Initialize variable for the rest of the function
    
    # Try direct ID match if it's a number
    if isinstance(file_name_or_id, int) or (isinstance(file_name_or_id, str) and file_name_or_id.isdigit()):
        try:
            file_id = int(file_name_or_id)
            file = UserFile.objects.filter(id=file_id, user=user).first()
            if file:
                logger.info(f"[{operation_name}] Found file by ID {file_id}: {file.original_filename}")
                return file
        except (ValueError, TypeError):
            pass  # Not a valid integer ID, continue to name matching
    
    # Handle string matching
    if isinstance(file_name_or_id, str):
        # Clean up the filename for comparison
        search_name = file_name_or_id.strip().lower()
        
        # Create alternative search name variations
        search_variations = [search_name]
        
        # Add a variation with spaces removed
        no_spaces_search = search_name.replace(" ", "")
        if no_spaces_search != search_name:
            search_variations.append(no_spaces_search)
        
        # Try to split camelCase (e.g., "CGProjectPlanes" -> "cg project planes")
        camel_case_pattern = re.compile(r'((?<=[a-z])[A-Z]|(?<!\A)[A-Z](?=[a-z]))')
        camel_split_search = camel_case_pattern.sub(r' \1', search_name).lower()
        if camel_split_search != search_name:
            search_variations.append(camel_split_search)
            
        # Add joined variation without spaces
        if " " in search_name:
            search_variations.append("".join(search_name.split()))
            
        logger.info(f"[{operation_name}] Search variations: {search_variations}")
        
        # Try each search variation
        for variant in search_variations:
            # 1. Try exact match first (case-insensitive)
            file = UserFile.objects.filter(
                user=user, 
                original_filename__iexact=variant
            ).first()
            
            if file:
                logger.info(f"[{operation_name}] Found exact filename match with variant '{variant}': {file.original_filename}")
                return file
            
            # 2. Try with added extensions if no extension present
            if '.' not in variant:
                common_extensions = ['.pdf', '.docx', '.doc', '.xlsx', '.txt', '.jpg', '.png']
                for ext in common_extensions:
                    file = UserFile.objects.filter(
                        user=user, 
                        original_filename__iexact=variant + ext
                    ).first()
                    if file:
                        logger.info(f"[{operation_name}] Found match with added extension {ext} to variant '{variant}': {file.original_filename}")
                        return file
        
        # For more fuzzy matches, use the original search term but also collect matches from all variations
        all_base_matches = []
        all_partial_matches = []
        
        for variant in search_variations:
            # 3. Try matching the beginning of filename (startswith)
            base_name_matches = UserFile.objects.filter(
                user=user,
                original_filename__istartswith=variant
            ).order_by('-upload_date')
            
            all_base_matches.extend(list(base_name_matches))
            
            # 4. Try fuzzy partial matching within filenames (contains)
            partial_matches = UserFile.objects.filter(
                user=user,
                original_filename__icontains=variant
            ).order_by('-upload_date')
            
            all_partial_matches.extend(list(partial_matches))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_base_matches = [x for x in all_base_matches if not (x.id in seen or seen.add(x.id))]
        
        if unique_base_matches:
            file = unique_base_matches[0]
            logger.info(f"[{operation_name}] Found base name match: {file.original_filename}")
            return file
            
        seen = set()
        unique_partial_matches = [x for x in all_partial_matches if not (x.id in seen or seen.add(x.id))]
        
        if unique_partial_matches:
            file = unique_partial_matches[0]
            logger.info(f"[{operation_name}] Found partial name match: {file.original_filename}")
            return file
            
        # 5. Try splitting search term into words and matching on individual words
        search_words = search_name.split()
        if len(search_words) > 1:
            logger.info(f"[{operation_name}] Trying multi-word matching with {len(search_words)} words")
            
            # Try matching on any individual word within the filename
            word_matches = []
            for word in search_words:
                # Skip very short words (< 3 chars)
                if len(word) < 3:
                    continue
                    
                matches = UserFile.objects.filter(
                    user=user,
                    original_filename__icontains=word
                )
                word_matches.extend(list(matches))
            
            # Count occurrences of each file to rank by match quality
            if word_matches:
                from collections import Counter
                file_counts = Counter(word_matches)
                # Get the file with the most word matches
                best_match = file_counts.most_common(1)[0][0]
                logger.info(f"[{operation_name}] Found best word match: {best_match.original_filename}")
                return best_match
    
    # No matches found
    logger.warning(f"[{operation_name}] No file found for '{file_name_or_id}'")
    return None

def list_files_for_sparkle(user, category_name=None, file_type=None):
    """Lists user's files based on filters."""
    operation_name = "list_files"
    logger.info(f"[{operation_name}] User: {user.id} | Category: '{category_name}' | Type: '{file_type}'")
    try:
        files = UserFile.objects.filter(user=user)
        filters_applied = []
        if category_name:
            # Handle potential variations like "Banking documents" -> "Banking"
            simple_category_name = category_name.split(' ')[0]
            files = files.filter(category__name__iexact=simple_category_name)
            filters_applied.append(f"category '{category_name}'")
        if file_type:
            type_map = {'pdf': 'document', 'doc': 'document', 'docx': 'document',
                        'xls': 'document', 'xlsx': 'document', 'image': 'image',
                        'jpg': 'image', 'jpeg': 'image', 'png': 'image', 'audio': 'audio', 'mp3':'audio', 'wav': 'audio'}
            search_type = type_map.get(file_type.lower(), file_type.lower())
            valid_types = [choice[0] for choice in UserFile.FILE_TYPES]
            if search_type in valid_types:
                 files = files.filter(file_type=search_type)
                 filters_applied.append(f"type '{file_type}'")
            else:
                 files = files.filter(original_filename__iendswith=f'.{file_type}')
                 filters_applied.append(f"extension '.{file_type}'")

        files = files.select_related('category').order_by('-upload_date')
        count = files.count()

        if count == 0:
            filter_str = f" matching {', '.join(filters_applied)}" if filters_applied else ""
            result_text = f"You don't seem to have any files{filter_str}."
            logger.info(f"[{operation_name}] Found 0 files.")
            # Still success, just no results
            return json.dumps({"success": True, "count": 0, "result": result_text})
        else:
            grouped_files = {}
            limit = 20
            for f in files[:limit]:
                cat_name = f.category.name if f.category else "Uncategorized"
                if cat_name not in grouped_files:
                    grouped_files[cat_name] = []
                grouped_files[cat_name].append(f"- ID:{f.id} {f.original_filename} (Type: {f.get_file_type_display()}, Uploaded: {timezone.localtime(f.upload_date).strftime('%b %d, %Y')})")

            result_text = f"Found {count} file(s)"
            if filters_applied:
                 result_text += f" matching {', '.join(filters_applied)}"
            result_text += ":\n"
            for cat, file_list in grouped_files.items():
                result_text += f"\n📁 Category: {cat}\n" + "\n".join(file_list)
            if count > limit:
                 result_text += f"\n... and {count - limit} more files."

            logger.info(f"[{operation_name}] Found {count} files.")
            return json.dumps({"success": True, "count": count, "result": result_text})

    except Exception as e:
        logger.exception(f"[{operation_name}] Error: {e}")
        return json.dumps({"success": False, "error": "Sorry, I encountered an error while trying to list your files."})

def search_files_for_sparkle(user, keyword):
    """Searches file names and OCR content."""
    operation_name = "search_files"
    logger.info(f"[{operation_name}] User: {user.id} | Keyword: '{keyword}'")
    try:
        if not keyword or len(keyword) < 3:
            logger.warning(f"[{operation_name}] Keyword too short: '{keyword}'")
            return json.dumps({"success": False, "error": "Please provide a search keyword with at least 3 characters."})

        name_matches = UserFile.objects.filter(Q(user=user) & Q(original_filename__icontains=keyword))
        ocr_matches = UserFile.objects.filter(Q(user=user) & Q(ocrresult__text_content__icontains=keyword) & Q(ocrresult__status='completed'))
        all_matches = (name_matches | ocr_matches).distinct().select_related('category').order_by('-upload_date')
        count = all_matches.count()

        if count == 0:
            result_text = f"I couldn't find any files containing '{keyword}' in the name or content."
            logger.info(f"[{operation_name}] Found 0 matches for '{keyword}'.")
            return json.dumps({"success": True, "count": 0, "result": result_text}) # Success, but no results
        else:
            limit = 20
            response_list = [f"- ID:{f.id} {f.original_filename} (Category: {f.category.name if f.category else 'Uncategorized'})" for f in all_matches[:limit]]
            result_text = f"I found {count} file(s) containing '{keyword}':\n" + "\n".join(response_list)
            if count > limit:
                result_text += f"\n... and {count - limit} more matches."

            logger.info(f"[{operation_name}] Found {count} matches for '{keyword}'.")
            return json.dumps({"success": True, "count": count, "result": result_text})

    except Exception as e:
        logger.exception(f"[{operation_name}] Error: {e}")
        return json.dumps({"success": False, "error": "Sorry, I encountered an error while searching your files."})

def get_file_details_for_display(user, file_name_or_id, reference_context=None):
    """
    Gets file details and URL, using context.
    Returns: (json_string, UserFile_object_or_None)
    """
    operation_name = "display_file"
    file = find_file_by_name_or_id(user, file_name_or_id, operation_name, reference_context)

    if not file:
        error_message = f"I couldn't find a file matching '{file_name_or_id}'. Please check the name or try again."
        logger.warning(f"[{operation_name}] File not found: '{file_name_or_id}' for user {user.id}")
        return json.dumps({"success": False, "error": error_message}), None

    try:
        storage_manager = S3StorageManager(user)
        # Try generating download URL first
        file_url = storage_manager.generate_download_url(file.s3_key, expires_in=3600)
        if not file_url: # Fallback
             file_url = storage_manager.get_file_url(file.s3_key, expiry=3600)

        if not file_url:
             logger.error(f"[{operation_name}] Failed to generate URL for file {file.id}")
             return json.dumps({"success": False, "error": "Could not generate a link for this file."}), file

        logger.info(f"[{operation_name}] Generated URL for file {file.id}: {file.original_filename}")

        result_message = f"""
Here's the file you requested:
File: {file.original_filename}
Category: {file.category.name if file.category else "Uncategorized"}
Type: {file.get_file_type_display() if hasattr(file, 'get_file_type_display') else file.file_type}
Uploaded: {file.upload_date.strftime("%B %d, %Y")}

Direct Link: {file_url}
        """
        payload = {
            "success": True,
            "file_id": file.id, "fileId": file.id,
            "file_name": file.original_filename, "fileName": file.original_filename,
            "file_type": file.file_type, "fileType": file.file_type,
            "category": file.category.name if file.category else "Uncategorized",
            "upload_date": file.upload_date.strftime("%Y-%m-%d"), "uploadDate": file.upload_date.strftime("%Y-%m-%d"),
            "file_url": file_url, "fileUrl": file_url, "url": file_url, "direct_url": file_url,
            "result": result_message
        }
        return json.dumps(payload), file # Return the found file object

    except Exception as e:
        logger.exception(f"[{operation_name}] Error generating details/URL for file {file.id}: {e}")
        return json.dumps({"success": False, "error": f"Sorry, an error occurred while getting details for '{file.original_filename}'."}), file

def summarize_file_for_sparkle(user, file_name_or_id, reference_context=None):
    """
    Summarizes file content using context.
    Returns: (json_string, UserFile_object_or_None)
    """
    operation_name = "summarize_file"
    file = find_file_by_name_or_id(user, file_name_or_id, operation_name, reference_context)

    if not file:
        error_message = f"I couldn't find a file matching '{file_name_or_id}' to summarize."
        logger.warning(f"[{operation_name}] File not found: '{file_name_or_id}' for user {user.id}")
        return json.dumps({"success": False, "error": error_message}), None

    try:
        ocr_result = OCRResult.objects.filter(file=file, status='completed').first()
        if not ocr_result or not ocr_result.text_content:
            logger.info(f"[{operation_name}] No completed OCR text found for file {file.id}. Cannot summarize.")
            # Optionally trigger OCR here if desired, or just report failure
            return json.dumps({"success": False, "error": f"I found '{file.original_filename}', but it doesn't have text content I can summarize yet. Please ensure OCR has been processed."}), file

        text_content = ocr_result.text_content
        is_truncated = False
        max_length = 9000 # Limit context window for summarization
        if len(text_content) > max_length:
            text_content = text_content[:max_length] + "..."
            is_truncated = True

        logger.info(f"[{operation_name}] Sending file {file.id} content (truncated: {is_truncated}) to OpenAI for summarization.")
        summary_response = client.chat.completions.create(
            model="gpt-4-turbo", # Or gpt-3.5-turbo if preferred
            messages=[
                {"role": "system", "content": "You summarize documents concisely but informatively, extracting key points."},
                {"role": "user", "content": f"Summarize this text from document '{file.original_filename}':\n\n{text_content}"}
            ],
            max_tokens=800
        )
        summary = summary_response.choices[0].message.content
        if is_truncated:
            summary += "\n\n(Note: Summary based on the first part of a long document.)"

        # Try to get a file URL to include
        file_url = None
        try:
            storage_manager = S3StorageManager(user)
            file_url = storage_manager.generate_download_url(file.s3_key, expires_in=3600)
        except Exception as url_error:
            logger.warning(f"[{operation_name}] Could not generate URL for summarized file {file.id}: {url_error}")

        result_text = f"**Summary of '{file.original_filename}'**:\n\n{summary}"
        if file_url:
            result_text += f"\n\nView Document: {file_url}"

        payload = {
            "success": True,
            "file_id": file.id,
            "file_name": file.original_filename,
            "summary": summary,
            "file_url": file_url,
            "result": result_text
        }
        return json.dumps(payload), file # Return the file object

    except Exception as e:
        logger.exception(f"[{operation_name}] Error summarizing file {file.id}: {e}")
        return json.dumps({"success": False, "error": f"Sorry, an error occurred while summarizing '{file.original_filename}'."}), file

def get_storage_info_for_sparkle(user):
    try:
        storage_manager = S3StorageManager(user)
        info = storage_manager.get_user_storage_info()
        # Format for readability
        used_gb = info['used'] / (1024**3)
        limit_gb = info['limit'] / (1024**3)
        perc = info['percentage_used']
        result_text = f"You are currently using {used_gb:.2f} GB out of {limit_gb:.1f} GB ({perc:.1f}% used)."
        return json.dumps({"success": True, "result": result_text})
    except Exception as e:
        logger.exception(f"Error getting storage info for Sparkle: {e}")
        return json.dumps({"success": False, "error": "Sorry, I couldn't retrieve your storage information right now."})

def rename_file_for_sparkle(user, file_name_or_id, new_name, reference_context=None):
    """
    Renames a file using context.
    Returns: (json_string, UserFile_object_or_None)
    """
    operation_name = "rename_file"
    file = find_file_by_name_or_id(user, file_name_or_id, operation_name, reference_context)

    if not file:
        error_message = f"I couldn't find a file matching '{file_name_or_id}' to rename."
        logger.warning(f"[{operation_name}] File not found: '{file_name_or_id}' for user {user.id}")
        return json.dumps({"success": False, "error": error_message}), None

    if not new_name or len(new_name.strip()) < 3:
        logger.warning(f"[{operation_name}] Invalid new name provided: '{new_name}'")
        return json.dumps({"success": False, "error": "Please provide a valid new name (at least 3 characters)."}), file

    try:
        old_name = file.original_filename
        # Preserve extension if missing in new_name
        if '.' not in new_name and '.' in old_name:
            original_extension = old_name.rsplit('.', 1)[-1]
            new_name = f"{new_name.strip()}.{original_extension}"
        else:
             new_name = new_name.strip() # Ensure no leading/trailing whitespace

        if old_name == new_name:
            return json.dumps({"success": False, "error": f"The new name '{new_name}' is the same as the current name."}), file

        file.original_filename = new_name
        file.save(update_fields=['original_filename']) # Only update the filename field

        logger.info(f"[{operation_name}] Successfully renamed file {file.id} from '{old_name}' to '{new_name}'")
        payload = {
            "success": True,
            "file_id": file.id,
            "old_name": old_name,
            "new_name": new_name,
            "result": f"Okay, I've renamed the file from '{old_name}' to '{new_name}'."
        }
        return json.dumps(payload), file # Return the file object

    except Exception as e:
        logger.exception(f"[{operation_name}] Error renaming file {file.id}: {e}")
        return json.dumps({"success": False, "error": f"Sorry, an error occurred while renaming '{old_name}'."}), file

def delete_file_for_sparkle(user, file_name_or_id, reference_context=None):
    """
    Deletes a file using context.
    Returns: (json_string, UserFile_object_or_None)
    """
    operation_name = "delete_file"
    file = find_file_by_name_or_id(user, file_name_or_id, operation_name, reference_context)

    if not file:
        error_message = f"I couldn't find a file matching '{file_name_or_id}' to delete."
        logger.warning(f"[{operation_name}] File not found: '{file_name_or_id}' for user {user.id}")
        return json.dumps({"success": False, "error": error_message}), None

    try:
        file_name_deleted = file.original_filename
        file_id_deleted = file.id # Capture ID before deletion
        file.delete() # This should handle S3 deletion via the model's method override
        logger.info(f"[{operation_name}] Successfully deleted file '{file_name_deleted}' (ID: {file_id_deleted}) for user {user.id}")
        payload = {
            "success": True,
            "deleted_file_name": file_name_deleted,
            "deleted_file_id": file_id_deleted,
            "result": f"Okay, I have permanently deleted the file '{file_name_deleted}'."
        }
        return json.dumps(payload), None # Return None for file object

    except Exception as e:
        logger.exception(f"[{operation_name}] Error deleting file ID {file.id if file else 'unknown'}: {e}")
        return json.dumps({"success": False, "error": f"Sorry, an error occurred while trying to delete '{file.original_filename if file else file_name_or_id}'."}), file

def move_file_for_sparkle(user, file_name_or_id, target_category_name, reference_context=None):
    """
    Moves a file using context.
    Returns: (json_string, UserFile_object_or_None)
    """
    operation_name = "move_file"
    file = find_file_by_name_or_id(user, file_name_or_id, operation_name, reference_context)

    if not file:
        error_message = f"I couldn't find a file matching '{file_name_or_id}' to move."
        logger.warning(f"[{operation_name}] File not found: '{file_name_or_id}' for user {user.id}")
        return json.dumps({"success": False, "error": error_message}), None

    if not target_category_name:
         return json.dumps({"success": False, "error": "Please specify which category/folder to move the file to."}), file

    try:
        target_category = FileCategory.objects.filter(
            Q(created_by=user) | Q(is_default=True), # Allow moving to default or user's own
            name__iexact=target_category_name.strip()
        ).first()

        if not target_category:
            # Option 1: Fail if category doesn't exist
            # return json.dumps({"success": False, "error": f"I couldn't find a category named '{target_category_name}'. Would you like to create it?"}), file
            # Option 2: Create the category if it doesn't exist (as implemented before)
             logger.info(f"[{operation_name}] Category '{target_category_name}' not found, creating it for user {user.id}.")
             target_category = FileCategory.objects.create(name=target_category_name.strip().title(), created_by=user, is_default=False)


        original_category_name = file.category.name if file.category else "Uncategorized"

        if file.category and file.category.id == target_category.id:
            logger.info(f"[{operation_name}] File {file.id} already in category '{target_category.name}'.")
            return json.dumps({"success": False, "error": f"'{file.original_filename}' is already in the '{target_category.name}' category."}), file

        file.category = target_category
        file.save(update_fields=['category'])

        logger.info(f"[{operation_name}] Successfully moved file {file.id} from '{original_category_name}' to '{target_category.name}'")
        payload = {
            "success": True,
            "file_id": file.id,
            "file_name": file.original_filename,
            "from_category": original_category_name,
            "to_category": target_category.name,
            "result": f"Okay, I've moved '{file.original_filename}' to the '{target_category.name}' category."
        }
        return json.dumps(payload), file # Return the file object

    except Exception as e:
        logger.exception(f"[{operation_name}] Error moving file {file.id}: {e}")
        return json.dumps({"success": False, "error": f"Sorry, an error occurred while moving '{file.original_filename}'."}), file

def share_file_for_sparkle(user, file_name_or_id, reference_context=None):
    """
    Generates a share link using context.
    Returns: (json_string, UserFile_object_or_None)
    """
    operation_name = "share_file"
    file = find_file_by_name_or_id(user, file_name_or_id, operation_name, reference_context)

    if not file:
        error_message = f"I couldn't find a file matching '{file_name_or_id}' to share."
        logger.warning(f"[{operation_name}] File not found: '{file_name_or_id}' for user {user.id}")
        return json.dumps({"success": False, "error": error_message}), None

    try:
        if not file.s3_key:
            logger.error(f"[{operation_name}] Cannot share file {file.id} - S3 key missing.")
            return json.dumps({"success": False, "error": "Sharing is not available for this file right now."}), file

        storage_manager = S3StorageManager(user)
        share_url = storage_manager.generate_download_url(file.s3_key, expires_in=86400) # 1 day expiry

        if not share_url:
            logger.error(f"[{operation_name}] Failed to generate share URL for file {file.id}")
            return json.dumps({"success": False, "error": "Sorry, I couldn't create a share link for that file."}), file

        logger.info(f"[{operation_name}] Successfully generated share link for file {file.id} ('{file.original_filename}')")
        result_text = f"Okay, here is a temporary link to share '{file.original_filename}'. It will expire in 24 hours:\n{share_url}"
        payload = {
            "success": True,
            "file_id": file.id,
            "file_name": file.original_filename,
            "share_url": share_url,
            "expires_in_seconds": 86400,
            "result": result_text
        }
        return json.dumps(payload), file # Return the file object

    except Exception as e:
        logger.exception(f"[{operation_name}] Error sharing file {file.id}: {e}")
        return json.dumps({"success": False, "error": f"Sorry, an error occurred while creating a share link for '{file.original_filename}'."}), file

def create_folder_for_sparkle(user, folder_name):
    """Creates a new custom category (folder)."""
    operation_name = "create_folder"
    logger.info(f"[{operation_name}] User: {user.id} | Folder Name: '{folder_name}'")
    try:
        if not folder_name or len(folder_name) < 3:
            return json.dumps({"success": False, "error": "Please provide a folder name (at least 3 characters)."})

        # Check if category already exists (case-insensitive)
        existing_category = FileCategory.objects.filter(
            Q(created_by=user) | Q(is_default=True), # User can't create a default category name
            name__iexact=folder_name
        ).first()

        if existing_category:
            logger.warning(f"[{operation_name}] Folder '{folder_name}' already exists for user {user.id}.")
            return json.dumps({"success": False, "error": f"A folder named '{existing_category.name}' already exists."})

        # Create new category
        new_category = FileCategory.objects.create(
            name=folder_name.title(), # Capitalize
            created_by=user,
            is_default=False
        )
        logger.info(f"[{operation_name}] Success. Created folder '{new_category.name}' for user {user.id}.")
        return json.dumps({"success": True, "result": f"Okay, I've created the folder '{new_category.name}'."})

    except Exception as e:
        logger.exception(f"[{operation_name}] Error: {e}")
        return json.dumps({"success": False, "error": "Sorry, I couldn't create the folder due to an internal error."})

from django.contrib.auth import get_user_model 
User = get_user_model()
# ============================================
# MAIN VOICE/TEXT PROCESSING API VIEW
# ============================================

from rest_framework.permissions import AllowAny
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny]) 
def process_voice_api(request):
    """
    Processes voice/text input using conversation history and context.
    Handles function calling for file operations.
    Allows unauthenticated access for template demo, using a default user.
    """
    # --- Service Availability Check ---
    if not client:
         logger.error("OpenAI client not initialized.")
         return Response({'success': False, 'error': 'AI service is unavailable.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    if not s3_client:
         logger.error("S3 client not initialized.")
         # Allow non-S3 operations, but log warning
         # Return error only if an S3 operation is attempted later

    # --- Determine User ---
    user = None
    if request.user.is_authenticated:
        user = request.user
        logger.info(f"Authenticated user {user.id} accessing process_voice_api.")
    else:
        # --- Fallback for Unauthenticated Template/Demo Access ---
        logger.warning("Unauthenticated access to process_voice_api. Attempting fallback user.")
        # Prioritize a user named 'demo' or 'test', then superuser, then first user
        user = User.objects.filter(username='demo').first() or \
               User.objects.filter(username='test').first() or \
               User.objects.filter(is_superuser=True).order_by('id').first() or \
               User.objects.order_by('id').first()

        if not user:
            logger.error("No authenticated user and no fallback user found.")
            return Response({
                'success': False,
                'error': 'Authentication required and no default user available.'
            }, status=status.HTTP_401_UNAUTHORIZED) # Return 401 if truly no user
        logger.info(f"Using fallback user {user.username} (ID: {user.id}) for unauthenticated request.")
    # --- END Determine User ---

    # --- Initialize variables ---
    prompt_text = None
    temp_audio_path = None
    conversation_id_str = request.data.get('conversation_id') # Get as string first
    conversation_id = None
    current_reference_context = {}
    final_response_text = "Sorry, I couldn't process that request." # Default error
    function_executed_successfully = True # Assume success initially
    action_payload = None
    operated_file_object = None
    audio_url = None
    interaction_success = False # Overall success of the interaction

    # --- Validate and Parse conversation_id ---
    if conversation_id_str:
        try:
            conversation_id = uuid.UUID(conversation_id_str)
        except ValueError:
            logger.warning(f"User {user.id} - Invalid conversation_id format received: {conversation_id_str}. Starting new conversation.")
            conversation_id = uuid.uuid4() # Treat as new if invalid UUID
    else:
        conversation_id = uuid.uuid4() # Start new conversation
        logger.info(f"User {user.id} - No conversation_id provided. Starting new conversation: {conversation_id}")

    # Determine if audio response is needed (handle potential string 'true'/'false')
    include_audio_req = request.data.get('include_audio', 'true')
    include_audio_response = str(include_audio_req).lower() == 'true'


    try:
        # --- Step 1: Get Text Input (Transcription or Direct Text) ---
        if 'audio' in request.FILES:
            audio_file = request.FILES['audio']
            logger.info(f"User {user.id} - Processing audio input for conversation {conversation_id}...")
            # Define suffix based on content type or filename if possible
            content_type = audio_file.content_type
            suffix = '.wav' # Default
            if 'mp4' in content_type: suffix = '.mp4'
            elif 'mpeg' in content_type: suffix = '.mp3' # mpeg often means mp3
            elif 'm4a' in content_type: suffix = '.m4a'
            elif 'aac' in content_type: suffix = '.aac'

            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_audio:
                for chunk in audio_file.chunks(): temp_audio.write(chunk)
                temp_audio_path = temp_audio.name
            try:
                with open(temp_audio_path, 'rb') as audio:
                    transcript = client.audio.transcriptions.create(model="whisper-1", file=audio, language="en")
                prompt_text = transcript.text
                logger.info(f"User {user.id} - Transcription for conversation {conversation_id}: '{prompt_text}'")
            except Exception as transcription_error:
                 logger.error(f"User {user.id} - Transcription failed for conversation {conversation_id}: {transcription_error}")
                 prompt_text = "[Audio Transcription Failed]"
                 final_response_text = "Sorry, I couldn't understand the audio. Please try again."
                 interaction_success = False
                 raise transcription_error # Re-raise to save interaction and return

        elif 'text' in request.data:
            prompt_text = request.data['text']
            logger.info(f"User {user.id} - Text input for conversation {conversation_id}: '{prompt_text}'")
        else:
            logger.error(f"User {user.id} - No audio or text provided for conversation {conversation_id}.")
            raise ValueError("Input required (audio or text).")

        if not prompt_text or len(prompt_text.strip()) < 2:
             logger.warning(f"User {user.id} - Prompt too short: '{prompt_text}' for conversation {conversation_id}")
             final_response_text = "Sorry, I couldn't understand that. Please provide more detail."
             interaction_success = False
             # Raise an error to save interaction and return standard error format
             raise ValueError("Prompt too short.")


        # --- Step 2: Manage Conversation History & Context ---
        messages = []
        history_interactions = []

        if conversation_id: # Fetch history only if continuing
            history_limit = 10
            db_interactions = VoiceInteraction.objects.filter(
                user=user,
                conversation_id=conversation_id # Use the validated UUID
            ).order_by('-created_at')[:history_limit]

            if db_interactions:
                 logger.info(f"User {user.id} - Loading {len(db_interactions)} interactions for conversation {conversation_id}")
                 for interaction in reversed(list(db_interactions)):
                    messages.append({"role": "user", "content": interaction.prompt})
                    if interaction.response and interaction.response.strip():
                         messages.append({"role": "assistant", "content": interaction.response})
                 latest_interaction_in_history = db_interactions.first()
                 if latest_interaction_in_history and isinstance(latest_interaction_in_history.reference_context, dict):
                      current_reference_context = latest_interaction_in_history.reference_context
                      logger.debug(f"User {user.id} - Loaded reference context from history: {current_reference_context}")


        # --- Step 3: Prepare OpenAI Request ---
        system_prompt = f"""
        You are Sparkle... (keep your detailed system prompt focusing on file access and context)
        Current Date/Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S %Z')}
        """
        openai_messages = [{"role": "system", "content": system_prompt}] + messages + [{"role": "user", "content": prompt_text}]

        tools = [
            {"type": "function", "function": {"name": "list_files_for_sparkle", "description": "Lists user's files. Can filter by category (e.g., Banking, Personal) or file type/extension (e.g., PDF, Image, DOCX). Use when asked to 'show', 'list', or 'find' files generally or by type/category.", "parameters": {"type": "object", "properties": {"category_name": {"type": "string", "description": "The name of the category to filter by (case-insensitive)."}, "file_type": {"type": "string", "description": "The type or extension of the file to filter by (e.g., PDF, DOCX, Image, JPG)."}}, "required": []}}},
            {"type": "function", "function": {"name": "search_files_for_sparkle", "description": "Searches for files based on a keyword within their name or text content (from OCR). Use when asked to 'search for', 'find files containing', or similar keyword-based queries.", "parameters": {"type": "object", "properties": {"keyword": {"type": "string", "description": "The keyword to search for (should be at least 3 characters)."}}, "required": ["keyword"]}}},
            {"type": "function", "function": {"name": "summarize_file_for_sparkle", "description": "Summarizes the text content of a specific file identified by its exact name or unique ID. Use when asked to 'summarize', 'give key points of', or 'tell me about' a specific file.", "parameters": {"type": "object", "properties": {"file_name_or_id": {"type": "string", "description": "The exact file name (case-insensitive) or the numeric file ID of the file to summarize."}}, "required": ["file_name_or_id"]}}},
            {"type": "function", "function": {"name": "get_file_details_for_display", "description": "Gets details and a secure temporary URL to display a specific file identified by its exact name or ID. ALWAYS use this tool when the user asks to 'show', 'display', 'open', 'view', 'access', 'give link to', or 'get' a specific file. This is the ONLY way to provide a file URL to the user.", "parameters": {"type": "object", "properties": {"file_name_or_id": {"type": "string", "description": "The exact file name (case-insensitive) or the numeric file ID of the file to display."}}, "required": ["file_name_or_id"]}}},
            {"type": "function", "function": {"name": "rename_file_for_sparkle", "description": "Renames a specific file.", "parameters": {"type": "object", "properties": {"file_name_or_id": {"type": "string", "description": "The current exact name or ID of the file."}, "new_name": {"type": "string", "description": "The desired new name for the file (including extension if applicable)."}}, "required": ["file_name_or_id", "new_name"]}}},
            {"type": "function", "function": {"name": "delete_file_for_sparkle", "description": "Deletes a specific file permanently.", "parameters": {"type": "object", "properties": {"file_name_or_id": {"type": "string", "description": "The exact name or ID of the file to delete."}}, "required": ["file_name_or_id"]}}},
            {"type": "function", "function": {"name": "move_file_for_sparkle", "description": "Moves a specific file to a different category/folder.", "parameters": {"type": "object", "properties": {"file_name_or_id": {"type": "string", "description": "The exact name or ID of the file to move."}, "target_category_name": {"type": "string", "description": "The name of the category/folder to move the file into."}}, "required": ["file_name_or_id", "target_category_name"]}}},
            {"type": "function", "function": {"name": "share_file_for_sparkle", "description": "Generates a temporary shareable link for a specific file.", "parameters": {"type": "object", "properties": {"file_name_or_id": {"type": "string", "description": "The exact name or ID of the file to share."}}, "required": ["file_name_or_id"]}}},
            {"type": "function", "function": {"name": "create_folder_for_sparkle", "description": "Creates a new folder/category for organizing files.", "parameters": {"type": "object", "properties": {"folder_name": {"type": "string", "description": "The name for the new folder/category."}}, "required": ["folder_name"]}}},
            {"type": "function", "function": {"name": "get_storage_info_for_sparkle", "description": "Gets the current storage usage information for the user. Use when asked about storage space, storage usage, or storage limits.", "parameters": {"type": "object", "properties": {}, "required": []}}},
        ]

        # --- Step 4: First OpenAI Call ---
        logger.info(f"User {user.id} - Calling OpenAI (pass 1) for conversation {conversation_id}. Messages: {len(openai_messages)}")
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=openai_messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.2
        )

        # --- Step 5: Process Tool Calls (if any) ---
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls if hasattr(response_message, 'tool_calls') else None

        if tool_calls:
            openai_messages.append(response_message)
            logger.info(f"User {user.id} - OpenAI requested {len(tool_calls)} tool call(s) for conversation {conversation_id}")
            tool_outputs = []
            function_executed_successfully = True # Assume success for this stage unless a tool fails

            for tool_call in tool_calls:
                function_name = tool_call.function.name
                tool_call_id = tool_call.id
                tool_json_response = None
                temp_file_obj = None

                try:
                    function_args = json.loads(tool_call.function.arguments)
                    logger.info(f"User {user.id} - Executing tool: {function_name} with args: {function_args}")

                    # --- Execute Local Helper Function (Pass context) ---
                    if function_name == "get_file_details_for_display":
                        tool_json_response, temp_file_obj = get_file_details_for_display(user, function_args.get("file_name_or_id"), current_reference_context)
                    elif function_name == "list_files_for_sparkle":
                        tool_json_response, temp_file_obj = list_files_for_sparkle(user, function_args.get("category_name"), function_args.get("file_type")), None
                    elif function_name == "summarize_file_for_sparkle":
                            tool_json_response, temp_file_obj = summarize_file_for_sparkle(user, function_args.get("file_name_or_id"), current_reference_context)
                    elif function_name == "rename_file_for_sparkle":
                            tool_json_response, temp_file_obj = rename_file_for_sparkle(user, function_args.get("file_name_or_id"), function_args.get("new_name"), current_reference_context)
                    elif function_name == "delete_file_for_sparkle":
                            tool_json_response, temp_file_obj = delete_file_for_sparkle(user, function_args.get("file_name_or_id"), current_reference_context) # temp_file_obj is None
                    elif function_name == "move_file_for_sparkle":
                            tool_json_response, temp_file_obj = move_file_for_sparkle(user, function_args.get("file_name_or_id"), function_args.get("target_category_name"), current_reference_context)
                    elif function_name == "share_file_for_sparkle":
                            tool_json_response, temp_file_obj = share_file_for_sparkle(user, function_args.get("file_name_or_id"), current_reference_context)
                    elif function_name == "create_folder_for_sparkle":
                            tool_json_response, temp_file_obj = create_folder_for_sparkle(user, function_args.get("folder_name")), None
                    elif function_name == "get_storage_info_for_sparkle":
                            tool_json_response, temp_file_obj = get_storage_info_for_sparkle(user), None
                    else:
                        logger.warning(f"User {user.id} - Unknown function call requested: {function_name}")
                        tool_json_response = json.dumps({"success": False, "error": "Unknown function"})

                    # Process helper result
                    if tool_json_response:
                        tool_outputs.append({"tool_call_id": tool_call_id, "role": "tool", "name": function_name, "content": tool_json_response})
                        try:
                            result_data = json.loads(tool_json_response)
                            if not result_data.get('success', False):
                                function_executed_successfully = False
                            if temp_file_obj:
                                 operated_file_object = temp_file_obj # Store file for context update
                            if function_name == "get_file_details_for_display" and result_data.get('success'):
                                 action_payload = result_data
                                 action_payload['type'] = 'display_file'
                                 logger.info(f"User {user.id} - Captured action_payload for display_file")
                        except json.JSONDecodeError:
                            logger.error(f"User {user.id} - Failed to parse JSON from tool {function_name}")
                            function_executed_successfully = False
                    else:
                         logger.error(f"User {user.id} - Tool {function_name} returned None or empty response.")
                         tool_outputs.append({"tool_call_id": tool_call_id, "role": "tool", "name": function_name, "content": json.dumps({"success": False, "error": "Function execution failed."})})
                         function_executed_successfully = False

                except json.JSONDecodeError:
                    logger.error(f"User {user.id} - Invalid JSON args for {function_name}: {tool_call.function.arguments}")
                    tool_outputs.append({"tool_call_id": tool_call_id, "role": "tool", "name": function_name, "content": json.dumps({"success": False, "error": "Invalid arguments."})})
                    function_executed_successfully = False
                except Exception as tool_error:
                    logger.exception(f"User {user.id} - Error executing tool {function_name}: {tool_error}")
                    tool_outputs.append({"tool_call_id": tool_call_id, "role": "tool", "name": function_name, "content": json.dumps({"success": False, "error": str(tool_error)})})
                    function_executed_successfully = False

            # --- Step 6: Second OpenAI Call (if tools were called) ---
            if tool_outputs:
                openai_messages.extend(tool_outputs)
                logger.info(f"User {user.id} - Calling OpenAI (pass 2) for conversation {conversation_id} with {len(tool_outputs)} tool results.")
                try:
                    final_response = client.chat.completions.create(
                        model="gpt-4-turbo", messages=openai_messages, temperature=0.2
                    )
                    final_response_text = final_response.choices[0].message.content
                    logger.debug(f"User {user.id} - Final OpenAI response: {final_response_text[:200]}...")

                    # --- URL Verification ---
                    if action_payload and action_payload.get('fileUrl') and action_payload['fileUrl'] not in final_response_text:
                            logger.warning(f"User {user.id} - URL missing from final response for '{action_payload.get('fileName')}'. Appending.")
                            final_response_text += f"\n\nView File: {action_payload['fileUrl']}"

                except Exception as openai_error:
                    logger.exception(f"User {user.id} - OpenAI API Error (pass 2): {openai_error}")
                    final_response_text = "I performed the action, but encountered an issue generating the final explanation."
                    # Use tool result text if available and successful
                    if function_executed_successfully and action_payload and action_payload.get('result'):
                         final_response_text = action_payload.get('result')
                    interaction_success = False # Mark overall as failed due to OpenAI error

        else:
            # No tool calls needed
            final_response_text = response_message.content if response_message and response_message.content else "I'm ready for your next command."
            interaction_success = bool(final_response_text and final_response_text != "I'm ready for your next command.")
            logger.info(f"User {user.id} - No tool calls needed. Direct response for conversation {conversation_id}.")


        # --- Step 7: Generate Audio ---
        if final_response_text:
            audio_url = generate_audio_if_requested(request, final_response_text, interaction=None)


        # --- Step 8: Update Reference Context ---
        if operated_file_object: # Only update if a specific file was successfully acted upon
             current_reference_context = update_reference_context(current_reference_context, operated_file_object)
             logger.info(f"User {user.id} - Updated context for conversation {conversation_id}")


        # --- Step 9: Save Interaction ---
        # Determine overall success based on both OpenAI and function execution
        interaction_success = function_executed_successfully and bool(final_response_text)

        interaction = VoiceInteraction.objects.create(
            user=user,
            prompt=prompt_text,
            response=final_response_text or "[No Response Text]",
            audio_response_url=audio_url,
            success=interaction_success,
            conversation_id=conversation_id,
            reference_context=current_reference_context
        )
        logger.info(f"User {user.id} - Saved interaction {interaction.id} for conversation {conversation_id}")


        # --- Step 10: Format and Return Response ---
        response_data = {
            'prompt': prompt_text,
            'response': final_response_text,
            'audio_url': audio_url,
            'interaction_id': interaction.id,
            'interaction_success': interaction_success,
            'conversation_id': str(conversation_id),
            'action': action_payload # Include payload if a display action occurred
        }
        if action_payload and action_payload.get('type') == 'display_file':
            response_data['file_details'] = { # Add consistent file_details block
                'success': action_payload.get('success', False),
                'fileUrl': action_payload.get('fileUrl'),
                'fileName': action_payload.get('fileName'),
                'fileType': action_payload.get('fileType'),
                'fileId': action_payload.get('fileId')
            }

        return Response({'success': True, 'data': response_data}) # API call itself succeeded

    except Exception as e:
        # --- Global Error Handling ---
        logger.exception(f"User {user.id} - Unhandled error in process_voice_api for conversation {conversation_id}: {e}")
        error_response_text = "Sorry, an unexpected error occurred while processing your request."
        interaction_id_for_error = None
        try:
            # Use determined conversation_id, fallback to new if error happened early
            conv_id_for_error = conversation_id if 'conversation_id' in locals() and conversation_id else uuid.uuid4()
            interaction = VoiceInteraction.objects.create(
                user=user,
                prompt=prompt_text if 'prompt_text' in locals() else "[Input Unavailable]",
                response=f"Error: {e}", # Log specific error internally
                success=False,
                conversation_id=conv_id_for_error,
                reference_context=current_reference_context # Save context state
            )
            interaction_id_for_error = interaction.id
        except Exception as log_error:
            logger.error(f"Failed to save error interaction for conversation {conv_id_for_error if 'conv_id_for_error' in locals() else 'Unknown'}: {log_error}")

        return Response(
             {'success': False, # API call itself failed
              'error': error_response_text,
              'data': { # Provide some data for debugging if possible
                   'prompt': prompt_text if 'prompt_text' in locals() else None,
                   'response': error_response_text,
                   'audio_url': None,
                   'interaction_id': interaction_id_for_error,
                   'interaction_success': False,
                   'conversation_id': str(conv_id_for_error if 'conv_id_for_error' in locals() else conversation_id),
                   'action': None,
                   'file_details': None
              }},
             status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        # --- Cleanup ---
        if temp_audio_path and os.path.exists(temp_audio_path):
            try: os.remove(temp_audio_path)
            except Exception as cleanup_error: logger.error(f"Error cleaning input audio file {temp_audio_path}: {cleanup_error}")

def force_open_file(user, query):
    """
    Force-open a file based on query, completely bypassing LLM.
    Returns (success, response_text, action_payload)
    """
    query_lower = query.lower()
    file_found = None
    file_keywords = ["file", "document", "pdf", "docx", "image", "picture", "doc"]
    open_keywords = ["open", "show", "display", "view", "give", "access", "link"]
    
    # Only proceed if this looks like a file opening request
    if not any(k in query_lower for k in open_keywords):
        return False, None, None
        
    # Extract potential filename by removing opening keywords and file type references
    clean_query = query_lower
    for word in open_keywords + ["me", "for", "to", "the"]:
        clean_query = clean_query.replace(word, " ")
    for word in file_keywords:
        clean_query = clean_query.replace(word, " ")
        
    # Clean up extra spaces
    clean_query = re.sub(r'\s+', ' ', clean_query).strip()
    if len(clean_query) < 3:
        return False, None, None
    
    # Handle camelCase and remove spaces - create alternative query formats
    query_variations = [clean_query]
    
    # Add a variation with spaces removed (e.g., "my document" -> "mydocument")
    no_spaces_query = clean_query.replace(" ", "")
    if no_spaces_query != clean_query:
        query_variations.append(no_spaces_query)
    
    # Try to split camelCase (e.g., "CGProjectPlanes" -> "cg project planes")
    camel_case_pattern = re.compile(r'((?<=[a-z])[A-Z]|(?<!\A)[A-Z](?=[a-z]))')
    camel_split_query = camel_case_pattern.sub(r' \1', clean_query).lower()
    if camel_split_query != clean_query:
        query_variations.append(camel_split_query)
        
    # Add joined variations without spaces to better handle combined terms
    if " " in clean_query:
        query_variations.append("".join(clean_query.split()))
    
    logger.info(f"Force-opening file attempt with extracted queries: {query_variations}")
    
    # Try to find the file
    potential_matches = []
    all_files = UserFile.objects.filter(user=user).order_by('-upload_date')
    
    # First look for exact or contains matches
    for file in all_files:
        filename_lower = file.original_filename.lower()
        highest_match_weight = 0
        
        # Try each query variation
        for query_var in query_variations:
            # Check for exact match first
            if query_var == filename_lower:
                file_found = file
                break
                
            # Check for contains match - prioritize files that contain the query
            elif query_var in filename_lower:
                match_weight = 2
                # Prefer matches where the query is closer to the full filename length
                similarity_ratio = len(query_var) / len(filename_lower)
                if similarity_ratio > 0.5:  # If query is at least 50% of filename length
                    match_weight += 1
                    
                highest_match_weight = max(highest_match_weight, match_weight)
            else:
                # Check individual words
                search_terms = query_var.split()
                word_match_weight = 0
                for term in search_terms:
                    if len(term) > 2 and term in filename_lower:
                        word_match_weight += 1
                highest_match_weight = max(highest_match_weight, word_match_weight)
                
        # Add to potential matches if any variation matched
        if highest_match_weight > 0:
            potential_matches.append((file, highest_match_weight))
            
        # Break early if exact match found
        if file_found:
            break
    
    # Sort potential matches by weight
    if not file_found and potential_matches:
        potential_matches.sort(key=lambda x: x[1], reverse=True)
        file_found = potential_matches[0][0]
    
    # If file found, generate URL and response
    if file_found:
        try:
            # Get file URL
            storage_manager = S3StorageManager(user)
            file_url = storage_manager.generate_download_url(file_found.s3_key, expires_in=3600)
            
            # Format nice response
            result_message = f"""
Here's the file you requested:

File: {file_found.original_filename}
Category: {file_found.category.name if file_found.category else "Uncategorized"}
Type: {file_found.get_file_type_display() if hasattr(file_found, 'get_file_type_display') else file_found.file_type}
Uploaded: {file_found.upload_date.strftime("%B %d, %Y")}

Direct Link: {file_url}
            """
            
            # Create action payload structure
            action_payload = {
                "success": True,
                "file_id": file_found.id,
                "fileId": file_found.id,
                "file_name": file_found.original_filename,
                "fileName": file_found.original_filename,
                "file_type": file_found.file_type,
                "fileType": file_found.file_type,
                "category": file_found.category.name if file_found.category else "Uncategorized",
                "upload_date": file_found.upload_date.strftime("%Y-%m-%d"),
                "uploadDate": file_found.upload_date.strftime("%Y-%m-%d"),
                "file_url": file_url,
                "fileUrl": file_url
            }
            
            return True, result_message, action_payload
            
        except Exception as e:
            logger.exception(f"Error in force_open_file: {e}")
            
    return False, None, None

def detect_file_open_intent(query):
    """
    Detect if the user's query indicates intent to open a file.
    Returns True if file opening intent is detected.
    """
    query_lower = query.lower()
    open_keywords = ["open", "show", "display", "view", "see", "get", "access", "link", "open up", "pull up"]
    file_keywords = ["file", "document", "pdf", "docx", "image", "picture", "photo", "spreadsheet", "presentation"]
    
    # Check for common patterns
    # Pattern 1: "open/show/etc. [the/my/etc.] file"
    for open_word in open_keywords:
        for file_word in file_keywords:
            patterns = [
                f"{open_word} {file_word}",
                f"{open_word} the {file_word}",
                f"{open_word} my {file_word}",
                f"{open_word} that {file_word}",
                f"{open_word} this {file_word}",
            ]
            if any(pattern in query_lower for pattern in patterns):
                return True
    
    # Pattern 2: Direct references to "this" or "that"
    reference_patterns = [
        "open this", "show this", "display this", "view this",
        "open that", "show that", "display that", "view that",
        "open it", "show it", "display it", "view it"
    ]
    if any(pattern in query_lower for pattern in reference_patterns):
        return True
    
    # Pattern 3: "can you open/show/etc."
    for open_word in open_keywords:
        prefixes = ["can you ", "could you ", "would you ", "please ", "i want to ", "i'd like to "]
        for prefix in prefixes:
            if f"{prefix}{open_word}" in query_lower:
                return True
    
    return False

def extract_filename_from_prompt(prompt):
    """
    Extract potential filename from a user prompt.
    Returns the potential filename or None if no clear filename is found.
    """
    prompt_lower = prompt.lower()
    
    # Define patterns to find filenames
    # Pattern 1: after "open/show/display/etc." keywords
    open_keywords = ["open", "show", "display", "view", "see", "get", "access", "link to"]
    file_keywords = ["file", "document", "pdf", "docx", "image", "picture", "photo"]
    called_keywords = ["called", "named", "titled"]
    
    # Try to extract after "open X" where X is the filename
    for keyword in open_keywords:
        if keyword in prompt_lower:
            # Find the position of the keyword
            pos = prompt_lower.find(keyword) + len(keyword)
            
            # Skip articles and other words
            skip_words = ["the", "my", "a", "this", "that", "your", "to", "me"]
            for skip in skip_words:
                if prompt_lower[pos:].strip().startswith(skip + " "):
                    pos += len(skip) + 1
            
            # Skip file type words
            for file_type in file_keywords:
                if prompt_lower[pos:].strip().startswith(file_type + " "):
                    pos += len(file_type) + 1
            
            # Handle "called/named" constructs
            for called in called_keywords:
                if prompt_lower[pos:].strip().startswith(called + " "):
                    pos += len(called) + 1
            
            # Extract the filename - up to end or punctuation
            filename_part = prompt[pos:].strip()
            # Find first punctuation
            punctuation_pos = len(filename_part)
            for punct in ['.', ',', '?', '!', ';']:
                pos_punct = filename_part.find(punct)
                if pos_punct > 0 and pos_punct < punctuation_pos:
                    punctuation_pos = pos_punct
            
            filename = filename_part[:punctuation_pos].strip()
            
            # If filename looks reasonable (not too short), return it
            if len(filename) >= 2:
                return filename
    
    # Pattern 2: Check for reference terms like "this", "that", etc.
    reference_terms = ["this", "that", "it", "the file", "the document"]
    for term in reference_terms:
        if term in prompt_lower:
            return term
    
    # If no clear filename found, return None
    return None

def handle_direct_file_opening(user, file_obj, reference_context=None):
    """
    Handle opening a file directly.
    
    Args:
        user: User requesting the file
        file_obj: File object to open
        reference_context: Optional reference context to update
        
    Returns:
        (success, message, payload)
    """
    if not file_obj:
        return False, None, None
        
    try:
        # Get file URL
        storage_manager = S3StorageManager(user)
        file_url = None
        
        # Try multiple methods to get a valid URL
        try:
            file_url = storage_manager.generate_download_url(file_obj.s3_key, expires_in=3600)
        except Exception as e1:
            logger.warning(f"First URL generation method failed: {e1}")
            
            try:
                file_url = storage_manager.get_file_url(file_obj.s3_key, expiry=3600)
            except Exception as e2:
                logger.warning(f"Second URL generation method failed: {e2}")
                
                try:
                    file_url = s3_client.generate_presigned_url(
                        'get_object',
                        Params={
                            'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                            'Key': file_obj.s3_key
                        },
                        ExpiresIn=3600
                    )
                except Exception as e3:
                    logger.warning(f"Third URL generation method failed: {e3}")
        
        if not file_url:
            return False, "I'm sorry, I couldn't generate a URL to view this file.", None
            
        # Format nice response
        result_message = f"""
Here's the file you requested:

File: {file_obj.original_filename}
Category: {file_obj.category.name if file_obj.category else "Uncategorized"}
Type: {file_obj.get_file_type_display() if hasattr(file_obj, 'get_file_type_display') else file_obj.file_type}
Uploaded: {file_obj.upload_date.strftime("%B %d, %Y")}

Direct Link: {file_url}
        """
        
        # Create action payload structure with all possible URL fields for maximum compatibility
        action_payload = {
            "success": True,
            "file_id": file_obj.id,
            "fileId": file_obj.id,
            "file_name": file_obj.original_filename,
            "fileName": file_obj.original_filename,
            "file_type": file_obj.file_type,
            "fileType": file_obj.file_type,
            "category": file_obj.category.name if file_obj.category else "Uncategorized",
            "upload_date": file_obj.upload_date.strftime("%Y-%m-%d"),
            "uploadDate": file_obj.upload_date.strftime("%Y-%m-%d"),
            "file_url": file_url,
            "fileUrl": file_url,
            "url": file_url,
            "direct_url": file_url
        }
        
        return True, result_message, action_payload
        
    except Exception as e:
        logger.exception(f"Error in handle_direct_file_opening: {e}")
        return False, None, None

def generate_audio_response(user, text, interaction):
    """
    Generate audio response for text using OpenAI TTS.
    
    Args:
        user: User to generate audio for
        text: Text to convert to speech
        interaction: VoiceInteraction object to update with audio URL
        
    Returns:
        Audio URL or None if generation fails
    """
    
    try:
        # Create a temporary file for storing the audio
        temp_response_path = f"/tmp/sparkle_response_{uuid.uuid4()}.mp3"
        
        # Get user voice preferences (with defaults)
        user_settings = getattr(user, 'assistant_settings', None) or {}
        voice_type = user_settings.get('voice_type', 'nova')
        
        # For really long text, truncate to a reasonable limit for TTS
        tts_text = text
        if len(tts_text) > 4000:
            # If too long, create a summarized version for speech
            tts_text = tts_text[:1000] + "... I've provided more details in the text response."
        
        # Generate audio using OpenAI TTS
        audio_response = client.audio.speech.create(
            model="tts-1",
            voice=voice_type,
            input=tts_text
        )
        
        # Stream to file
        audio_response.stream_to_file(temp_response_path)
        
        # Set up S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        
        # Get base filename (without path)
        s3_filename = f"media/voice_responses/response_{uuid.uuid4()}.mp3"
        
        # Upload to S3
        with open(temp_response_path, "rb") as audio_file:
            s3_client.upload_fileobj(
                audio_file,
                settings.AWS_STORAGE_BUCKET_NAME,
                s3_filename
            )
        
        # Generate presigned URL
        audio_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                'Key': s3_filename
            },
            ExpiresIn=3600  # URL valid for 1 hour
        )
        
        # Update interaction with audio URL
        interaction.audio_response_url = audio_url
        interaction.save()
        
        logger.info(f"Generated audio response for interaction {interaction.id}, URL: {audio_url}")
        
    except Exception as tts_error:
        logger.warning(f"Error generating audio response: {tts_error}")
        audio_url = None
    
    finally:
        # Clean up temporary file
        if temp_response_path and os.path.exists(temp_response_path):
            try:
                os.remove(temp_response_path)
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up temporary audio file: {cleanup_error}")
    
    return audio_url



@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def direct_file_open_api(request):
    """
    Direct file opening API endpoint that bypasses all AI processing.
    Intended as a fallback for the frontend to call if the main API response indicates
    file opening intent but doesn't provide a proper file URL.
    
    Request body should contain:
    - file_reference: Name or ID of the file to open
    """
    try:
        # Get file reference from request
        file_reference = request.data.get('file_reference')
        
        if not file_reference:
            return Response({
                'success': False,
                'error': 'No file reference provided'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        logger.info(f"User {request.user.id} - FALLBACK API: Direct file open for '{file_reference}'")
        
        # Find the file using our best matching algorithm
        file = find_file_by_name_or_id(user=request.user, file_name_or_id=file_reference, operation_name="fallback_api")
        
        if not file:
            return Response({
                'success': False,
                'error': f"Couldn't find a file matching '{file_reference}'",
                'fallback_files': [
                    {
                        'id': f.id, 
                        'name': f.original_filename,
                        'type': f.file_type,
                        'category': f.category.name if f.category else "Uncategorized"
                    } 
                    for f in UserFile.objects.filter(user=request.user).order_by('-upload_date')[:5]
                ]
            }, status=status.HTTP_404_NOT_FOUND)
            
        # Generate URL for the file
        storage_manager = S3StorageManager(request.user)
        file_url = storage_manager.generate_download_url(file.s3_key, expires_in=3600)
        
        return Response({
            'success': True,
            'file_data': {
                'id': file.id,
                'name': file.original_filename,
                'type': file.file_type,
                'category': file.category.name if file.category else "Uncategorized",
                'url': file_url,
                'upload_date': file.upload_date.strftime("%Y-%m-%d")
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.exception(f"User {request.user.id} - FALLBACK API: Error: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def handle_direct_file_opening(user, file_obj, reference_context=None):
    """Handle opening a file directly, returns (success, message, payload)"""
    if not file_obj:
        return False, None, None
        
    try:
        # Get file URL
        storage_manager = S3StorageManager(user)
        file_url = None
        
        # Try multiple methods to get a valid URL
        try:
            file_url = storage_manager.generate_download_url(file_obj.s3_key, expires_in=3600)
        except Exception as e1:
            logger.warning(f"First URL generation method failed: {e1}")
            
            try:
                file_url = storage_manager.get_file_url(file_obj.s3_key, expiry=3600)
            except Exception as e2:
                logger.warning(f"Second URL generation method failed: {e2}")
                
                try:
                    file_url = s3_client.generate_presigned_url(
                        'get_object',
                        Params={
                            'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                            'Name': file_obj.s3_key
                        },
                        ExpiresIn=3600
                    )
                except Exception as e3:
                    logger.warning(f"Third URL generation method failed: {e3}")
        
        if not file_url:
            return False, "I'm sorry, I couldn't generate a URL to view this file.", None
            
        # Format nice response
        result_message = f"""
Here's the file you requested:

File: {file_obj.original_filename}
Category: {file_obj.category.name if file_obj.category else "Uncategorized"}
Type: {file_obj.get_file_type_display() if hasattr(file_obj, 'get_file_type_display') else file_obj.file_type}
Uploaded: {file_obj.upload_date.strftime("%B %d, %Y")}
"""
        
        # Create action payload structure with all possible URL fields for maximum compatibility
        action_payload = {
            "success": True,
            "file_id": file_obj.id,
            "fileId": file_obj.id,
            "file_name": file_obj.original_filename,
            "fileName": file_obj.original_filename,
            "file_type": file_obj.file_type,
            "fileType": file_obj.file_type,
            "category": file_obj.category.name if file_obj.category else "Uncategorized",
            "upload_date": file_obj.upload_date.strftime("%Y-%m-%d"),
            "uploadDate": file_obj.upload_date.strftime("%Y-%m-%d"),
            "file_url": file_url,
            "fileUrl": file_url,
            "url": file_url,
            "direct_url": file_url
        }
        
        return True, result_message, action_payload
        
    except Exception as e:
        logger.exception(f"Error in handle_direct_file_opening: {e}")
        return False, None, None

def generate_audio_if_requested(request, text, interaction):
    """Generate audio response if requested and update interaction."""
    audio_url = None
    include_audio_response = request.data.get('include_audio') == 'true'
    user = request.user

    if include_audio_response and text:
        try:
            temp_response_path = f"/tmp/sparkle_response_{uuid.uuid4()}.mp3"
            
            # Handle users without assistant_settings attribute
            voice_type = 'nova'  # Default voice
            try:
                # Safely check for assistant_settings
                if hasattr(user, 'assistant_settings') and user.assistant_settings:
                    voice_type = user.assistant_settings.get('voice_type', 'nova')
            except AttributeError:
                # Log the issue but continue with default voice
                logger.info(f"User {getattr(user, 'id', 'unknown')} has no assistant_settings, using default voice")
            
            # Ensure text isn't too long for TTS
            tts_text = text
            if len(tts_text) > 4000:
                # If too long, create a summarized version for speech
                tts_text = tts_text[:1000] + "... I've provided more details in the text response."
            
            # Generate the audio
            audio_response = client.audio.speech.create(
                model="tts-1",
                voice=voice_type,
                input=tts_text
            )
            audio_response.stream_to_file(temp_response_path)

            # Generate a unique S3 path that won't conflict between users
            # Use username if available, otherwise a random string
            user_identifier = getattr(user, 'username', str(uuid.uuid4()))
            s3_filename = f"audio-responses/{user_identifier}/{uuid.uuid4()}.mp3"
            
            with open(temp_response_path, "rb") as audio_file:
                s3_client.upload_fileobj(
                    audio_file,
                    settings.AWS_STORAGE_BUCKET_NAME,
                    s3_filename
                )

            audio_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': settings.AWS_STORAGE_BUCKET_NAME, 'Key': s3_filename},
                ExpiresIn=3600
            )

            # If interaction object is provided, update it directly
            if interaction:
                interaction.audio_response_url = audio_url
                # Don't save here, let the main view save it after all updates
            
            logger.info(f"User {getattr(user, 'id', 'unknown')} - Generated TTS audio URL: {audio_url[:100]}...")

        except Exception as tts_error:
            logger.warning(f"User {getattr(user, 'id', 'unknown')} - TTS generation failed: {tts_error}")
            audio_url = None  # Ensure it's None on failure
        finally:
            if 'temp_response_path' in locals() and os.path.exists(temp_response_path):
                try: 
                    os.remove(temp_response_path)
                except Exception as cleanup_error: 
                    logger.error(f"Error cleaning TTS file: {cleanup_error}")

    return audio_url

