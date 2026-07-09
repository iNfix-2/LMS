from django.db import models
from django.contrib.auth.models import User
from courses.models import Course, Lesson


class Enrollment(models.Model):
    """Tracks a student's enrollment in a course."""

    STATUS_CHOICES = (
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('suspended', 'Suspended'),
    )

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('student', 'course')
        ordering = ['-enrolled_at']

    def __str__(self):
        return f"{self.student.get_full_name() or self.student.username} → {self.course.title} ({self.get_status_display()})"

    @property
    def progress_percentage(self):
        total_lessons = self.course.get_total_lessons()
        if total_lessons == 0:
            return 0
        completed_lessons = self.progress.filter(is_completed=True).count()
        return int((completed_lessons / total_lessons) * 100)


class LessonProgress(models.Model):
    """Tracks a student's progress through individual lessons."""

    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='progress')
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_accessed_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Lesson progress"
        unique_together = ('enrollment', 'lesson')
        ordering = ['-last_accessed_at']

    def __str__(self):
        status = "✓" if self.is_completed else "○"
        return f"{status} {self.enrollment.student.username} — {self.lesson.title}"
