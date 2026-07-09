from django.db import models
from django.contrib.auth.models import User
from courses.models import Course, Lesson

class AIConversation(models.Model):
    CONVERSATION_TYPES = [
        ('lesson_assistant', 'Lesson Assistant'),
        ('lesson_summary', 'Lesson Summary'),
        ('practice_questions', 'Practice Questions'),
        ('quiz_generation', 'Quiz Generation'),
        ('worksheet_generation', 'Worksheet Generation'),
        ('report_comment', 'Report Comment'),
        ('study_recommendation', 'Study Recommendation'),
        ('general', 'General'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_conversations')
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, related_name='ai_conversations')
    lesson = models.ForeignKey(Lesson, on_delete=models.SET_NULL, null=True, blank=True, related_name='ai_conversations')
    title = models.CharField(max_length=255)
    conversation_type = models.CharField(max_length=50, choices=CONVERSATION_TYPES, default='general')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.title} ({self.get_conversation_type_display()}) - {self.user.username}"


class AIMessage(models.Model):
    SENDER_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]
    MODERATION_STATUS_CHOICES = [
        ('not_checked', 'Not Checked'),
        ('safe', 'Safe'),
        ('flagged', 'Flagged'),
        ('blocked', 'Blocked'),
    ]
    conversation = models.ForeignKey(AIConversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=20, choices=SENDER_CHOICES)
    content = models.TextField()
    moderation_status = models.CharField(max_length=20, choices=MODERATION_STATUS_CHOICES, default='not_checked')
    moderation_categories = models.JSONField(default=dict, blank=True)
    tokens_input = models.PositiveIntegerField(default=0)
    tokens_output = models.PositiveIntegerField(default=0)
    model_used = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Msg {self.id} in Chat {self.conversation_id} by {self.sender}"


class AIRequestLog(models.Model):
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('blocked', 'Blocked'),
        ('flagged', 'Flagged'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_request_logs')
    request_type = models.CharField(max_length=100)
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, related_name='ai_request_logs')
    lesson = models.ForeignKey(Lesson, on_delete=models.SET_NULL, null=True, blank=True, related_name='ai_request_logs')
    prompt = models.TextField()
    response = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='success')
    error_message = models.TextField(blank=True)
    model_used = models.CharField(max_length=100, blank=True)
    tokens_input = models.PositiveIntegerField(default=0)
    tokens_output = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Log {self.id}: {self.request_type} - {self.status} for {self.user.username}"


class AIGeneratedContent(models.Model):
    CONTENT_TYPE_CHOICES = [
        ('quiz', 'Quiz'),
        ('worksheet', 'Worksheet'),
        ('lesson_summary', 'Lesson Summary'),
        ('practice_questions', 'Practice Questions'),
        ('report_comment', 'Report Comment'),
        ('study_plan', 'Study Plan'),
    ]
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('published', 'Published'),
    ]
    generated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_generated_contents')
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, related_name='ai_generated_contents')
    lesson = models.ForeignKey(Lesson, on_delete=models.SET_NULL, null=True, blank=True, related_name='ai_generated_contents')
    content_type = models.CharField(max_length=50, choices=CONTENT_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    prompt = models.TextField()
    generated_content = models.JSONField(default=dict, blank=True)
    raw_response = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_ai_content')
    review_comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_content_type_display()}) - {self.status}"


class AIUsageLimit(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='ai_usage_limit')
    date = models.DateField()
    requests_count = models.PositiveIntegerField(default=0)
    tokens_used = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} AI Usage on {self.date}: {self.requests_count} requests"


class AISafetyFlag(models.Model):
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_safety_flags')
    message = models.ForeignKey(AIMessage, on_delete=models.SET_NULL, null=True, blank=True, related_name='safety_flags')
    request_log = models.ForeignKey(AIRequestLog, on_delete=models.SET_NULL, null=True, blank=True, related_name='safety_flags')
    flag_type = models.CharField(max_length=100)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='low')
    description = models.TextField()
    reviewed = models.BooleanField(default=False)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_ai_flags')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Flag {self.flag_type} ({self.severity}) - {self.user.username} - Reviewed: {self.reviewed}"
