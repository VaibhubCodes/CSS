from django.db import models
from django.conf import settings
import uuid

class VoiceInteraction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    prompt = models.TextField()
    response = models.TextField()
    audio_response_url = models.URLField(null=True, blank=True)
    success = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    conversation_id = models.UUIDField(default=uuid.uuid4)  # Group related interactions
    reference_context = models.JSONField(null=True, blank=True)  # Store parsed references for "this", "that", etc.
    
    # Enhanced fields for better file reference tracking
    referenced_file_id = models.IntegerField(null=True, blank=True)  # Store the most recently referenced file ID
    referenced_file_name = models.CharField(max_length=255, null=True, blank=True)  # Store the most recently referenced file name
    action_type = models.CharField(max_length=50, null=True, blank=True)  # Store the type of action performed (e.g., "open_file", "list_files")
    
    def __str__(self):
        return f"Voice Interaction - {self.created_at}"
    
    def get_recent_interactions(user, conversation_id, limit=5):
        """Get the most recent interactions for a conversation"""
        return VoiceInteraction.objects.filter(
            user=user,
            conversation_id=conversation_id
        ).order_by('-created_at')[:limit]
    
    def update_file_reference(self, file_obj):
        """Update this interaction with file reference details"""
        if file_obj:
            self.referenced_file_id = file_obj.id
            self.referenced_file_name = file_obj.original_filename
            
            # Update reference_context if it doesn't exist
            if not self.reference_context:
                self.reference_context = {}
                
            # Create a standardized file reference
            file_reference = {
                'id': file_obj.id,
                'name': file_obj.original_filename,
                'type': getattr(file_obj, 'file_type', 'unknown')
            }
            
            # Update common reference terms
            self.reference_context.update({
                'this': file_reference,
                'it': file_reference,
                'that': file_reference,
                'the file': file_reference,
                'the document': file_reference,
                '1': file_reference  # If not already in numbered list, add as #1
            })
            
            self.save()
            return True
        return False