from django.contrib import admin
from .models import Assignment, AssignmentSubmission

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'due_date', 'total_marks', 'is_published')
    list_filter = ('is_published', 'course', 'due_date')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}

@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'student', 'score', 'status', 'submitted_at')
    list_filter = ('status', 'assignment__course', 'submitted_at')
    search_fields = ('student__username', 'student__first_name', 'student__last_name', 'assignment__title')
