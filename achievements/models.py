from django.db import models
from django.conf import settings
from django.utils import timezone

class Badge(models.Model):
    BADGE_TYPES = [
        ('course_completed', 'Course Completion'),
        ('perfect_score', 'Perfect Score'),
        ('high_attendance', 'High Attendance'),
        ('custom', 'Custom Achievement'),
    ]
    title = models.CharField(max_length=150, unique=True)
    description = models.TextField()
    badge_type = models.CharField(choices=BADGE_TYPES, default='custom', max_length=50)
    image = models.ImageField(blank=True, null=True, upload_to='badges/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class CourseCompletionRule(models.Model):
    course = models.OneToOneField('courses.Course', on_delete=models.CASCADE, related_name='completion_rule')
    min_progress_percentage = models.PositiveIntegerField(default=100, help_text="Minimum progress percentage required")
    require_all_assessments_passed = models.BooleanField(default=True, help_text="Require passing all published assessments")
    require_all_assignments_submitted = models.BooleanField(default=True, help_text="Require submitting all published assignments")
    min_attendance_percentage = models.FloatField(blank=True, null=True, help_text="Minimum attendance percentage required (optional)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Completion Rule for {self.course.title}"

class StudentAchievement(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='achievements')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name='student_achievements')
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='student_achievements', blank=True, null=True)
    earned_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-earned_at']
        unique_together = ('student', 'badge', 'course')

    def __str__(self):
        return f"{self.student.username} earned {self.badge.title}"

class Certificate(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='certificates')
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='certificates')
    certificate_number = models.CharField(max_length=100, unique=True)
    verification_code = models.CharField(max_length=100, unique=True)
    issued_at = models.DateTimeField(default=timezone.now)
    pdf_file = models.FileField(blank=True, null=True, upload_to='certificates/')

    class Meta:
        ordering = ['-issued_at']
        unique_together = ('student', 'course')

    def __str__(self):
        return f"Certificate for {self.student.username} - {self.course.title}"
