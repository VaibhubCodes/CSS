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
from views import *

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_voice_api(request):
    """Processes voice input (audio) or text input for the Sparkle assistant using Function Calling."""
    serializer = VoiceCommandSerializer(data=request.data)
    if not serializer.is_valid():
        logger.warning(f"User {request.user.id} - Invalid input data for process_voice_api: {serializer.errors}")
        return Response({'success': False, 'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    prompt_text = None
    temp_audio_path = None
    include_audio_response = request.data.get('include_audio', 'true').lower() == 'true' # Check request for audio flag
    
    # Get conversation_id if provided to continue previous conversation
    conversation_id = serializer.validated_data.get('conversation_id')
    
    try:
        # --- Step 1: Get Text Input ---
        if audio_file := serializer.validated_data.get('audio'):
            logger.info(f"User {request.user.id} - Processing audio input...")
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_audio:
                for chunk in audio_file.chunks(): temp_audio.write(chunk)
                temp_audio_path = temp_audio.name
            with open(temp_audio_path, 'rb') as audio:
                transcript = client.audio.transcriptions.create(model="whisper-1", file=audio, language="en")
            prompt_text = transcript.text
            logger.info(f"User {request.user.id} - Transcription: '{prompt_text}'")
        elif text_input := serializer.validated_data.get('text'):
            prompt_text = text_input
            logger.info(f"User {request.user.id} - Text input: '{prompt_text}'")
        else:
            logger.error(f"User {request.user.id} - No audio or text provided.")
            return Response({'success': False, 'error': 'No input provided.'}, status=status.HTTP_400_BAD_REQUEST)

        if not prompt_text or len(prompt_text.strip()) < 2:
             logger.warning(f"User {request.user.id} - Prompt too short: '{prompt_text}'")
             interaction = VoiceInteraction.objects.create(user=request.user, prompt=prompt_text, response="Input too short.", success=False)
             return Response({'success': True, 'data': {'prompt': prompt_text, 'response': "Sorry, I couldn't understand that.", 'audio_url': None, 'interaction_success': False, 'interaction_id': interaction.id}})

        # --- Retrieve Previous Conversation Context ---
        reference_context = {}
        if conversation_id:
            # Get the most recent interaction for this conversation
            previous_interactions = VoiceInteraction.objects.filter(
                user=request.user,
                conversation_id=conversation_id
            ).order_by('-created_at')[:5]  # Get last 5 interactions
            
            # Collect all reference_context data from previous interactions
            for interaction in previous_interactions:
                if interaction.reference_context:
                    # Merge with existing reference_context, giving priority to more recent interactions
                    reference_context.update(interaction.reference_context)
                    
            logger.info(f"User {request.user.id} - Loaded reference context from conversation {conversation_id}: {len(reference_context.keys())} references")

        # --- Check for Direct File Opening Intent ---
        # Analyze the prompt for file opening intent
        is_file_open_intent = detect_file_open_intent(prompt_text)
        
        if is_file_open_intent:
            # Extract potential filename from the prompt
            potential_filename = extract_filename_from_prompt(prompt_text)
            
            if potential_filename:
                logger.info(f"User {request.user.id} - Detected file open intent for: '{potential_filename}'")
                
                # Try to find the file using the enhanced reference resolution
                file_obj = find_file_by_name_or_id(
                    user=request.user,
                    file_name_or_id=potential_filename,
                    operation_name="file_open_intent",
                    reference_context=reference_context,
                    conversation_id=conversation_id
                )
                
                if file_obj:
                    # Successfully found the file - generate a direct file response
                    successful, result_text, action_payload = handle_direct_file_opening(
                        request.user, file_obj, reference_context
                    )
                    
                    if successful:
                        # Update reference context with this file
                        updated_ref_context = update_reference_context(reference_context, file_obj)
                        
                        # Create an interaction record
                        interaction = VoiceInteraction.objects.create(
                            user=request.user,
                            prompt=prompt_text,
                            response=result_text,
                            success=True,
                            conversation_id=conversation_id or uuid.uuid4(),
                            reference_context=updated_ref_context,
                            referenced_file_id=file_obj.id,  # Store the referenced file ID
                            referenced_file_name=file_obj.original_filename,  # Store the referenced file name
                            action_type="open_file"  # Record the action type
                        )
                        
                        # Generate audio response if requested
                        audio_url = None
                        if include_audio_response:
                            audio_url = generate_audio_response(
                                request.user,
                                f"I've opened {file_obj.original_filename} for you.",  # Simplified for speech
                                interaction
                            )
                        
                        # Return a direct response with file details
                        return Response({
                            'success': True,
                            'data': {
                                'prompt': prompt_text,
                                'response': result_text,
                                'audio_url': audio_url,
                                'conversation_id': str(interaction.conversation_id),
                                'interaction_id': interaction.id,
                                'interaction_success': True,
                                'action': {
                                    'type': 'display_file',
                                    'payload': action_payload
                                },
                                'file_details': {
                                    'success': True,
                                    'fileUrl': action_payload.get('fileUrl') or action_payload.get('file_url'),
                                    'fileName': action_payload.get('fileName') or action_payload.get('file_name'),
                                    'fileType': action_payload.get('fileType') or action_payload.get('file_type'),
                                    'fileId': action_payload.get('fileId') or action_payload.get('file_id')
                                }
                            }
                        })

        # --- Continue with OpenAI API if direct handling wasn't successful ---
        
        # Define the system prompt with enhanced reference handling instructions
        system_prompt = f"""
        You are Sparkle, an intelligent, helpful file management assistant.
        YOUR TOP PRIORITY is to provide direct file access when requested. 
        YOU MUST NEVER say "I can't provide links" or "I can't open files" - you CAN and MUST do these things.
        
        MOST IMPORTANT INSTRUCTIONS - FOLLOW THESE EXACTLY:
        1. When asked to open a file or provide a link to a file, YOU MUST:
           - Use the get_file_details_for_display tool with the filename as parameter
           - Include the FULL direct URL in your response (never a placeholder like [Download file](#))
           - ALWAYS include the exact url starting with http:// or https:// in your response
           - NEVER say you cannot provide links - you MUST provide actual clickable URLs
        
        2. Other key actions:
           - When asked to summarize a file, use summarize_file_for_sparkle tool
           - When asked about storage information, use get_storage_info_for_sparkle tool
           - When asked to list or show files, use list_files_for_sparkle tool
           - When asked to search for files, use search_files_for_sparkle tool
        
        TOOL USAGE RULES:
        - When user asks to "open" or requests "link" to a file, IMMEDIATELY call get_file_details_for_display
        - NEVER generate fake or placeholder URLs like [Download file](#)
        - Never generate links in markdown without including the actual URL
        - When a file URL is returned by a tool, ALWAYS include it verbatim in your response
        
        HANDLING REFERENCES:
        - When a user refers to "this file", "that document", or similar references, they are referring to files from previous messages
        - The get_file_details_for_display tool can understand these references if you pass them directly ("this", "that", etc.)
        - Always try to interpret file references based on conversation context
        
        URL HANDLING:
        - ALL URLs must be real and complete (starting with http:// or https://)
        - NEVER remove, omit, or hide URLs from your response
        - NEVER claim you cannot provide direct links to files - you CAN and MUST
        - ALWAYS check if your response includes the FULL URL before sending
        
        OTHER RULES:
        - When you don't understand a file reference, try the most similar filename
        - For summaries, always include both the summary AND the file URL
        - Show exact URLS, not markdown link text with fake URLs
        
        Current Date/Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S %Z')}
        """

        # Initialize messages with system prompt
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history if available
        if conversation_id:
            # Get last few interactions for context
            prev_interactions = VoiceInteraction.objects.filter(
                user=request.user,
                conversation_id=conversation_id
            ).order_by('-created_at')[:5]
            
            # Add them in reverse order (oldest first)
            for interaction in reversed(list(prev_interactions)):
                messages.append({"role": "user", "content": interaction.prompt})
                messages.append({"role": "assistant", "content": interaction.response})
                
        # Add current user message with reference context
        # Create a more detailed prompt that gives context about any referenced files
        enhanced_prompt = prompt_text
        if reference_context:
            # Get details about the most recent referenced file if available
            recent_file_info = ""
            if 'this' in reference_context:
                ref = reference_context['this']
                if isinstance(ref, dict) and 'name' in ref:
                    recent_file_info = f"Previously, you were interacting with file: {ref['name']}"
            
            # Only add context if there's something useful to add
            if recent_file_info:
                enhanced_prompt = f"{recent_file_info}\n\nUser query: {prompt_text}"
        
        messages.append({"role": "user", "content": enhanced_prompt})

        # --- Define Tools for OpenAI Function Calling ---
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

        # --- Execute OpenAI Call ---
        try:
            # Call OpenAI with function calling capability
            logger.info(f"User {request.user.id} - Calling OpenAI with prompt: '{prompt_text}'")
            response = client.chat.completions.create(
                model="gpt-4-turbo",  # Use the latest model for better instruction following
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.2  # Lower temperature for better instruction following
            )
            
            # Validate response structure
            if not hasattr(response, 'choices') or len(response.choices) == 0:
                logger.error(f"User {request.user.id} - Invalid OpenAI response structure: {response}")
                raise ValueError("Invalid response from OpenAI: Missing choices")
                
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls if hasattr(response_message, 'tool_calls') else None
            
            # Process tool calls if present
            final_response_text = None
            function_executed_successfully = None
            file_url_from_tool = None
            file_details = None
            referenced_file_id = None
            referenced_file_name = None
            action_type = None
            updated_reference_context = reference_context.copy() if reference_context else {}
            
            if tool_calls:
                function_executed_successfully = False
                messages.append({"role": "assistant", "content": None, "tool_calls": tool_calls})
                
                # Process each tool call
                for tool_call in tool_calls:
                    try:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)
                        logger.info(f"User {request.user.id} - Function call: {function_name} with args: {function_args}")
                        
                        # Track the action type
                        if function_name == "get_file_details_for_display":
                            action_type = "open_file"
                        elif function_name == "list_files_for_sparkle":
                            action_type = "list_files"
                        elif function_name == "search_files_for_sparkle":
                            action_type = "search_files"
                        elif function_name == "summarize_file_for_sparkle":
                            action_type = "summarize_file"
                        elif function_name == "rename_file_for_sparkle":
                            action_type = "rename_file"
                        elif function_name == "delete_file_for_sparkle":
                            action_type = "delete_file"
                        elif function_name == "move_file_for_sparkle":
                            action_type = "move_file"
                        elif function_name == "share_file_for_sparkle":
                            action_type = "share_file"
                        elif function_name == "create_folder_for_sparkle":
                            action_type = "create_folder"
                        elif function_name == "get_storage_info_for_sparkle":
                            action_type = "get_storage_info"
                        
                        # Execute the function
                        tool_response = None
                        
                        # Special handling for file display
                        if function_name == "get_file_details_for_display":
                            # Get the file reference
                            file_reference = function_args.get("file_name_or_id")
                            
                            # Try to find the file with enhanced resolution
                            resolved_file = find_file_by_name_or_id(
                                user=request.user,
                                file_name_or_id=file_reference,
                                operation_name="tool_function_call",
                                reference_context=reference_context,
                                conversation_id=conversation_id
                            )
                            
                            # If file was found, update the reference context
                            if resolved_file:
                                referenced_file_id = resolved_file.id
                                referenced_file_name = resolved_file.original_filename
                                updated_reference_context = update_reference_context(
                                    updated_reference_context, resolved_file
                                )
                            
                            # Run the tool function
                            tool_response = get_file_details_for_display(
                                user=request.user,
                                file_name_or_id=file_reference
                            )
                            
                            # Parse response for file details
                            try:
                                response_obj = json.loads(tool_response)
                                if response_obj.get('success'):
                                    # Get URL from multiple possible fields for robustness
                                    file_url_from_tool = response_obj.get('file_url') or response_obj.get('fileUrl') or response_obj.get('url') or response_obj.get('direct_url')
                                    file_name_from_tool = response_obj.get('file_name') or response_obj.get('fileName')
                                    
                                    if file_url_from_tool and file_name_from_tool:
                                        # If we didn't resolve the file earlier, use the returned file ID
                                        if not referenced_file_id and response_obj.get('file_id'):
                                            referenced_file_id = response_obj.get('file_id')
                                            referenced_file_name = file_name_from_tool
                                        
                                        file_details = {
                                            'name': file_name_from_tool,
                                            'url': file_url_from_tool,
                                            'type': response_obj.get('file_type') or response_obj.get('fileType'),
                                            'category': response_obj.get('category'),
                                            'id': referenced_file_id or response_obj.get('file_id') or response_obj.get('fileId')
                                        }
                                        
                                        # Ensure ALL possible URL and filename fields are set in action_payload
                                        action_payload = {
                                            "success": True,
                                            "file_id": response_obj.get('file_id'),
                                            "fileId": response_obj.get('fileId') or response_obj.get('file_id'),
                                            "file_name": file_name_from_tool,
                                            "fileName": file_name_from_tool,
                                            "file_type": response_obj.get('file_type'),
                                            "fileType": response_obj.get('fileType') or response_obj.get('file_type'),
                                            "file_url": file_url_from_tool,
                                            "fileUrl": file_url_from_tool,
                                            "url": file_url_from_tool,
                                            "direct_url": file_url_from_tool,
                                            "category": response_obj.get('category'),
                                            "upload_date": response_obj.get('upload_date'),
                                            "uploadDate": response_obj.get('uploadDate') or response_obj.get('upload_date')
                                        }
                                        logger.info(f"[Function Call] Created action_payload with URL: {file_url_from_tool}")
                                    else:
                                        logger.warning(f"[Function Call] Missing URL or filename in response: {response_obj}")
                                        action_payload = response_obj  # Use original as fallback
                                else:
                                    logger.warning(f"[Function Call] get_file_details_for_display returned error: {response_obj.get('error')}")
                            except Exception as e:
                                logger.warning(f"Error parsing file details: {e}")
                                logger.warning(f"Original tool response: {tool_response[:200]}...")
                        
                        # Handle other file-related functions
                        elif function_name == "summarize_file_for_sparkle":
                            # Get the file reference
                            file_reference = function_args.get("file_name_or_id")
                            
                            # Try to find the file with enhanced resolution
                            resolved_file = find_file_by_name_or_id(
                                user=request.user,
                                file_name_or_id=file_reference,
                                operation_name="tool_function_call",
                                reference_context=reference_context,
                                conversation_id=conversation_id
                            )
                            
                            # If file was found, update the reference context
                            if resolved_file:
                                referenced_file_id = resolved_file.id
                                referenced_file_name = resolved_file.original_filename
                                updated_reference_context = update_reference_context(
                                    updated_reference_context, resolved_file
                                )
                            
                            # Execute the function
                            tool_response = summarize_file_for_sparkle(
                                user=request.user,
                                file_name_or_id=file_reference
                            )
                            
                            # Parse response to extract file URL if present
                            try:
                                response_obj = json.loads(tool_response)
                                if response_obj.get('success') and response_obj.get('file_url'):
                                    file_url_from_tool = response_obj.get('file_url')
                                    file_details = {
                                        'name': response_obj.get('file_name'),
                                        'url': file_url_from_tool,
                                        'id': response_obj.get('file_id')
                                    }
                                    # If we didn't resolve the file earlier
                                    if not referenced_file_id and response_obj.get('file_id'):
                                        referenced_file_id = response_obj.get('file_id')
                                        referenced_file_name = response_obj.get('file_name')
                            except Exception as e:
                                logger.warning(f"Error parsing summary details: {e}")
                        
                        # Handle rename, move, share files
                        elif function_name in ["rename_file_for_sparkle", "move_file_for_sparkle", "delete_file_for_sparkle", "share_file_for_sparkle"]:
                            # Get the file reference
                            file_reference = function_args.get("file_name_or_id")
                            
                            # Try to find the file with enhanced resolution
                            resolved_file = find_file_by_name_or_id(
                                user=request.user,
                                file_name_or_id=file_reference,
                                operation_name="tool_function_call",
                                reference_context=reference_context,
                                conversation_id=conversation_id
                            )
                            
                            # If file was found, update the reference info
                            if resolved_file:
                                referenced_file_id = resolved_file.id
                                referenced_file_name = resolved_file.original_filename
                                # Note: Don't update reference_context for operations like delete
                            
                            # Execute the function with appropriate arguments
                            if function_name == "rename_file_for_sparkle":
                                tool_response = rename_file_for_sparkle(
                                    user=request.user,
                                    file_name_or_id=file_reference,
                                    new_name=function_args.get("new_name")
                                )
                            elif function_name == "move_file_for_sparkle":
                                tool_response = move_file_for_sparkle(
                                    user=request.user,
                                    file_name_or_id=file_reference,
                                    target_category_name=function_args.get("target_category_name")
                                )
                            elif function_name == "delete_file_for_sparkle":
                                tool_response = delete_file_for_sparkle(
                                    user=request.user,
                                    file_name_or_id=file_reference
                                )
                            elif function_name == "share_file_for_sparkle":
                                tool_response = share_file_for_sparkle(
                                    user=request.user,
                                    file_name_or_id=file_reference
                                )
                                # Check for URL in share response
                                try:
                                    response_obj = json.loads(tool_response)
                                    if response_obj.get('success') and response_obj.get('share_url'):
                                        file_url_from_tool = response_obj.get('share_url')
                                        file_details = {'url': file_url_from_tool}
                                except Exception as e:
                                    logger.warning(f"Error parsing share details: {e}")
                        
                        # Handle other functions
                        elif function_name == "list_files_for_sparkle":
                            tool_response = list_files_for_sparkle(
                                user=request.user,
                                category_name=function_args.get("category_name"),
                                file_type=function_args.get("file_type")
                            )
                        elif function_name == "search_files_for_sparkle":
                            tool_response = search_files_for_sparkle(
                                user=request.user,
                                keyword=function_args.get("keyword")
                            )
                        elif function_name == "create_folder_for_sparkle":
                            tool_response = create_folder_for_sparkle(
                                user=request.user,
                                folder_name=function_args.get("folder_name")
                            )
                        elif function_name == "get_storage_info_for_sparkle":
                            tool_response = get_storage_info_for_sparkle(user=request.user)
                        
                        # Add result to messages for context
                        if tool_response:
                            messages.append({
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "name": function_name,
                                "content": tool_response
                            })
                            
                            # Track tool success
                            try:
                                result = json.loads(tool_response)
                                if result.get('success', False):
                                    function_executed_successfully = True
                            except json.JSONDecodeError:
                                pass
                    except Exception as e:
                        logger.exception(f"Error executing {function_name}: {e}")
                        messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": json.dumps({"success": False, "error": str(e)})
                        })
                
                # Get final response using all the tool outputs
                try:
                    final_response = client.chat.completions.create(
                        model="gpt-4-turbo",
                        messages=messages,
                        temperature=0.2
                    )
                    
                    final_response_text = final_response.choices[0].message.content
                    
                    # Verify file URL is included if we had one
                    if file_url_from_tool and file_details:
                        # Check if URL is in the response
                        if file_url_from_tool not in final_response_text:
                            logger.warning(f"User {request.user.id} - URL missing from response, adding it")
                            
                            file_name = file_details.get('name', 'file')
                            # Add URL to response
                            final_response_text += f"\n\nDirect Link: {file_url_from_tool}"
                            
                            # Also set action payload for frontend if it was a file open
                            if not action_payload and file_details.get('url'):
                                action_payload = {
                                    "success": True,
                                    "file_name": file_name,
                                    "file_url": file_url_from_tool
                                }
                except Exception as e:
                    logger.exception(f"Error getting final response: {e}")
                    final_response_text = "I'm sorry, I encountered an error processing your request."
            else:
                # No tool calls but still need a response
                final_response_text = response_message.content
            
        except Exception as openai_error:
            logger.exception(f"User {request.user.id} - Error in OpenAI call: {openai_error}")
            final_response_text = "I'm sorry, I encountered an error while processing your request. Please try again."
            function_executed_successfully = False

        # --- Save Interaction & Construct Final Response ---
        interaction_success = final_response_text is not None
        if function_executed_successfully is not None: # Check if a function was called
            interaction_success = interaction_success and function_executed_successfully

        # Create a new conversation_id if none provided
        if not conversation_id:
            conversation_id = uuid.uuid4()
            logger.info(f"User {request.user.id} - Created new conversation: {conversation_id}")

        # Save interaction with enhanced context
        interaction = VoiceInteraction.objects.create(
            user=request.user,
            prompt=prompt_text,
            response=final_response_text,
            success=interaction_success,
            conversation_id=conversation_id,
            reference_context=updated_reference_context,
            referenced_file_id=referenced_file_id,
            referenced_file_name=referenced_file_name,
            action_type=action_type
        )

        # Generate audio response if requested
        audio_url = None
        if include_audio_response:
            audio_url = generate_audio_response(request.user, final_response_text, interaction)

        # Construct the response
        response_data = {
            'success': True,
            'data': {
                'prompt': prompt_text,
                'response': final_response_text,
                'audio_url': audio_url,
                'conversation_id': str(conversation_id),
                'interaction_id': interaction.id,
                'interaction_success': interaction_success
            }
        }

        # Add action and file details if available
        if action_type == "open_file" and action_payload:
            response_data['data']['action'] = {
                'type': 'display_file',
                'payload': action_payload
            }
            response_data['data']['file_details'] = {
                'success': True,
                'fileUrl': action_payload.get('fileUrl') or action_payload.get('file_url'),
                'fileName': action_payload.get('fileName') or action_payload.get('file_name'),
                'fileType': action_payload.get('fileType') or action_payload.get('file_type'),
                'fileId': action_payload.get('fileId') or action_payload.get('file_id')
            }

        return Response(response_data)

    except Exception as e:
        logger.exception(f"User {request.user.id} - Unhandled error in process_voice_api: {e}")
        try:
            VoiceInteraction.objects.create(
                user=request.user,
                prompt=prompt_text if 'prompt_text' in locals() else "Input unavailable",
                response="Error during processing.",
                success=False,
                conversation_id=conversation_id if conversation_id else uuid.uuid4()
            )
        except Exception as log_error:
            logger.error(f"Failed to save error interaction: {log_error}")
        return Response({'success': False, 'error': "Sorry, an internal server error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    finally:
        if temp_audio_path and os.path.exists(temp_audio_path):
            try: os.remove(temp_audio_path)
            except Exception as cleanup_error: logger.error(f"Error cleaning input audio file: {cleanup_error}")


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
    import os
    import tempfile
    import uuid
    import logging
    import boto3
    from django.conf import settings
    from openai import OpenAI

    logger = logging.getLogger(__name__)
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    audio_url = None
    temp_response_path = None
    
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

