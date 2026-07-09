import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify

class PricingPlan(models.Model):
    PLAN_TYPES = [
        ('single_course', 'Single Course'),
        ('monthly_subscription', 'Monthly Subscription'),
        ('term_subscription', 'Term Subscription'),
        ('school_package', 'School Package'),
    ]

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    plan_type = models.CharField(max_length=50, choices=PLAN_TYPES, default='monthly_subscription')
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="NGN")
    duration_days = models.PositiveIntegerField(default=30)
    courses = models.ManyToManyField('courses.Course', blank=True, related_name='pricing_plans')
    class_levels = models.ManyToManyField('courses.ClassLevel', blank=True, related_name='pricing_plans')
    is_active = models.BooleanField(default=True)
    paystack_plan_code = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['price']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            # Handle potential duplicate slugs
            original_slug = self.slug
            count = 1
            while PricingPlan.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{count}"
                count += 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.price} {self.currency})"

    def grants_course(self, course):
        if self.courses.filter(id=course.id).exists():
            return True
        if self.class_levels.filter(id=course.class_level.id).exists():
            return True
        return False


class CoursePricing(models.Model):
    course = models.OneToOneField('courses.Course', on_delete=models.CASCADE, related_name='pricing')
    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="NGN")
    access_duration_days = models.PositiveIntegerField(default=90)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.course.title} - {self.price} {self.currency}"


class Invoice(models.Model):
    INVOICE_TYPES = [
        ('course_payment', 'Course Payment'),
        ('subscription', 'Subscription'),
        ('manual', 'Manual'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='invoices')
    invoice_number = models.CharField(max_length=100, unique=True, blank=True)
    invoice_type = models.CharField(max_length=50, choices=INVOICE_TYPES)
    course = models.ForeignKey('courses.Course', on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    plan = models.ForeignKey(PricingPlan, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="NGN")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    due_date = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            date_str = timezone.now().strftime('%Y%m%d')
            random_str = uuid.uuid4().hex[:8].upper()
            self.invoice_number = f"EDU-INV-{date_str}-{random_str}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Invoice {self.invoice_number} ({self.status})"

    def mark_paid(self):
        self.status = 'paid'
        self.paid_at = timezone.now()
        self.save()

    def mark_failed(self):
        self.status = 'failed'
        self.save()

    @property
    def is_paid(self):
        return self.status == 'paid'


class PaymentTransaction(models.Model):
    PROVIDER_CHOICES = [
        ('paystack', 'Paystack'),
        ('flutterwave', 'Flutterwave'),
        ('manual', 'Manual'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('abandoned', 'Abandoned'),
        ('reversed', 'Reversed'),
    ]

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='transactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    provider = models.CharField(max_length=50, choices=PROVIDER_CHOICES, default='paystack')
    reference = models.CharField(max_length=100, unique=True, blank=True)
    provider_reference = models.CharField(max_length=100, blank=True)
    access_code = models.CharField(max_length=100, blank=True)
    authorization_url = models.URLField(max_length=500, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="NGN")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    gateway_response = models.CharField(max_length=255, blank=True)
    channel = models.CharField(max_length=50, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    raw_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.reference:
            date_str = timezone.now().strftime('%Y%m%d')
            random_str = uuid.uuid4().hex[:8].upper()
            self.reference = f"EDU-PAY-{date_str}-{random_str}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Transaction {self.reference} ({self.status})"


class StudentSubscription(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('pending', 'Pending'),
    ]

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(PricingPlan, on_delete=models.CASCADE, related_name='subscriptions')
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='subscriptions')
    payment = models.ForeignKey(PaymentTransaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='subscriptions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    paystack_subscription_code = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.username} - {self.plan.name} ({self.status})"

    @property
    def is_valid(self):
        return self.status == 'active' and (self.ends_at is None or self.ends_at > timezone.now())


class CourseAccess(models.Model):
    SOURCE_CHOICES = [
        ('free', 'Free'),
        ('course_payment', 'Course Payment'),
        ('subscription', 'Subscription'),
        ('manual', 'Manual'),
    ]

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_accesses')
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='course_accesses')
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES)
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='course_accesses')
    payment = models.ForeignKey(PaymentTransaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='course_accesses')
    subscription = models.ForeignKey(StudentSubscription, on_delete=models.SET_NULL, null=True, blank=True, related_name='course_accesses')
    starts_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="granted_course_accesses")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.username} access to {self.course.title}"

    @property
    def is_valid(self):
        return self.is_active and (self.expires_at is None or self.expires_at > timezone.now())
