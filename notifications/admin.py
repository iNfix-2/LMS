from django.contrib import admin
from .models import Notification, EmailLog, ReminderRule, DocumentRecord


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'title', 'notification_type', 'delivery_channel', 'status', 'created_at')
    list_filter = ('notification_type', 'delivery_channel', 'status', 'created_at')
    search_fields = ('recipient__username', 'recipient__email', 'title', 'message')
    raw_id_fields = ('recipient', 'sender', 'related_invoice', 'related_payment', 'related_course', 'related_report')


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ('recipient_email', 'subject', 'status', 'sent_at', 'created_at')
    list_filter = ('status', 'created_at', 'sent_at')
    search_fields = ('recipient_email', 'recipient_user__username', 'subject', 'error_message')
    raw_id_fields = ('recipient_user', 'related_notification')


@admin.register(ReminderRule)
class ReminderRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'reminder_type', 'days_before', 'is_active')
    list_filter = ('reminder_type', 'is_active')
    search_fields = ('name',)


@admin.register(DocumentRecord)
class DocumentRecordAdmin(admin.ModelAdmin):
    list_display = ('user', 'document_type', 'created_at')
    list_filter = ('document_type', 'created_at')
    search_fields = ('user__username', 'user__email')
    raw_id_fields = ('user', 'invoice', 'payment', 'report', 'generated_by')
