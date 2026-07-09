from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Q
from accounts.decorators import role_required, is_admin_user, is_tutor_user, is_student_user, is_guardian_user
from courses.models import Course, Lesson
from enrollments.models import Enrollment, LessonProgress
from assessments.models import AssessmentAttempt, StudentAnswer, Assessment
from assignments.models import AssignmentSubmission, Assignment
from accounts.models import StudentProfile, UserProfile
from .models import StudentProgressReport
from .services import (
    get_student_course_progress,
    get_course_assessment_average,
    get_course_assignment_average,
    get_pending_assessment_marking_count,
    get_pending_assignment_marking_count
)


@login_required
@role_required(allowed_roles=['student'])
def student_report_dashboard(request):
    enrollments = Enrollment.objects.filter(student=request.user, status='active').select_related('course')
    
    course_data = []
    for enr in enrollments:
        progress = enr.progress_percentage
        assess_avg = get_course_assessment_average(request.user, enr.course)
        assign_avg = get_course_assignment_average(request.user, enr.course)
        course_data.append({
            'enrollment': enr,
            'course': enr.course,
            'progress': progress,
            'assessment_average': assess_avg,
            'assignment_average': assign_avg,
        })
        
    reports = StudentProgressReport.objects.filter(student=request.user).order_by('-created_at')
    
    return render(request, 'reports/student_report_dashboard.html', {
        'course_data': course_data,
        'reports': reports,
    })


@login_required
@role_required(allowed_roles=['guardian', 'admin'])
def guardian_dashboard(request):
    # Fetch wards linked to this guardian
    if request.user.is_staff or request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'admin'):
        wards = StudentProfile.objects.all().select_related('user')
    else:
        wards = StudentProfile.objects.filter(guardian=request.user).select_related('user')
        
    ward_data = []
    for ward_profile in wards:
        student = ward_profile.user
        enrollments = Enrollment.objects.filter(student=student, status='active').select_related('course')
        
        student_courses = []
        for enr in enrollments:
            progress = enr.progress_percentage
            assess_avg = get_course_assessment_average(student, enr.course)
            assign_avg = get_course_assignment_average(student, enr.course)
            
            # Fetch recent assignments submissions
            recent_subs = AssignmentSubmission.objects.filter(student=student, assignment__course=enr.course).order_by('-submitted_at')[:3]
            
            student_courses.append({
                'enrollment': enr,
                'course': enr.course,
                'progress': progress,
                'assessment_average': assess_avg,
                'assignment_average': assign_avg,
                'recent_submissions': recent_subs,
            })
            
        reports = StudentProgressReport.objects.filter(student=student).order_by('-created_at')[:5]
        
        ward_data.append({
            'profile': ward_profile,
            'student': student,
            'courses': student_courses,
            'reports': reports,
        })
        
    return render(request, 'reports/guardian_dashboard.html', {
        'ward_data': ward_data,
    })


@login_required
@role_required(allowed_roles=['tutor', 'admin'])
def tutor_dashboard(request):
    user = request.user
    if user.is_staff or user.is_superuser or (hasattr(user, 'profile') and user.profile.role == 'admin'):
        courses = Course.objects.all()
    else:
        courses = Course.objects.filter(Q(created_by=user) | Q(assigned_tutors=user)).distinct()
        
    course_list = []
    for course in courses:
        enrolled_count = course.get_enrolled_students_count()
        modules_count = course.modules.count()
        lessons_count = Lesson.objects.filter(module__course=course).count()
        assessments_count = course.assessments.filter(is_published=True).count()
        assignments_count = course.assignments.filter(is_published=True).count()
        
        pending_theory = get_pending_assessment_marking_count(course)
        pending_assignments = get_pending_assignment_marking_count(course)
        
        course_list.append({
            'course': course,
            'enrolled_count': enrolled_count,
            'modules_count': modules_count,
            'lessons_count': lessons_count,
            'assessments_count': assessments_count,
            'assignments_count': assignments_count,
            'pending_theory': pending_theory,
            'pending_assignments': pending_assignments,
        })
        
    # Also fetch general statistics for this tutor
    scheduled_live = []
    try:
        from academics.services import get_tutor_live_classes
        scheduled_live = get_tutor_live_classes(user)[:5]
    except Exception:
        pass

    return render(request, 'reports/tutor_dashboard.html', {
        'course_list': course_list,
        'scheduled_live': scheduled_live,
    })



@login_required
@role_required(allowed_roles=['tutor', 'admin'])
def course_learners(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug)
    
    if not course.can_be_managed_by(request.user):
        messages.error(request, "You do not have permission to view learners for this course.")
        return redirect('tutor_dashboard')
        
    enrollments = Enrollment.objects.filter(course=course, status='active').select_related('student')
    
    learner_data = []
    for enr in enrollments:
        student = enr.student
        progress = enr.progress_percentage
        assess_avg = get_course_assessment_average(student, course)
        assign_avg = get_course_assignment_average(student, course)
        
        # Last accessed lesson
        last_progress = LessonProgress.objects.filter(enrollment=enr, is_completed=True).order_by('-completed_at').first()
        last_lesson = last_progress.lesson if last_progress else None
        
        # Latest generated progress report
        latest_report = StudentProgressReport.objects.filter(student=student, course=course).order_by('-created_at').first()
        
        learner_data.append({
            'enrollment': enr,
            'student': student,
            'progress': progress,
            'assessment_average': assess_avg,
            'assignment_average': assign_avg,
            'last_lesson': last_lesson,
            'latest_report': latest_report,
        })
        
    # Fetch pending attempts to mark for this course
    pending_attempts = AssessmentAttempt.objects.filter(
        assessment__course=course,
        status='submitted',
        answers__question__question_type__in=['short_answer', 'theory'],
        answers__is_graded=False
    ).distinct().select_related('student', 'assessment')
    
    # Fetch pending assignments to mark for this course
    pending_submissions = AssignmentSubmission.objects.filter(
        assignment__course=course,
        status='submitted'
    ).select_related('student', 'assignment')
        
    return render(request, 'reports/course_learners.html', {
        'course': course,
        'learner_data': learner_data,
        'pending_attempts': pending_attempts,
        'pending_submissions': pending_submissions,
    })


@login_required
@role_required(allowed_roles=['admin'])
def admin_lms_dashboard(request):
    total_students = UserProfile.objects.filter(role='student').count()
    total_guardians = UserProfile.objects.filter(role='guardian').count()
    total_tutors = UserProfile.objects.filter(role='tutor').count()
    total_courses = Course.objects.count()
    total_enrollments = Enrollment.objects.filter(status='active').count()
    total_lessons = Lesson.objects.count()
    total_attempts = AssessmentAttempt.objects.filter(status='submitted').count()
    total_submissions = AssignmentSubmission.objects.filter(status='submitted').count()
    
    # Calculate pending marking total
    pending_theory_marking = AssessmentAttempt.objects.filter(
        status='submitted',
        answers__question__question_type__in=['short_answer', 'theory'],
        answers__is_graded=False
    ).distinct().count()
    
    pending_assignment_marking = AssignmentSubmission.objects.filter(status='submitted').count()
    total_pending_markings = pending_theory_marking + pending_assignment_marking
    
    recent_enrollments = Enrollment.objects.order_by('-enrolled_at').select_related('student', 'course')[:5]
    recent_submissions = AssignmentSubmission.objects.order_by('-submitted_at').select_related('student', 'assignment')[:5]
    
    return render(request, 'reports/admin_lms_dashboard.html', {
        'total_students': total_students,
        'total_guardians': total_guardians,
        'total_tutors': total_tutors,
        'total_courses': total_courses,
        'total_enrollments': total_enrollments,
        'total_lessons': total_lessons,
        'total_attempts': total_attempts,
        'total_submissions': total_submissions,
        'total_pending_markings': total_pending_markings,
        'recent_enrollments': recent_enrollments,
        'recent_submissions': recent_submissions,
    })


@login_required
@role_required(allowed_roles=['tutor', 'admin'])
def generate_student_course_report(request, student_id, course_slug):
    student = get_object_or_404(User, id=student_id)
    course = get_object_or_404(Course, slug=course_slug)
    
    if not course.can_be_managed_by(request.user):
        messages.error(request, "You do not have permission to generate reports for this course.")
        return redirect('tutor_dashboard')
        
    # Check if student is enrolled
    enrollment = Enrollment.objects.filter(student=student, course=course).first()
    if not enrollment:
        messages.error(request, "This student is not enrolled in the course.")
        return redirect('course_learners', course_slug=course.slug)
        
    title = f"Progress Report - {student.get_full_name() or student.username} - {course.title}"
    
    # Create new report instance
    report = StudentProgressReport(
        student=student,
        course=course,
        generated_by=request.user,
        title=title,
    )
    report.calculate_report()

    # Trigger PDF Generation & Notifications
    try:
        from notifications.pdf import generate_progress_report_pdf
        from notifications.services import create_notification
        from accounts.models import StudentProfile
        
        generate_progress_report_pdf(report)
        
        create_notification(
            recipient=student,
            title="Progress Report Generated",
            message=f"A new progress report ({report.title}) has been generated for you by {request.user.username}.",
            notification_type="report",
            delivery_channel="both",
            related_report=report
        )
        
        profile = StudentProfile.objects.filter(user=student).first()
        if profile and profile.guardian:
            create_notification(
                recipient=profile.guardian,
                title="Ward Progress Report Generated",
                message=f"A new progress report ({report.title}) has been generated for your ward {student.username}.",
                notification_type="report",
                delivery_channel="both",
                related_report=report
            )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Report notification failed: {str(e)}")
    
    messages.success(request, f"Progress report successfully generated for {student.username}!")
    return redirect('student_progress_report_detail', report_id=report.id)


@login_required
def report_detail(request, report_id):
    report = get_object_or_404(StudentProgressReport, id=report_id)
    user = request.user
    
    # Authorization checks
    can_view = False
    if user.is_staff or user.is_superuser:
        can_view = True
    elif hasattr(user, 'profile') and user.profile.role == 'admin':
        can_view = True
    elif user == report.student:
        can_view = True
    elif hasattr(user, 'profile') and user.profile.role == 'guardian':
        # Check if report student is ward of guardian
        if StudentProfile.objects.filter(user=report.student, guardian=user).exists():
            can_view = True
    elif hasattr(user, 'profile') and user.profile.role == 'tutor':
        if report.course.can_be_managed_by(user):
            can_view = True
            
    if not can_view:
        messages.error(request, "You are not authorized to view this progress report.")
        return redirect('homepage')
        
    # Check if POST for updating comments
    if request.method == 'POST':
        # Tutor can update tutor comments, Guardian can update guardian comments
        is_tutor = hasattr(user, 'profile') and user.profile.role == 'tutor' and report.course.can_be_managed_by(user)
        is_guardian = hasattr(user, 'profile') and user.profile.role == 'guardian' and StudentProfile.objects.filter(user=report.student, guardian=user).exists()
        is_admin = user.is_staff or user.is_superuser or (hasattr(user, 'profile') and user.profile.role == 'admin')
        
        if is_tutor or is_admin:
            report.tutor_comment = request.POST.get('tutor_comment', '').strip()
        if is_guardian or is_admin:
            report.guardian_comment = request.POST.get('guardian_comment', '').strip()
            
        report.save()
        messages.success(request, "Comments updated successfully.")
        return redirect('student_progress_report_detail', report_id=report.id)
        
    return render(request, 'reports/student_progress_report_detail.html', {
        'report': report,
        'student': report.student,
        'course': report.course,
    })
