from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from courses.models import Course, Lesson, Module, ClassLevel, Subject


class AcademicSession(models.Model):
    """Represents an entire school academic year."""
    name = models.CharField(max_length=200)  # Example: 2025/2026 Academic Session
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.name}{' (Current)' if self.is_current else ''}"

    def clean(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError("Start date cannot be after end date.")


class AcademicTerm(models.Model):
    """Represents a term/semester within an academic session."""
    session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE, related_name='terms')
    name = models.CharField(max_length=200)  # Example: First Term
    term_number = models.PositiveIntegerField(default=1)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.session.name} — {self.name}{' (Current)' if self.is_current else ''}"

    def clean(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError("Start date cannot be after end date.")


class AcademicWeek(models.Model):
    """Represents a specific week inside an academic term."""
    WEEK_TYPE_CHOICES = (
        ('normal', 'Normal Classes'),
        ('test', 'Test Week'),
        ('revision', 'Revision Week'),
        ('exam', 'Exam Week'),
        ('break', 'Mid-term Break'),
        ('report', 'Report Cards Week'),
        ('holiday', 'Holiday'),
    )

    term = models.ForeignKey(AcademicTerm, on_delete=models.CASCADE, related_name='weeks')
    week_number = models.PositiveIntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    activity = models.CharField(max_length=300)  # Example: First Test Week
    description = models.TextField(blank=True)
    week_type = models.CharField(max_length=20, choices=WEEK_TYPE_CHOICES, default='normal')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['week_number']
        unique_together = ('term', 'week_number')

    def __str__(self):
        return f"Week {self.week_number} ({self.activity})"


class TimetableSlot(models.Model):
    """Represents a recurring time slot in the school timetable for a class level."""
    DAY_CHOICES = (
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
        ('Sunday', 'Sunday'),
    )

    SLOT_TYPE_CHOICES = (
        ('lesson', 'Lesson'),
        ('recess', 'Recess'),
        ('fellowship', 'Fellowship'),
        ('break', 'Break'),
        ('assembly', 'Assembly'),
        ('other', 'Other'),
    )

    class_level = models.ForeignKey(ClassLevel, on_delete=models.CASCADE, related_name='timetable_slots')
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True, related_name='timetable_slots')
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, related_name='timetable_slots')
    tutor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='timetable_slots')
    day_of_week = models.CharField(max_length=15, choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    title = models.CharField(max_length=200, blank=True)  # Example: Mathematics, Recess
    slot_type = models.CharField(max_length=20, choices=SLOT_TYPE_CHOICES, default='lesson')
    room = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['day_of_week', 'start_time']

    def __str__(self):
        display_title = self.title or (self.subject.name if self.subject else self.get_slot_type_display())
        return f"{self.class_level} — {self.day_of_week} ({self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}): {display_title}"


class LiveClass(models.Model):
    """Represents a scheduled virtual interactive session for a course."""
    PROVIDER_CHOICES = (
        ('zoom', 'Zoom'),
        ('google_meet', 'Google Meet'),
        ('microsoft_teams', 'Microsoft Teams'),
        ('custom', 'Custom Link'),
    )

    STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('live', 'Live Now'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='live_classes')
    module = models.ForeignKey(Module, on_delete=models.SET_NULL, null=True, blank=True, related_name='live_classes')
    lesson = models.ForeignKey(Lesson, on_delete=models.SET_NULL, null=True, blank=True, related_name='live_classes')
    timetable_slot = models.ForeignKey(TimetableSlot, on_delete=models.SET_NULL, null=True, blank=True, related_name='live_classes')
    tutor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='live_classes')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default='custom')
    meeting_link = models.URLField(max_length=500)
    meeting_id = models.CharField(max_length=100, blank=True)
    passcode = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    recording_url = models.URLField(max_length=500, blank=True)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['scheduled_start']

    def __str__(self):
        return f"{self.title} — {self.course.title} ({self.get_status_display()})"


class AttendanceSession(models.Model):
    """Represents a roll-call event/period for tracking student presence."""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='attendance_sessions')
    live_class = models.ForeignKey(LiveClass, on_delete=models.SET_NULL, null=True, blank=True, related_name='attendance_sessions')
    timetable_slot = models.ForeignKey(TimetableSlot, on_delete=models.SET_NULL, null=True, blank=True, related_name='attendance_sessions')
    title = models.CharField(max_length=200)
    date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_attendance_sessions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.title} — {self.course.title} ({self.date})"


class AttendanceRecord(models.Model):
    """Represents the individual student attendance entry in an AttendanceSession."""
    STATUS_CHOICES = (
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused'),
    )

    attendance_session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name='records')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendance_records')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='present')
    marked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='marked_attendance_records')
    marked_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['student__username']
        unique_together = ('attendance_session', 'student')

    def __str__(self):
        return f"{self.student.username} — {self.attendance_session.title}: {self.get_status_display()}"
