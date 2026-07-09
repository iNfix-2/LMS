from django.utils import timezone
from django.db.models import Q
from django.contrib.auth.models import User
from .models import (
    AcademicSession,
    AcademicTerm,
    AcademicWeek,
    TimetableSlot,
    LiveClass,
    AttendanceSession,
    AttendanceRecord
)
from courses.models import ClassLevel, Course


def get_current_academic_session():
    """Returns the current active AcademicSession."""
    return AcademicSession.objects.filter(is_current=True).first()


def get_current_academic_term():
    """Returns the current active AcademicTerm."""
    return AcademicTerm.objects.filter(is_current=True).first()


def get_class_timetable(class_level):
    """Returns active TimetableSlot records for the class level grouped by day of the week."""
    slots = TimetableSlot.objects.filter(class_level=class_level, is_active=True).order_by('start_time')
    
    # We order the days chronologically rather than alphabetically
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    grouped = {day: [] for day in days}
    
    for slot in slots:
        if slot.day_of_week in grouped:
            grouped[slot.day_of_week].append(slot)
            
    return grouped


def get_student_timetable(student):
    """Retrieves the timetable for a student based on their profile class level."""
    if not student or not student.is_authenticated:
        return {}
    
    # Try to import StudentProfile dynamically to prevent circular dependencies
    from accounts.models import StudentProfile
    profile = StudentProfile.objects.filter(user=student).first()
    if not profile or not profile.class_level:
        return {}
        
    class_level = ClassLevel.objects.filter(name__iexact=profile.class_level).first()
    if not class_level:
        return {}
        
    return get_class_timetable(class_level)


def get_tutor_timetable(tutor):
    """Returns the timetable slots assigned directly to the tutor grouped by day."""
    slots = TimetableSlot.objects.filter(tutor=tutor, is_active=True).order_by('start_time')
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    grouped = {day: [] for day in days}
    
    for slot in slots:
        if slot.day_of_week in grouped:
            grouped[slot.day_of_week].append(slot)
            
    return grouped


def get_student_live_classes(student):
    """Returns published upcoming LiveClass records for courses the student is actively enrolled in."""
    if not student or not student.is_authenticated:
        return LiveClass.objects.none()
        
    from enrollments.models import Enrollment
    enrolled_course_ids = Enrollment.objects.filter(student=student, status='active').values_list('course_id', flat=True)
    
    now = timezone.now()
    return LiveClass.objects.filter(
        course_id__in=enrolled_course_ids,
        is_published=True,
        scheduled_end__gte=now
    ).order_by('scheduled_start')


def get_tutor_live_classes(tutor):
    """Returns LiveClass records where tutor is the assigned tutor (staff/admin see all)."""
    if not tutor or not tutor.is_authenticated:
        return LiveClass.objects.none()
        
    now = timezone.now()
    if tutor.is_staff or tutor.is_superuser:
        return LiveClass.objects.filter(scheduled_end__gte=now).order_by('scheduled_start')
        
    return LiveClass.objects.filter(tutor=tutor, scheduled_end__gte=now).order_by('scheduled_start')


def calculate_student_attendance_percentage(student, course=None):
    """Calculates present + late count against total attendance sessions."""
    records = AttendanceRecord.objects.filter(student=student)
    if course:
        records = records.filter(attendance_session__course=course)
        
    total = records.count()
    if total == 0:
        return 100.0  # safe default
        
    present_or_late = records.filter(status__in=['present', 'late']).count()
    return round((present_or_late / total) * 100.0, 1)
