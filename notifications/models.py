from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('system', 'System'),
        ('enrollment', 'Enrollment'),
        ('payment', 'Payment'),
        ('invoice', 'Invoice'),
        ('receipt', 'Receipt'),
        ('assessment', 'Assessment'),
        ('assignment', 'Assignment'),
        ('progress_report', 'Progress Report'),
        ('subscription', 'Subscription'),
        ('reminder', 'Reminder'),
    ]

    DELIVERY_CHANNELS = [
        ('in_app', 'In-App'),
        ('email', 'Email'),
        ('both', 'Both'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('read', 'Read'),
    ]

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES, default='system')
    delivery_channel = models.CharField(max_length=15, choices=DELIVERY_CHANNELS, default='in_app')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    
    # Related entities (lazy string references to avoid circular imports)
    related_invoice = models.ForeignKey('payments.Invoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    related_payment = models.ForeignKey('payments.PaymentTransaction', on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    related_course = models.ForeignKey('courses.Course', on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    related_report = models.ForeignKey('reports.StudentProgressReport', on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    
    email_sent_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} to {self.recipient.username} ({self.notification_type})"


class EmailLog(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]

    recipient_email = models.EmailField()
    recipient_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='email_logs')
    subject = models.CharField(max_length=255)
    template_name = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True)
    related_notification = models.ForeignKey(Notification, on_delete=models.SET_NULL, null=True, blank=True, related_name='email_logs')
    
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Email to {self.recipient_email} - {self.subject} ({self.status})"


class ReminderRule(models.Model):
    REMINDER_TYPES = [
        ('unpaid_invoice', 'Unpaid Invoice'),
        ('assignment_due', 'Assignment Due'),
        ('assessment_due', 'Assessment Due'),
        ('subscription_expiry', 'Subscription Expiry'),
        ('inactive_student', 'Inactive Student'),
        ('progress_report', 'Progress Report'),
    ]

    name = models.CharField(max_length=100)
    reminder_type = models.CharField(max_length=30, choices=REMINDER_TYPES)
    days_before = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    
    send_to_student = models.BooleanField(default=True)
    send_to_guardian = models.BooleanField(default=False)
    send_to_tutor = models.BooleanField(default=False)
    send_to_admin = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.reminder_type} - {self.days_before} days)"


class DocumentRecord(models.Model):
    DOCUMENT_TYPES = [
        ('invoice_pdf', 'Invoice PDF'),
        ('receipt_pdf', 'Receipt PDF'),
        ('progress_report_pdf', 'Progress Report PDF'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPES)
    
    # Related models
    invoice = models.ForeignKey('payments.Invoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')
    payment = models.ForeignKey('payments.PaymentTransaction', on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')
    report = models.ForeignKey('reports.StudentProgressReport', on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')
    
    file = models.FileField(upload_to='documents/')
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='generated_documents')
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_document_type_display()} for {self.user.username}"
