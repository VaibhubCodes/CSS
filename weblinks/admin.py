from django.contrib import admin
from .models import WebLink, Meeting,Notification

@admin.register(WebLink)
class WebLinkAdmin(admin.ModelAdmin):
    list_display = ('link_name', 'url', 'user', 'created_at')
    search_fields = ('link_name', 'description', 'url', 'user__username', 'user__email')
    list_filter = ('user', 'created_at')
    ordering = ('-created_at',)


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ('meeting_name', 'meeting_link', 'user', 'start_time', 'end_time', 'created_at')
    search_fields = ('meeting_name', 'description', 'user__username', 'user__email')
    list_filter = ('user', 'start_time')
    ordering = ('-start_time',)

admin.site.register(Notification)