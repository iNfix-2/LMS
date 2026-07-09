from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from courses.models import Course, Module

class Assignment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assignments')
    module = models.ForeignKey(Module, on_delete=models.SET_NULL, null=True, blank=True, related_name='assignments')
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField()
    instruction_file = models.FileField(upload_to='assignments/instructions/', null=True, blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    total_marks = models.PositiveIntegerField(default=100)
    is_published = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Assignment.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

class AssignmentSubmission(models.Model):
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('marked', 'Marked'),
        ('returned', 'Returned'),
    ]
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assignment_submissions')
    answer_text = models.TextField(blank=True)
    submitted_file = models.FileField(upload_to='assignments/submissions/', null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    score = models.FloatField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.student.username} - {self.assignment.title}"
