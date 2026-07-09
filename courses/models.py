from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils import timezone


class Subject(models.Model):
    """Academic subject (e.g. Mathematics, English)."""

    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ClassLevel(models.Model):
    """Represents a class/grade level (e.g. Year 1, Year 2)."""

    name = models.CharField(max_length=100, unique=True)
    order = models.PositiveIntegerField(default=0, help_text="Display order (lower = first)")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name


class Course(models.Model):
    """A course belongs to a subject and class level, created by a tutor."""

    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=300, unique=True, blank=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='courses')
    class_level = models.ForeignKey(ClassLevel, on_delete=models.CASCADE, related_name='courses')
    description = models.TextField(blank=True)
    thumbnail = models.ImageField(upload_to='course_thumbnails/', blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='courses_created')
    assigned_tutors = models.ManyToManyField(
        User,
        blank=True,
        related_name="assigned_courses"
    )
    is_published = models.BooleanField(default=False)
    is_free = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.class_level})"

    def get_total_lessons(self):
        return Lesson.objects.filter(module__course=self).count()

    def get_enrolled_students_count(self):
        return self.enrollments.filter(status='active').count()

    def can_be_managed_by(self, user):
        if not user or not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return True
        if self.created_by == user:
            return True
        if self.assigned_tutors.filter(id=user.id).exists():
            return True
        return False


class Module(models.Model):
    """A module groups lessons within a course."""

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.course.title} — Module {self.order}: {self.title}"


class Lesson(models.Model):
    """An individual lesson within a module."""

    LESSON_TYPE_CHOICES = (
        ('text', 'Text'),
        ('video', 'Video'),
        ('pdf', 'PDF'),
        ('mixed', 'Mixed'),
    )

    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=300, blank=True)
    lesson_type = models.CharField(max_length=10, choices=LESSON_TYPE_CHOICES, default='text')
    content = models.TextField(blank=True, help_text="Text/HTML content of the lesson")
    video_url = models.URLField(blank=True, help_text="URL to video (YouTube, Vimeo, etc.)")
    material_file = models.FileField(upload_to='lesson_materials/', blank=True, null=True)
    duration_minutes = models.PositiveIntegerField(default=0, help_text="Estimated duration in minutes")
    order = models.PositiveIntegerField(default=0)
    is_preview = models.BooleanField(default=False, help_text="Allow non-enrolled users to preview this lesson")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.module.course.title} — {self.title}"
