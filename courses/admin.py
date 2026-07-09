from django.contrib import admin
from .models import Subject, ClassLevel, Course, Module, Lesson


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


@admin.register(ClassLevel)
class ClassLevelAdmin(admin.ModelAdmin):
    list_display = ('name', 'order')
    ordering = ('order',)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'class_level', 'created_by', 'is_published', 'is_free', 'created_at')
    list_filter = ('is_published', 'is_free', 'subject', 'class_level')
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ('title', 'description')


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    fields = ('title', 'lesson_type', 'order', 'is_preview')


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order', 'created_at')
    list_filter = ('course',)
    ordering = ('course', 'order')
    inlines = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'module', 'lesson_type', 'order', 'duration_minutes', 'is_preview')
    list_filter = ('lesson_type', 'is_preview', 'module__course')
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ('title',)
    ordering = ('module__course', 'module__order', 'order')
