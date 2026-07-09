from django.contrib import admin
from .models import UserProfile, StudentProfile, TutorProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone', 'created_at')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'phone')


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'guardian', 'class_level', 'date_of_birth', 'created_at')
    list_filter = ('class_level',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name')


@admin.register(TutorProfile)
class TutorProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'subjects', 'is_approved', 'created_at')
    list_filter = ('is_approved',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'subjects')
