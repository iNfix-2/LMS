from django.contrib import admin
from .models import (
    AcademicSession,
    AcademicTerm,
    AcademicWeek,
    TimetableSlot,
    LiveClass,
    AttendanceSession,
    AttendanceRecord
)


@admin.register(AcademicSession)
class AcademicSessionAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'is_current')
    list_filter = ('is_current',)
    search_fields = ('name',)


@admin.register(AcademicTerm)
class AcademicTermAdmin(admin.ModelAdmin):
    list_display = ('session', 'name', 'start_date', 'end_date', 'is_current')
    list_filter = ('is_current', 'session')
    search_fields = ('name', 'session__name')


@admin.register(AcademicWeek)
class AcademicWeekAdmin(admin.ModelAdmin):
    list_display = ('term', 'week_number', 'start_date', 'end_date', 'week_type', 'activity')
    list_filter = ('week_type', 'term')
    search_fields = ('activity', 'description')


@admin.register(TimetableSlot)
class TimetableSlotAdmin(admin.ModelAdmin):
    list_display = ('class_level', 'day_of_week', 'start_time', 'end_time', 'title', 'subject', 'tutor', 'slot_type')
    list_filter = ('day_of_week', 'slot_type', 'class_level', 'subject', 'tutor')
    search_fields = ('title', 'room')


@admin.register(LiveClass)
class LiveClassAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'tutor', 'scheduled_start', 'scheduled_end', 'provider', 'status', 'is_published')
    list_filter = ('provider', 'status', 'is_published', 'course', 'tutor')
    search_fields = ('title', 'description', 'meeting_id')


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'date', 'start_time', 'end_time', 'created_by')
    list_filter = ('date', 'course', 'created_by')
    search_fields = ('title',)


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('attendance_session', 'student', 'status', 'marked_by', 'marked_at')
    list_filter = ('status', 'marked_at', 'attendance_session__course')
    search_fields = ('student__username', 'student__email', 'notes')
