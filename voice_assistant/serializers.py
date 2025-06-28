from rest_framework import serializers
from .models import VoiceInteraction

class VoiceInteractionSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoiceInteraction
        fields = ['id', 'prompt', 'response', 'audio_response_url', 'created_at', 'conversation_id', 'reference_context']
        read_only_fields = ['created_at', 'conversation_id']

class VoiceCommandSerializer(serializers.Serializer):
    audio = serializers.FileField(required=False)
    text = serializers.CharField(required=False)
    conversation_id = serializers.UUIDField(required=False)  # Optional field to continue existing conversation

    def validate(self, data):
        if not data.get('audio') and not data.get('text'):
            raise serializers.ValidationError(
                "Either audio or text must be provided"
            )
        return data

class CommandHistoryFilterSerializer(serializers.Serializer):
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    keyword = serializers.CharField(required=False)

class CommandSuggestionSerializer(serializers.Serializer):
    command = serializers.CharField()
    description = serializers.CharField()
    examples = serializers.ListField(child=serializers.CharField())

class AssistantSettingsSerializer(serializers.Serializer):
    voice_type = serializers.ChoiceField(
        choices=['nova', 'alloy', 'echo', 'fable', 'onyx', 'shimmer'],
        default='nova'
    )
    language = serializers.ChoiceField(
        choices=['en', 'es', 'fr', 'de'],
        default='en'
    )
    response_length = serializers.ChoiceField(
        choices=['concise', 'detailed'],
        default='concise'
    )
    include_audio_response = serializers.BooleanField(default=True)