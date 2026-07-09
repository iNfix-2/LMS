from django.contrib import admin
from .models import AIConversation, AIMessage, AIRequestLog, AIGeneratedContent, AIUsageLimit, AISafetyFlag

@admin.register(AIConversation)
class AIConversationAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'lesson', 'conversation_type', 'is_active', 'updated_at')
    list_filter = ('conversation_type', 'is_active', 'created_at')
    search_fields = ('user__username', 'title')

@admin.register(AIMessage)
class AIMessageAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'sender', 'moderation_status', 'model_used', 'created_at')
    list_filter = ('sender', 'moderation_status', 'model_used')
    search_fields = ('content',)

@admin.register(AIRequestLog)
class AIRequestLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'request_type', 'status', 'model_used', 'created_at')
    list_filter = ('request_type', 'status', 'model_used')
    search_fields = ('user__username', 'prompt', 'response')

@admin.register(AIGeneratedContent)
class AIGeneratedContentAdmin(admin.ModelAdmin):
    list_display = ('title', 'content_type', 'generated_by', 'status', 'reviewed_by', 'created_at')
    list_filter = ('content_type', 'status', 'created_at')
    search_fields = ('title', 'prompt')

@admin.register(AIUsageLimit)
class AIUsageLimitAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'requests_count', 'tokens_used', 'updated_at')
    list_filter = ('date',)
    search_fields = ('user__username',)

@admin.register(AISafetyFlag)
class AISafetyFlagAdmin(admin.ModelAdmin):
    list_display = ('user', 'flag_type', 'severity', 'reviewed', 'created_at')
    list_filter = ('severity', 'reviewed', 'flag_type')
    search_fields = ('user__username', 'description')
