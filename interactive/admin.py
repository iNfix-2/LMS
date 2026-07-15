from django.contrib import admin
from .models import CoursePathSettings, CoursePrerequisite, LessonPrerequisite, InteractiveContent

@admin.register(CoursePathSettings)
class CoursePathSettingsAdmin(admin.ModelAdmin):
    list_display = ('course', 'enforce_sequential')
    search_fields = ('course__title',)

@admin.register(CoursePrerequisite)
class CoursePrerequisiteAdmin(admin.ModelAdmin):
    list_display = ('course', 'prerequisite_course')
    search_fields = ('course__title', 'prerequisite_course__title')

@admin.register(LessonPrerequisite)
class LessonPrerequisiteAdmin(admin.ModelAdmin):
    list_display = ('lesson', 'prerequisite_lesson')
    search_fields = ('lesson__title', 'prerequisite_lesson__title')

@admin.register(InteractiveContent)
class InteractiveContentAdmin(admin.ModelAdmin):
    list_display = ('lesson', 'content_type', 'is_active', 'created_at')
    list_filter = ('content_type', 'is_active')
    search_fields = ('lesson__title',)
