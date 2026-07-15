from django.db import models
from django.conf import settings

class Resource(models.Model):
    RESOURCE_TYPES = [
        ('pdf', 'PDF Document'),
        ('document', 'Word Document'),
        ('video', 'Video Lecture'),
        ('audio', 'Audio Guide'),
        ('slide', 'Presentation Slide'),
        ('other', 'Other Material'),
    ]
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='library_resources/')
    resource_type = models.CharField(choices=RESOURCE_TYPES, default='pdf', max_length=20)
    is_free = models.BooleanField(default=False, help_text="Allow downloads without course enrollment/payment")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='resources', blank=True, null=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='uploaded_resources')
    download_count = models.PositiveIntegerField(default=0, help_text="Track number of downloads")

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
