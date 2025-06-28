
from django.contrib import admin
from django.utils.html import format_html
from .models import UserStorage, AdminAccessLog
from django.db import models
from django.contrib import messages

@admin.register(UserStorage)
class UserStorageAdmin(admin.ModelAdmin):
    """
    Admin view for UserStorage.
    Provides a read-only interface with formatted data and a visual usage bar.
    """
    list_display = ('user', 'formatted_storage_used', 'formatted_storage_limit', 'usage_bar', 'updated_at')
    search_fields = ('user__email', 'user__username')
    readonly_fields = ('user', 'storage_used', 'storage_limit', 'created_at', 'updated_at', 'usage_bar')
    list_per_page = 25

    def validation_status(self, obj):
        """Show validation status between DB and S3"""
        try:
            from storage_management.utils import S3StorageManager
            from file_management.models import UserFile
            
            # Get database size
            db_size = UserFile.objects.filter(user=obj.user).aggregate(
                total=models.Sum('file_size')
            )['total'] or 0
            
            # Get current stored size
            stored_size = obj.storage_used
            
            if db_size == 0 and stored_size == 0:
                return format_html('<span style="color: green;">✅ Clean</span>')
            elif db_size == 0 and stored_size > 0:
                return format_html('<span style="color: red;">❌ Phantom Usage</span>')
            elif abs(db_size - stored_size) < 1024:  # Within 1KB
                return format_html('<span style="color: green;">✅ Accurate</span>')
            else:
                diff = abs(db_size - stored_size)
                return format_html(
                    '<span style="color: orange;">⚠️ Drift ({})</span>',
                    self.format_size(diff)
                )
        except:
            return format_html('<span style="color: gray;">? Unknown</span>')
    
    validation_status.short_description = 'Validation'

    def storage_details(self, obj):
        """Show detailed storage breakdown"""
        try:
            from storage_management.utils import S3StorageManager
            from file_management.models import UserFile
            
            # Database stats
            user_files = UserFile.objects.filter(user=obj.user)
            db_count = user_files.count()
            db_size = user_files.aggregate(total=models.Sum('file_size'))['total'] or 0
            
            # S3 stats (simplified check)
            storage_manager = S3StorageManager(obj.user)
            try:
                file_info = storage_manager.get_user_files()
                s3_count = file_info.get('total_s3_objects', 0)
                orphan_count = len(file_info.get('orphaned_files', []))
            except:
                s3_count = orphan_count = 0
            
            return format_html(
                '<div style="font-family: monospace;">'
                '<strong>Database:</strong> {} files, {}<br>'
                '<strong>S3 Objects:</strong> {} files<br>'
                '<strong>Orphaned:</strong> {} files<br>'
                '<strong>Stored Size:</strong> {}'
                '</div>',
                db_count, self.format_size(db_size),
                s3_count,
                orphan_count,
                self.format_size(obj.storage_used)
            )
        except Exception as e:
            return format_html('<span style="color: red;">Error: {}</span>', str(e))
    
    storage_details.short_description = 'Storage Details'

    def recalculate_storage(self, request, queryset):
        """Admin action to recalculate storage for selected users"""
        from storage_management.utils import S3StorageManager
        
        updated_count = 0
        for storage in queryset:
            try:
                storage_manager = S3StorageManager(storage.user)
                storage_info = storage_manager.get_user_storage_info()
                self.message_user(
                    request, 
                    f"Updated storage for {storage.user.email}: {self.format_size(storage_info['used'])}"
                )
                updated_count += 1
            except Exception as e:
                self.message_user(
                    request, 
                    f"Error updating {storage.user.email}: {str(e)}", 
                    level=messages.ERROR
                )
        
        self.message_user(
            request, 
            f"Successfully updated {updated_count} storage records"
        )
    
    recalculate_storage.short_description = "Recalculate storage usage"

    def clean_orphaned_files(self, request, queryset):
        """Admin action to clean orphaned files for selected users"""
        from storage_management.utils import S3StorageManager
        
        cleaned_count = 0
        total_cleaned_size = 0
        
        for storage in queryset:
            try:
                storage_manager = S3StorageManager(storage.user)
                orphan_info = storage_manager.clean_orphaned_files(dry_run=False)
                
                if 'error' not in orphan_info:
                    cleaned_size = orphan_info.get('total_size', 0)
                    total_cleaned_size += cleaned_size
                    
                    self.message_user(
                        request, 
                        f"Cleaned {len(orphan_info['orphaned_files'])} orphaned files "
                        f"for {storage.user.email}: {self.format_size(cleaned_size)}"
                    )
                    cleaned_count += 1
                else:
                    self.message_user(
                        request, 
                        f"Error cleaning {storage.user.email}: {orphan_info['error']}", 
                        level=messages.ERROR
                    )
            except Exception as e:
                self.message_user(
                    request, 
                    f"Error cleaning {storage.user.email}: {str(e)}", 
                    level=messages.ERROR
                )
        
        if total_cleaned_size > 0:
            self.message_user(
                request, 
                f"Successfully cleaned {cleaned_count} users, "
                f"recovered {self.format_size(total_cleaned_size)} total space"
            )
    
    clean_orphaned_files.short_description = "Clean orphaned S3 files"


    def formatted_storage_used(self, obj):
        return self.format_size(obj.storage_used)
    formatted_storage_used.short_description = 'Storage Used'

    def formatted_storage_limit(self, obj):
        return self.format_size(obj.storage_limit)
    formatted_storage_limit.short_description = 'Storage Limit'

    def usage_bar(self, obj):
        """Creates a visual progress bar for storage usage."""
        if obj.storage_limit == 0:
            return "N/A"
        
        percentage = obj.get_usage_percentage()
        color = 'green'
        if percentage > 90:
            color = 'red'
        elif percentage > 75:
            color = 'orange'
        
        # --- FIX APPLIED HERE ---
        # Pre-format the percentage into a string first.
        percentage_text = f"{percentage:.1f}%"
        
        # Then, use a simple placeholder {} for the pre-formatted text.
        return format_html(
            '<div style="width: 100%; border: 1px solid #ccc; background: #f0f0f0; border-radius: 4px;">'
            '<div style="height: 18px; width: {}%; background-color: {}; border-radius: 4px; text-align: center; color: white; font-weight: bold;">{}</div>'
            '</div>',
            percentage,  # This is for the width calculation (needs to be a number)
            color,
            percentage_text  # This is for the display text (now a simple string)
        )
    usage_bar.short_description = 'Usage %'

    @staticmethod
    def format_size(size_in_bytes):
        if size_in_bytes is None:
            return "0 B"
        if size_in_bytes == 0:
            return "0 B"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_in_bytes < 1024.0:
                return f"{size_in_bytes:.2f} {unit}"
            size_in_bytes /= 1024.0
        return f"{size_in_bytes:.2f} PB"

    def has_add_permission(self, request):
        # UserStorage is created automatically via signal
        return False

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(AdminAccessLog)
class AdminAccessLogAdmin(admin.ModelAdmin):
    """
    Read-only admin view for auditing admin access to user files.
    """
    list_display = ('admin_user', 'accessed_file', 'access_time', 'ip_address', 'access_type')
    list_filter = ('access_time', 'admin_user', 'access_type')
    search_fields = ('admin_user__username', 'accessed_file', 'ip_address')
    readonly_fields = ('admin_user', 'accessed_file', 'access_time', 'ip_address', 'access_type')
    date_hierarchy = 'access_time'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False