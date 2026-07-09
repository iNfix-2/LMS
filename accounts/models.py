from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    """Extended profile for every user with role-based access."""

    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('tutor', 'Tutor'),
        ('student', 'Student'),
        ('guardian', 'Guardian'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    phone = models.CharField(max_length=20, blank=True)
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"


class StudentProfile(models.Model):
    """Additional profile data specific to students."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    guardian = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='wards',
        limit_choices_to={'profile__role': 'guardian'},
    )
    class_level = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Student: {self.user.get_full_name() or self.user.username}"


class TutorProfile(models.Model):
    """Additional profile data specific to tutors."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='tutor_profile')
    bio = models.TextField(blank=True)
    subjects = models.CharField(max_length=500, blank=True, help_text="Comma-separated list of subjects")
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        status = "Approved" if self.is_approved else "Pending"
        return f"Tutor: {self.user.get_full_name() or self.user.username} ({status})"
