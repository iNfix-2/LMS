from django.contrib import admin
from .models import GuardianConsent, DataPrivacyRequest, ModerationLog

@admin.register(GuardianConsent)
class GuardianConsentAdmin(admin.ModelAdmin):
    list_display = ('student', 'guardian_email', 'is_approved', 'created_at')
    list_filter = ('is_approved',)
    search_fields = ('student__username', 'guardian_email')

@admin.register(DataPrivacyRequest)
class DataPrivacyRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'request_type', 'status', 'created_at')
    list_filter = ('request_type', 'status')
    search_fields = ('user__username',)

@admin.register(ModerationLog)
class ModerationLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'content_type', 'flagged_reason', 'created_at', 'resolved')
    list_filter = ('content_type', 'resolved')
    search_fields = ('user__username', 'flagged_reason', 'original_content')
