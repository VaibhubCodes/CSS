from rest_framework import serializers
from .models import (
    PasswordCategory, 
    PasswordEntry, 
    PasswordCompromise, 
    PasswordHistory,
    SecuritySetting,
    PasskeyCredential,
    PasswordAccessLog,
    MasterPassword
)
import base64
from .utils import PasswordEncryption, PasswordSecurity, create_master_password_hash

class PasswordCategorySerializer(serializers.ModelSerializer):
    """Serializer for password categories"""
    class Meta:
        model = PasswordCategory
        fields = ['id', 'name', 'icon', 'color', 'created_at']
        read_only_fields = ['created_at']

    def create(self, validated_data):
        """Add the current user to the category"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
        
class PasswordEntrySerializer(serializers.ModelSerializer):
    print("✅ PasswordEntrySerializer LOADED")
    """Serializer for password entries with encrypted password handling"""
    password = serializers.CharField(write_only=True, required=False)
    password_decrypted = serializers.SerializerMethodField(read_only=True)
    category_name = serializers.SerializerMethodField(read_only=True)
    is_compromised = serializers.SerializerMethodField(read_only=True)
    is_reused = serializers.SerializerMethodField(read_only=True)
    website_url = serializers.URLField(allow_blank=True, required=False, allow_null=True)
    class Meta:
        model = PasswordEntry
        fields = [
            'id', 'entry_type', 'title', 'username', 'email',
            'password', 'password_decrypted', 'website_url', 'notes', 'strength',
            'category', 'category_name', 'last_used', 'is_favorite',
            'created_at', 'updated_at', 'is_compromised', 'is_reused'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'strength', 'last_used']
    
    def get_category_name(self, obj):
        """Return the category name for display"""
        if obj.category:
            return obj.category.name
        return None
    
    def get_password_decrypted(self, obj):
        request = self.context.get('request')
        master_password = self.context.get('master_password')

        print("🔍 get_password_decrypted:", master_password, request.user if request else 'No request')

        if not master_password or not request:
            return None

        try:
            mp_record = MasterPassword.objects.get(user=request.user)
            key = PasswordEncryption.generate_key(master_password, mp_record.salt, mp_record.iterations)
            decrypted = PasswordEncryption.decrypt(obj.password, key, obj.password_iv)
            print("✅ Decrypted successfully:", decrypted)
            return decrypted
        except Exception as e:
            print("❌ Decryption failed:", str(e))
            return None


    
    def get_is_compromised(self, obj):
        """Return whether this password is compromised"""
        return obj.is_compromised
    
    def get_is_reused(self, obj):
        """Return whether this password is reused"""
        return obj.is_reused
    
    def create(self, validated_data):
        """Create a new password entry with encryption"""
        # Handle the password field for encryption
        password = validated_data.pop('password', None)
        user = self.context['request'].user
        
        # Create the entry without the password first
        entry = PasswordEntry(user=user, **validated_data)
        
        # Get the master password info
        master_password = self.context.get('master_password')
        if not master_password:
            # In actual implementation, we would get the master password from
            # a secure session or require it on entry creation
            raise serializers.ValidationError(
                "Master password required to create a password entry"
            )
            
        # Get or create the master password record
        try:
            mp_record = MasterPassword.objects.get(user=user)
        except MasterPassword.DoesNotExist:
            # For development/testing only - create a default master password record
            from .utils import create_master_password_hash
            password_hash, salt, iterations = create_master_password_hash('default_master_password')
            mp_record = MasterPassword.objects.create(
                user=user,
                password_hash=password_hash,
                salt=salt,
                iterations=iterations
            )
        
        # Generate encryption key from master password
        key = PasswordEncryption.generate_key(
            master_password,
            mp_record.salt,
            mp_record.iterations
        )
        
        # Encrypt the password
        if password:
            encrypted_data, iv = PasswordEncryption.encrypt(password, key)
            entry.password = encrypted_data
            entry.password_iv = iv
            
            # Calculate password strength
            strength, _ = PasswordSecurity.check_password_strength(password)
            entry.strength = strength
        
        entry.save()
        return entry
    
    def update(self, instance, validated_data):
        """Update a password entry with encryption if needed"""
        # Handle the password field for encryption
        password = validated_data.pop('password', None)
        user = self.context['request'].user
        
        # Update the instance with other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # If password is provided, encrypt it
        if password:
            # Get the master password info
            master_password = self.context.get('master_password')
            if not master_password:
                raise serializers.ValidationError(
                    "Master password required to update a password"
                )
                
            try:
                mp_record = MasterPassword.objects.get(user=user)
            except MasterPassword.DoesNotExist:
                raise serializers.ValidationError(
                    "Master password not set up for this user"
                )
            
            # Save the current password to history
            if instance.password:
                PasswordHistory.objects.create(
                    password_entry=instance,
                    previous_password=instance.password,
                    password_iv=instance.password_iv
                )
            
            # Generate encryption key and encrypt the new password
            key = PasswordEncryption.generate_key(
                master_password,
                mp_record.salt,
                mp_record.iterations
            )
            
            encrypted_data, iv = PasswordEncryption.encrypt(password, key)
            instance.password = encrypted_data
            instance.password_iv = iv
            
            # Calculate password strength
            strength, _ = PasswordSecurity.check_password_strength(password)
            instance.strength = strength
        
        instance.save()
        return instance

class PasswordHistorySerializer(serializers.ModelSerializer):
    """Serializer for password history entries"""
    changed_date = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model = PasswordHistory
        fields = ['id', 'password_entry', 'changed_date']
        read_only_fields = ['id', 'password_entry', 'changed_date']

class SecuritySettingSerializer(serializers.ModelSerializer):
    """Serializer for security settings"""
    class Meta:
        model = SecuritySetting
        fields = [
            'check_for_compromised', 'suggest_strong_passwords',
            'min_password_length', 'password_require_uppercase',
            'password_require_numbers', 'password_require_symbols',
            'auto_fill_enabled'
        ]
    
    def create(self, validated_data):
        """Create or update security settings for the user"""
        user = self.context['request'].user
        settings, created = SecuritySetting.objects.update_or_create(
            user=user,
            defaults=validated_data
        )
        return settings

class MasterPasswordSerializer(serializers.Serializer):
    """Serializer for setting up or verifying the master password"""
    current_password = serializers.CharField(write_only=True, required=False)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True, required=False)
    
    def validate(self, data):
        """Validate the master password data"""
        # Check if this is an update or create
        user = self.context['request'].user
        try:
            existing = MasterPassword.objects.get(user=user)
            # If updating, require current password
            if 'current_password' not in data:
                raise serializers.ValidationError({
                    'current_password': 'Current password is required when updating'
                })
            # Check if the current password is correct
            from .utils import verify_master_password
            if not verify_master_password(
                data['current_password'],
                existing.password_hash,
                existing.salt,
                existing.iterations
            ):
                raise serializers.ValidationError({
                    'current_password': 'Current password is incorrect'
                })
        except MasterPassword.DoesNotExist:
            # This is a new master password setup
            pass
        
        # For new password or changes, confirm_password is required
        if 'new_password' in data and data['new_password']:
            if 'confirm_password' not in data or data['confirm_password'] != data['new_password']:
                raise serializers.ValidationError({
                    'confirm_password': 'Passwords do not match'
                })
            
            # Check password strength
            strength, score = PasswordSecurity.check_password_strength(data['new_password'])
            if strength == 'weak':
                raise serializers.ValidationError({
                    'new_password': 'Password is too weak. Please use a stronger password.'
                })
        
        return data
    
    def create(self, validated_data):
        """Create or update the master password"""
        user = self.context['request'].user
        new_password = validated_data['new_password']
        
        # Create hash and salt for the new password
        password_hash, salt, iterations = create_master_password_hash(new_password)
        
        # Save or update
        master_password, created = MasterPassword.objects.update_or_create(
            user=user,
            defaults={
                'password_hash': password_hash,
                'salt': salt,
                'iterations': iterations
            }
        )
        
        return {
            'success': True,
            'created': created
        }

class PasswordVerificationSerializer(serializers.Serializer):
    """Serializer for verifying the master password"""
    master_password = serializers.CharField(write_only=True)

    def validate(self, data):
        """Validate the master password"""
        user = self.context['request'].user
        try:
            mp_record = MasterPassword.objects.get(user=user)
        except MasterPassword.DoesNotExist:
            raise serializers.ValidationError({
                'master_password': 'Master password has not been set up'
            })
        
        # Verify the master password
        from .utils import verify_master_password
        if not verify_master_password(
            data['master_password'],
            mp_record.password_hash,
            mp_record.salt,
            mp_record.iterations
        ):
            raise serializers.ValidationError({
                'master_password': 'Incorrect master password'
            })
            
        return data 
    
class PasswordEntryFilterSerializer(serializers.Serializer):
    category = serializers.IntegerField(required=False, allow_null=True) # Expecting category ID
    entry_type = serializers.ChoiceField(choices=PasswordEntry.TYPE_CHOICES, required=False, allow_blank=True)
    is_favorite = serializers.BooleanField(required=False, allow_null=True)
    q = serializers.CharField(required=False, allow_blank=True) # Search query
    sort_by = serializers.ChoiceField(
        choices=['title', '-title', 'updated_at', '-updated_at', 'last_used', '-last_used', 'created_at', '-created_at'],
        required=False,
        allow_blank=True
    )

    def validate_category(self, value):
        if value is not None:
            try:
                PasswordCategory.objects.get(id=value) 
            except PasswordCategory.DoesNotExist:
                raise serializers.ValidationError("Invalid category ID.")
        return value
    
