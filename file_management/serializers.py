
from rest_framework import serializers
from .models import UserFile, FileCategory, CardDetails, AppSubscription, OCRResult


class FileCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FileCategory
        fields = ['id', 'name', 'description', 'is_default']

class UserFileSerializer(serializers.ModelSerializer):
    category = FileCategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True, required=False)
    file_url = serializers.SerializerMethodField()
    file_size_display = serializers.SerializerMethodField()
    document_pair = serializers.SerializerMethodField()
    has_pair = serializers.SerializerMethodField()
    is_locked = serializers.BooleanField(source='locked', read_only=True)
    locked_at = serializers.DateTimeField(read_only=True)
    can_access = serializers.SerializerMethodField()

    class Meta:
        model = UserFile
        fields = [
            'id', 'file_type', 'file', 'upload_date', 'category', 
            'category_id', 'is_public', 'original_filename', 
            'file_size', 'file_url', 'file_size_display',
            'document_side', 'paired_document', 'document_type_name',
            'document_pair', 'has_pair', 'is_favorite', 'is_hidden', 
            'is_locked', 'locked_at', 'can_access'
        ]
        read_only_fields = ['upload_date', 'file_size', 'original_filename']

    def get_file_url(self, obj):
        return obj.get_file_url()
    
    def get_can_access(self, obj):
        """Check if current user can access file"""
        request = self.context.get('request')
        if request:
            return obj.is_accessible_by_user(request.user)
        return False

    def get_file_size_display(self, obj):
        return obj.get_file_size_display()
    
    def get_document_pair(self, obj):
        if obj.document_side == 'single':
            return None
            
        pair_data = {}
        pair = obj.get_document_pair()
        
        for side, doc in pair.items():
            if doc:
                pair_data[side] = {
                    'id': doc.id,
                    'file_url': doc.get_file_url() if doc.is_accessible_by_user(self.context.get('request').user) else None,
                    'original_filename': doc.original_filename,
                    'is_locked': doc.locked
                }
        
        return pair_data if pair_data else None
    
    def get_has_pair(self, obj):
        return obj.has_pair()

class OCRResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = OCRResult
        fields = ['id', 'text_content', 'processed_date', 'status', 'job_id']
        read_only_fields = ['processed_date', 'status', 'job_id']

class FileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    file_type = serializers.ChoiceField(choices=UserFile.FILE_TYPES)
    category_id = serializers.IntegerField(required=False)

class FileSearchSerializer(serializers.Serializer):
    query = serializers.CharField(required=False)
    file_type = serializers.ChoiceField(choices=UserFile.FILE_TYPES, required=False)
    category = serializers.IntegerField(required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)

class CardDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CardDetails
        fields = ['id', 'card_type', 'bank_name', 'card_number', 
                'card_holder', 'expiry_month', 'expiry_year', 'cvv']
        read_only_fields = ['id']
        extra_kwargs = {
            'cvv': {'write_only': True}  # CVV should never be sent back
        }

    def validate_card_number(self, value):
        # Remove any spaces or dashes
        value = ''.join(filter(str.isdigit, value))
        if not len(value) in [15, 16]:
            raise serializers.ValidationError("Invalid card number length")
        return value

    def validate_expiry_month(self, value):
        if not (1 <= int(value) <= 12):
            raise serializers.ValidationError("Invalid expiry month")
        return value.zfill(2)

    def validate_expiry_year(self, value):
        from datetime import datetime
        current_year = datetime.now().year
        year = int(value)
        if not (current_year <= year <= current_year + 20):
            raise serializers.ValidationError("Invalid expiry year")
        return str(year)

    def create(self, validated_data):
        # Get the user from the context
        user = self.context['request'].user
        validated_data['user'] = user
        return super().create(validated_data)

class AppSubscriptionSerializer(serializers.ModelSerializer):
    payment_method = CardDetailsSerializer(read_only=True)
    payment_method_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = AppSubscription
        fields = ['id', 'app_name', 'subscription_type', 'amount', 
                'start_date', 'end_date', 'auto_renewal', 'status',
                'payment_method', 'payment_method_id']
        read_only_fields = ['id']

    def validate(self, data):
        if 'start_date' in data and 'end_date' in data:
            if data['start_date'] > data['end_date']:
                raise serializers.ValidationError({
                    'end_date': 'End date must be after start date'
                })
        return data

    def create(self, validated_data):
        payment_method_id = validated_data.pop('payment_method_id', None)
        if payment_method_id:
            try:
                payment_method = CardDetails.objects.get(
                    id=payment_method_id,
                    user=self.context['request'].user
                )
                validated_data['payment_method'] = payment_method
            except CardDetails.DoesNotExist:
                raise serializers.ValidationError({
                    'payment_method_id': 'Invalid payment method'
                })
        
        return super().create(validated_data)
    
class MobileFileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    file_type = serializers.ChoiceField(choices=['document', 'image'])
    category_id = serializers.IntegerField(required=False)
    category = serializers.IntegerField(required=False)  # For backward compatibility
    
    def validate(self, data):
        # Handle both category fields
        category_legacy = data.pop('category', None) # Get it, or None if not present
        if category_legacy is not None and 'category_id' not in data:
            data['category_id'] = category_legacy
        return data
    
class FilePasswordSerializer(serializers.Serializer):
    password = serializers.CharField(min_length=6, max_length=100)
    
    def validate_password(self, value):
        """Validate password strength"""
        if len(value) < 6:
            raise serializers.ValidationError("Password must be at least 6 characters long")
        
        # Check for at least one digit
        if not any(char.isdigit() for char in value):
            raise serializers.ValidationError("Password must contain at least one digit")
        
        # Check for at least one letter
        if not any(char.isalpha() for char in value):
            raise serializers.ValidationError("Password must contain at least one letter")
        
        return value
    

