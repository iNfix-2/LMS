from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from courses.models import Course, Lesson
from .models import Enrollment, LessonProgress

@login_required
def enroll_in_course(request, course_slug):
    if request.user.is_staff or request.user.is_superuser:
        course = get_object_or_404(Course, slug=course_slug)
    else:
        course = get_object_or_404(Course, slug=course_slug, is_published=True)
        
    from payments.services import user_has_course_access, grant_course_access
    
    if course.is_free:
        grant_course_access(student=request.user, course=course, source='free')
    else:
        if not user_has_course_access(request.user, course):
            messages.warning(request, "This is a paid course. Please complete payment to enroll.")
            return redirect('payments:course_checkout', course_slug=course.slug)
        
    enrollment, created = Enrollment.objects.get_or_create(
        student=request.user,
        course=course,
        defaults={'status': 'active'}
    )
    
    trigger_notification = False
    if created:
        messages.success(request, f"Successfully enrolled in {course.title}!")
        trigger_notification = True
    else:
        if enrollment.status == 'active':
            messages.info(request, "You are already enrolled in this course.")
        else:
            enrollment.status = 'active'
            enrollment.save()
            messages.success(request, f"Re-enrolled in {course.title} successfully!")
            trigger_notification = True

    if trigger_notification:
        try:
            from notifications.services import create_notification
            from accounts.models import StudentProfile
            
            create_notification(
                recipient=request.user,
                title="Course Enrollment Confirmed",
                message=f"You have successfully enrolled in {course.title}.",
                notification_type="enrollment",
                delivery_channel="both",
                related_course=course
            )
            
            profile = StudentProfile.objects.filter(user=request.user).first()
            if profile and profile.guardian:
                create_notification(
                    recipient=profile.guardian,
                    title="Ward Course Enrollment Confirmed",
                    message=f"Your ward {request.user.username} has enrolled in the course: {course.title}.",
                    notification_type="enrollment",
                    delivery_channel="both",
                    related_course=course
                )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Enrollment notification failed: {str(e)}")
            
    return redirect('course_detail', slug=course.slug)


@login_required
def mark_lesson_complete(request, course_slug, lesson_slug):
    enrollment = get_object_or_404(Enrollment, student=request.user, course__slug=course_slug, status='active')
    lesson = get_object_or_404(Lesson, slug=lesson_slug, module__course=enrollment.course)
    
    progress, created = LessonProgress.objects.get_or_create(
        enrollment=enrollment,
        lesson=lesson
    )
    progress.is_completed = True
    progress.completed_at = timezone.now()
    progress.save()
    
    messages.success(request, f"Lesson '{lesson.title}' marked as completed!")
    return redirect('lesson_detail', course_slug=course_slug, lesson_slug=lesson_slug)

@login_required
def student_dashboard(request):
    enrollments = Enrollment.objects.filter(student=request.user, status='active').select_related('course')
    
    try:
        from assessments.models import AssessmentAttempt
        recent_attempts = AssessmentAttempt.objects.filter(student=request.user).select_related('assessment', 'assessment__course').order_by('-started_at')[:5]
    except Exception:
        recent_attempts = []
        
    try:
        from assignments.models import AssignmentSubmission
        recent_submissions = AssignmentSubmission.objects.filter(student=request.user).select_related('assignment', 'assignment__course').order_by('-submitted_at')[:5]
    except Exception:
        recent_submissions = []

    # Sprint 8 Academics Context
    today_slots = []
    upcoming_live = []
    attendance_percentage = 100.0
    try:
        from academics.services import get_student_timetable, get_student_live_classes, calculate_student_attendance_percentage
        from django.utils import timezone
        
        student_timetable = get_student_timetable(request.user)
        today_name = timezone.now().strftime('%A')
        today_slots = student_timetable.get(today_name, [])
        upcoming_live = get_student_live_classes(request.user)[:5]
        attendance_percentage = calculate_student_attendance_percentage(request.user)
    except Exception:
        pass

    return render(request, 'dashboard/student_dashboard.html', {
        'enrollments': enrollments,
        'recent_attempts': recent_attempts,
        'recent_submissions': recent_submissions,
        'today_slots': today_slots,
        'upcoming_live': upcoming_live,
        'attendance_percentage': attendance_percentage,
    })

