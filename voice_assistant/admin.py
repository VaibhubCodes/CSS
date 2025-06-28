from django.contrib import admin
from .models import VoiceInteraction

@admin.register(VoiceInteraction)
class VoiceInteractionAdmin(admin.ModelAdmin):
    """
    Admin view for VoiceInteraction.
    Provides a read-only interface to review conversation history for debugging and analysis.
    """
    list_display = ('user', 'short_prompt', 'short_response', 'created_at', 'success', 'conversation_id')
    list_filter = ('success', 'created_at', 'user')
    search_fields = ('user__email', 'prompt', 'response', 'conversation_id')
    readonly_fields = (
        'user', 'prompt', 'response', 'audio_response_url', 'success', 'created_at',
        'conversation_id', 'reference_context', 'referenced_file_id',
        'referenced_file_name', 'action_type'
    )
    date_hierarchy = 'created_at'
    list_per_page = 25

    def short_prompt(self, obj):
        return (obj.prompt[:75] + '...') if len(obj.prompt) > 75 else obj.prompt
    short_prompt.short_description = 'Prompt'

    def short_response(self, obj):
        return (obj.response[:75] + '...') if len(obj.response) > 75 else obj.response
    short_response.short_description = 'Response'

    def has_add_permission(self, request):
        # Interactions should only be created by the system
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        # Allow deletion for cleanup if necessary, but generally should be kept
        return request.user.is_superuser