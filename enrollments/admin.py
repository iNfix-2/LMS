from django.contrib import admin
from .models import Enrollment, LessonProgress


class LessonProgressInline(admin.TabularInline):
    model = LessonProgress
    extra = 0
    readonly_fields = ('last_accessed_at',)


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'status', 'enrolled_at', 'completed_at')
    list_filter = ('status', 'course')
    search_fields = ('student__username', 'student__first_name', 'student__last_name', 'course__title')
    inlines = [LessonProgressInline]


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'lesson', 'is_completed', 'completed_at', 'last_accessed_at')
    list_filter = ('is_completed',)
    search_fields = ('enrollment__student__username', 'lesson__title')
