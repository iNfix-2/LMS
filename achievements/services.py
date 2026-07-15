import uuid
from django.utils import timezone
from django.core.files.base import ContentFile
from django.conf import settings
from .models import Badge, CourseCompletionRule, StudentAchievement, Certificate
from enrollments.models import Enrollment
from notifications.pdf import render_to_pdf

def check_and_award_course_completion(student, course):
    """
    Checks if a student has met all completion rules for a course.
    If met, awards the completion badge and generates a certificate.
    """
    # 1. Check if certificate already exists
    if Certificate.objects.filter(student=student, course=course).exists():
        return True, "Already completed"

    # 2. Get the enrollment
    enrollment = Enrollment.objects.filter(student=student, course=course, status='active').first()
    if not enrollment:
        # Check if already completed enrollment exists
        enrollment = Enrollment.objects.filter(student=student, course=course, status='completed').first()
        if not enrollment:
            return False, "Not enrolled in this course"

    # 3. Get or create completion rule
    rule = CourseCompletionRule.objects.filter(course=course).first()
    
    # 4. Check progress percentage
    progress = enrollment.progress_percentage
    min_progress = rule.min_progress_percentage if rule else 100
    if progress < min_progress:
        return False, f"Progress {progress}% is below required {min_progress}%"

    # 5. Check assessments
    if rule and rule.require_all_assessments_passed:
        published_assessments = course.assessments.filter(is_published=True)
        from assessments.models import AssessmentAttempt
        for assess in published_assessments:
            # Check if there is any passed attempt (percentage >= pass_mark)
            passed = AssessmentAttempt.objects.filter(
                student=student, 
                assessment=assess, 
                status='submitted',
                percentage__gte=assess.pass_mark
            ).exists()
            if not passed:
                return False, f"Did not pass assessment: {assess.title}"

    # 6. Check assignments
    if rule and rule.require_all_assignments_submitted:
        published_assignments = course.assignments.filter(is_published=True)
        from assignments.models import AssignmentSubmission
        for assign in published_assignments:
            submitted = AssignmentSubmission.objects.filter(
                student=student,
                assignment=assign,
                status__in=['submitted', 'marked', 'returned']
            ).exists()
            if not submitted:
                return False, f"Did not submit assignment: {assign.title}"

    # 7. Check attendance
    if rule and rule.min_attendance_percentage is not None:
        from academics.services import calculate_student_attendance_percentage
        attendance = calculate_student_attendance_percentage(student, course)
        if attendance < rule.min_attendance_percentage:
            return False, f"Attendance {attendance}% is below required {rule.min_attendance_percentage}%"

    # 8. Rules satisfied! Award completion
    # Get or create course completion badge
    badge, _ = Badge.objects.get_or_create(
        badge_type='course_completed',
        title=f"{course.title} Completion Badge",
        defaults={
            'description': f"Awarded to students who successfully completed all requirements for {course.title}.",
        }
    )

    # Award Badge
    achievement, achievement_created = StudentAchievement.objects.get_or_create(
        student=student,
        badge=badge,
        course=course
    )

    # Update Enrollment Status to Completed
    if enrollment.status != 'completed':
        enrollment.status = 'completed'
        enrollment.completed_at = timezone.now()
        enrollment.save(update_fields=['status', 'completed_at'])

    # Create Certificate
    cert_number = f"EDU-CERT-{uuid.uuid4().hex[:8].upper()}"
    verif_code = uuid.uuid4().hex[:12].upper()
    
    certificate, created = Certificate.objects.get_or_create(
        student=student,
        course=course,
        defaults={
            'certificate_number': cert_number,
            'verification_code': verif_code,
            'issued_at': timezone.now()
        }
    )

    # Generate Certificate PDF
    if created or not certificate.pdf_file:
        context = {
            'certificate': certificate,
            'student': student,
            'course': course,
            'title': f"Certificate of Completion - {student.get_full_name() or student.username}"
        }
        try:
            pdf_bytes = render_to_pdf('achievements/certificate_pdf.html', context)
            filename = f"certificate_{certificate.certificate_number}.pdf"
            certificate.pdf_file.save(filename, ContentFile(pdf_bytes))
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error generating certificate PDF: {str(e)}")

    # Send Notification/Email
    try:
        from notifications.models import Notification
        Notification.objects.create(
            recipient=student,
            title="Course Completed!",
            message=f"Congratulations! You have successfully completed the course '{course.title}' and earned a certificate and completion badge.",
            notification_type='system',
            delivery_channel='both',
            related_course=course
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Notification creation failed: {str(e)}")

    return True, "Course successfully completed and achievements awarded!"
