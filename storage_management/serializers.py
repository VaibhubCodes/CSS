from rest_framework import serializers
from .models import UserStorage, AdminAccessLog

class StorageInfoSerializer(serializers.ModelSerializer):
    usage_percentage = serializers.SerializerMethodField()
    storage_used_formatted = serializers.SerializerMethodField()
    storage_limit_formatted = serializers.SerializerMethodField()
    available_storage_formatted = serializers.SerializerMethodField()

    class Meta:
        model = UserStorage
        fields = [
            'id', 'storage_used', 'storage_limit', 'usage_percentage',
            'storage_used_formatted', 'storage_limit_formatted',
            'available_storage_formatted', 'created_at', 'updated_at'
        ]
        read_only_fields = ['storage_used', 'created_at', 'updated_at']

    def get_usage_percentage(self, obj):
        return obj.get_usage_percentage()

    def format_size(self, size_in_bytes):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_in_bytes < 1024:
                return f"{size_in_bytes:.2f} {unit}"
            size_in_bytes /= 1024
        return f"{size_in_bytes:.2f} TB"

    def get_storage_used_formatted(self, obj):
        return self.format_size(obj.storage_used)

    def get_storage_limit_formatted(self, obj):
        return self.format_size(obj.storage_limit)

    def get_available_storage_formatted(self, obj):
        return self.format_size(obj.get_available_storage())

class StorageAnalyticsSerializer(serializers.Serializer):
    file_count = serializers.IntegerField()
    file_types = serializers.DictField()
    categories = serializers.DictField()
    recent_uploads = serializers.ListField()
    storage_growth = serializers.DictField()

class AdminAccessLogSerializer(serializers.ModelSerializer):
    admin_user = serializers.StringRelatedField()

    class Meta:
        model = AdminAccessLog
        fields = [
            'id', 'admin_user', 'accessed_file', 'access_time',
            'ip_address', 'access_type'
        ]
        read_only_fields = fields

class StorageOptimizationSerializer(serializers.Serializer):
    large_files = serializers.ListField()
    duplicate_files = serializers.ListField()
    old_files = serializers.ListField()
    potential_savings = serializers.IntegerField()
    recommendations = serializers.ListField()

class EnhancedStorageInfoSerializer(StorageInfoSerializer):
    """Enhanced serializer with subscription info"""
    subscription_info = serializers.SerializerMethodField()
    
    class Meta(StorageInfoSerializer.Meta):
        fields = StorageInfoSerializer.Meta.fields + ['subscription_info']
    
    def get_subscription_info(self, obj):
        try:
            from payments.utils import get_user_subscription_info
            return get_user_subscription_info(obj.user)
        except ImportError:
            return {'is_sparkle': False}