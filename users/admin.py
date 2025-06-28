from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Extends the default UserAdmin to include custom fields.
    """
    # Add custom fields to the list display
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'google_id')
    
    # Add custom fields to the fieldsets for the detail view
    # Inherit existing fieldsets and add a new one for custom data
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Profile Info', {
            'fields': ('google_id', 'profile_picture', 'assistant_settings'),
        }),
    )
    
    # Make custom fields searchable
    search_fields = UserAdmin.search_fields + ('google_id',)
    
    # Make google_id readonly if it's set
    readonly_fields = UserAdmin.readonly_fields + ('google_id',)