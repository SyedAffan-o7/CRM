from django.contrib import admin
from .models import NotificationType, NotificationPreference, Notification, NotificationLog


@admin.register(NotificationType)
class NotificationTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'priority', 'is_active', 'send_email', 'send_in_app']
    list_filter = ['category', 'priority', 'is_active']
    search_fields = ['name', 'description']
    ordering = ['category', 'name']


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'email_follow_ups', 'email_lead_changes', 'daily_digest']
    list_filter = ['daily_digest', 'weekly_digest']
    search_fields = ['user__username', 'user__email']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'recipient', 'notification_type', 'status', 'email_sent', 'created_at']
    list_filter = ['status', 'notification_type', 'email_sent', 'created_at']
    search_fields = ['title', 'message', 'recipient__username']
    readonly_fields = ['created_at', 'sent_at', 'read_at', 'email_sent_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('notification_type', 'recipient', 'title', 'message')
        }),
        ('Content Object', {
            'fields': ('content_type', 'object_id'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('status', 'scheduled_for', 'sent_at', 'read_at')
        }),
        ('Email', {
            'fields': ('email_sent', 'email_sent_at', 'email_error'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('data', 'created_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ['notification', 'action', 'timestamp']
    list_filter = ['action', 'timestamp']
    search_fields = ['notification__title', 'details']
    readonly_fields = ['timestamp']
    ordering = ['-timestamp']
