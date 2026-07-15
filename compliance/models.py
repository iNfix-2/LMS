import uuid
from django.db import models
from django.contrib.auth.models import User

class GuardianConsent(models.Model):
    student = models.OneToOneField(User, on_delete=models.CASCADE, related_name='guardian_consent')
    guardian_email = models.EmailField()
    consent_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        status = "Approved" if self.is_approved else "Pending"
        return f"Consent for {self.student.username} ({status})"

class DataPrivacyRequest(models.Model):
    REQUEST_TYPE_CHOICES = (
        ('export', 'Export Data'),
        ('delete', 'Delete Account'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processed', 'Processed'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='privacy_requests')
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.get_request_type_display()} for {self.user.username} ({self.status})"

class ModerationLog(models.Model):
    CONTENT_TYPE_CHOICES = (
        ('forum_post', 'Forum Post'),
        ('direct_message', 'Direct Message'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='moderation_logs')
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES)
    original_content = models.TextField()
    flagged_reason = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"Flagged {self.get_content_type_display()} by {self.user.username} - {self.flagged_reason}"
