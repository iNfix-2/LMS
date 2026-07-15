from django.db import models
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver
from courses.models import Course, Lesson

class CoursePathSettings(models.Model):
    course = models.OneToOneField(Course, on_delete=models.CASCADE, related_name='path_settings')
    enforce_sequential = models.BooleanField(default=False, help_text="Force students to complete lessons in sequence")

    def __str__(self):
        return f"Path Settings for {self.course.title}"

@receiver(post_save, sender=Course)
def create_course_path_settings(sender, instance, created, **kwargs):
    if created:
        CoursePathSettings.objects.create(course=instance)

@receiver(post_save, sender=Course)
def save_course_path_settings(sender, instance, **kwargs):
    if hasattr(instance, 'path_settings'):
        instance.path_settings.save()
    else:
        CoursePathSettings.objects.create(course=instance)


class CoursePrerequisite(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='prerequisites')
    prerequisite_course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='required_for')

    class Meta:
        unique_together = ('course', 'prerequisite_course')

    def clean(self):
        if self.course == self.prerequisite_course:
            raise ValidationError("A course cannot be a prerequisite of itself.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.prerequisite_course.title} is required for {self.course.title}"


class LessonPrerequisite(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='prerequisites')
    prerequisite_lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='required_for')

    class Meta:
        unique_together = ('lesson', 'prerequisite_lesson')

    def clean(self):
        if self.lesson == self.prerequisite_lesson:
            raise ValidationError("A lesson cannot be a prerequisite of itself.")
        if self.lesson.module.course != self.prerequisite_lesson.module.course:
            raise ValidationError("Prerequisite lesson must be in the same course.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.prerequisite_lesson.title} is required for {self.lesson.title}"


class InteractiveContent(models.Model):
    CONTENT_TYPE_CHOICES = (
        ('scorm', 'SCORM 1.2 Package'),
        ('h5p', 'H5P Package'),
        ('h5p_embed', 'H5P Embed URL'),
    )

    lesson = models.OneToOneField(Lesson, on_delete=models.CASCADE, related_name='interactive_content')
    content_type = models.CharField(max_length=15, choices=CONTENT_TYPE_CHOICES)
    package_file = models.FileField(upload_to='interactive_packages/', blank=True, null=True, help_text="SCORM or H5P zip/package file")
    embed_url = models.URLField(blank=True, null=True, help_text="For H5P iframe embed links")
    launch_path = models.CharField(max_length=255, blank=True, null=True, help_text="SCORM entry point (e.g. index.html or path from manifest)")
    extracted_dir = models.CharField(max_length=255, blank=True, null=True, help_text="Relative directory where package is extracted")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Interactive {self.get_content_type_display()} for {self.lesson.title}"
