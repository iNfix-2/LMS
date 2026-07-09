from django.contrib import admin
from .models import StudentProgressReport


@admin.register(StudentProgressReport)
class StudentProgressReportAdmin(admin.ModelAdmin):
    list_display = (
        'student',
        'course',
        'lesson_progress_percentage',
        'assessment_average',
        'assignment_average',
        'overall_percentage',
        'created_at',
    )
    list_filter = (
        'course',
        'created_at',
    )
    search_fields = (
        'student__username',
        'student__email',
        'course__title',
    )
