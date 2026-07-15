from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Tenant(models.Model):
    name = models.CharField(max_length=200)
    subdomain = models.CharField(max_length=100, unique=True)
    logo = models.ImageField(upload_to='tenant_logos/', blank=True, null=True)
    theme_color = models.CharField(max_length=7, default='#002769')  # default navy
    theme_accent = models.CharField(max_length=7, default='#0ea5e9') # default sky blue
    payout_account_number = models.CharField(max_length=20, blank=True)
    payout_bank_code = models.CharField(max_length=10, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.subdomain})"

class TenantUserMapping(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='tenant_mapping')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='user_mappings')

    def __str__(self):
        return f"{self.user.username} -> {self.tenant.name}"

class TenantCourseMapping(models.Model):
    course = models.OneToOneField('courses.Course', on_delete=models.CASCADE, related_name='tenant_mapping')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='course_mappings')

    def __str__(self):
        return f"{self.course.title} -> {self.tenant.name}"

class TenantPayout(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    )
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='payouts')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reference = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Payout {self.reference} for {self.tenant.name} ({self.status})"
