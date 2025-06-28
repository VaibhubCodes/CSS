from django.contrib import admin
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

class PasswordHistoryInline(admin.TabularInline):
    model = PasswordHistory
    extra = 0
    readonly_fields = ('previous_password', 'password_iv_display', 'changed_date')
    fields = ('changed_date', 'password_iv_display')

    def password_iv_display(self, obj):
        import base64
        return base64.b64encode(obj.password_iv).decode('utf-8') if obj.password_iv else 'N/A'
    password_iv_display.short_description = 'IV (Base64)'
    
    def has_change_permission(self, request, obj=None):
        return False
        
    def has_add_permission(self, request, obj=None):
        return False

class PasswordCompromiseInline(admin.TabularInline):
    model = PasswordCompromise
    extra = 0
    readonly_fields = ('detected_date', 'breach_source', 'is_resolved', 'resolved_date')
    fields = ('detected_date', 'breach_source', 'is_resolved', 'resolved_date')
    
    def has_change_permission(self, request, obj=None):
        return False
        
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(PasswordCategory)
class PasswordCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'created_at')
    list_filter = ('user',)
    search_fields = ('name',)

@admin.register(PasswordEntry)
class PasswordEntryAdmin(admin.ModelAdmin):
    list_display = ('title', 'entry_type', 'user', 'category', 'strength', 'last_used', 'created_at')
    list_filter = ('entry_type', 'strength', 'category', 'user')
    search_fields = ('title', 'username', 'email', 'website_url')
    readonly_fields = ('password', 'password_iv', 'created_at', 'updated_at')
    inlines = [PasswordHistoryInline, PasswordCompromiseInline]

    def password_iv_display(self, obj):
        import base64
        return base64.b64encode(obj.password_iv).decode('utf-8') if obj.password_iv else 'N/A'
    password_iv_display.short_description = 'Password IV (Base64)'

@admin.register(PasswordCompromise)
class PasswordCompromiseAdmin(admin.ModelAdmin):
    list_display = ('password_entry', 'detected_date', 'breach_source', 'is_resolved')
    list_filter = ('is_resolved', 'detected_date')
    readonly_fields = ('detected_date',)

@admin.register(PasswordHistory)
class PasswordHistoryAdmin(admin.ModelAdmin):
    list_display = ('password_entry', 'changed_date')
    list_filter = ('changed_date',)
    readonly_fields = ('password_entry', 'previous_password', 'password_iv', 'changed_date')

@admin.register(SecuritySetting)
class SecuritySettingAdmin(admin.ModelAdmin):
    list_display = ('user', 'check_for_compromised', 'suggest_strong_passwords', 'auto_fill_enabled')
    list_filter = ('check_for_compromised', 'suggest_strong_passwords', 'auto_fill_enabled')

@admin.register(PasskeyCredential)
class PasskeyCredentialAdmin(admin.ModelAdmin):
    list_display = ('password_entry', 'device_name', 'created_at', 'last_used')
    list_filter = ('created_at', 'last_used')
    readonly_fields = ('credential_id', 'public_key', 'sign_count', 'created_at')

@admin.register(PasswordAccessLog)
class PasswordAccessLogAdmin(admin.ModelAdmin):
    list_display = ('password_entry', 'access_type', 'access_date', 'ip_address')
    list_filter = ('access_type', 'access_date')
    readonly_fields = ('password_entry', 'access_date', 'device_info', 'ip_address')

@admin.register(MasterPassword)
class MasterPasswordAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'last_changed')
    readonly_fields = ('password_hash', 'salt', 'iterations', 'created_at', 'last_changed')
    
    def has_add_permission(self, request):
        # Prevent adding master passwords directly through admin
        return False

