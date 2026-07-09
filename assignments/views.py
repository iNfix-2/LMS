from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from courses.models import Course
from enrollments.models import Enrollment
from .models import Assignment, AssignmentSubmission

def check_enrollment(user, course):
    if user.is_staff or user.is_superuser:
        return True
    return Enrollment.objects.filter(student=user, course=course, status='active').exists()

@login_required
def course_assignments(request, course_slug):
    if request.user.is_staff or request.user.is_superuser:
        course = get_object_or_404(Course, slug=course_slug)
    else:
        course = get_object_or_404(Course, slug=course_slug, is_published=True)
        
    if not check_enrollment(request.user, course):
        messages.error(request, "You must be enrolled in this course to view assignments.")
        return redirect('course_detail', slug=course.slug)
        
    assignments = Assignment.objects.filter(course=course, is_published=True)
    return render(request, 'assignments/course_assignments.html', {
        'course': course,
        'assignments': assignments,
    })

@login_required
def assignment_detail(request, course_slug, assignment_slug): # Note: task says: `/assignments/<slug:course_slug>/<slug:assignment_slug>/` -> name parameter is assignment_slug
    if request.user.is_staff or request.user.is_superuser:
        course = get_object_or_404(Course, slug=course_slug)
    else:
        course = get_object_or_404(Course, slug=course_slug, is_published=True)
        
    if not check_enrollment(request.user, course):
        messages.error(request, "You must be enrolled in this course to view this assignment.")
        return redirect('course_detail', slug=course.slug)
        
    assignment = get_object_or_404(Assignment, course=course, slug=assignment_slug, is_published=True)
    submission = AssignmentSubmission.objects.filter(assignment=assignment, student=request.user).first()
    
    return render(request, 'assignments/assignment_detail.html', {
        'course': course,
        'assignment': assignment,
        'submission': submission,
    })

@login_required
def submit_assignment(request, course_slug, assignment_slug):
    if request.method != 'POST':
        return redirect('course_list')
        
    if request.user.is_staff or request.user.is_superuser:
        course = get_object_or_404(Course, slug=course_slug)
    else:
        course = get_object_or_404(Course, slug=course_slug, is_published=True)
        
    if not check_enrollment(request.user, course):
        messages.error(request, "You must be enrolled in this course to submit this assignment.")
        return redirect('course_detail', slug=course.slug)
        
    assignment = get_object_or_404(Assignment, course=course, slug=assignment_slug, is_published=True)
    
    # Check if due date has passed
    if assignment.due_date and assignment.due_date < timezone.now():
        messages.error(request, "The due date for this assignment has passed. Submissions are closed.")
        return redirect('assignment_detail', course_slug=course.slug, assignment_slug=assignment.slug)
        
    answer_text = request.POST.get('answer_text', '').strip()
    submitted_file = request.FILES.get('submitted_file')
    
    submission, created = AssignmentSubmission.objects.get_or_create(
        assignment=assignment,
        student=request.user,
        defaults={'status': 'submitted'}
    )
    
    submission.answer_text = answer_text
    if submitted_file:
        submission.submitted_file = submitted_file
    submission.submitted_at = timezone.now()
    
    # If it was already marked, reset to submitted when student updates it
    if not created:
        submission.status = 'submitted'
        
    submission.save()
    
    # Trigger notifications to tutors
    try:
        from notifications.services import create_notification
        
        # Get all recipient tutors (creator + assigned)
        tutors = set()
        if assignment.course.created_by:
            tutors.add(assignment.course.created_by)
        for t in assignment.course.assigned_tutors.all():
            tutors.add(t)
            
        for tutor in tutors:
            create_notification(
                recipient=tutor,
                title=f"New Assignment Submission: {assignment.title}",
                message=f"Student {request.user.username} has submitted a response for the assignment: {assignment.title} in course {assignment.course.title}.",
                notification_type="assignment",
                delivery_channel="both",
                related_course=assignment.course
            )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Assignment submission notification failed: {str(e)}")
    
    if created:
        messages.success(request, f"Assignment '{assignment.title}' submitted successfully!")
    else:
        messages.success(request, f"Assignment '{assignment.title}' submission updated successfully!")
        
    return redirect('assignment_submission_detail', submission_id=submission.id)

@login_required
def assignment_submission_detail(request, submission_id):
    submission = get_object_or_404(AssignmentSubmission, id=submission_id)
    
    is_guardian = False
    try:
        from accounts.models import StudentProfile
        is_guardian = StudentProfile.objects.filter(user=submission.student, guardian=request.user).exists()
    except Exception:
        pass

    if not (request.user == submission.student or 
            request.user.is_staff or 
            request.user.is_superuser or 
            submission.assignment.course.can_be_managed_by(request.user) or
            is_guardian):
        messages.error(request, "You are not authorized to view this submission.")
        return redirect('course_list')
        
    return render(request, 'assignments/submission_detail.html', {
        'submission': submission,
        'assignment': submission.assignment,
        'course': submission.assignment.course,
    })

from accounts.decorators import role_required

@login_required
@role_required(allowed_roles=['tutor', 'admin'])
def mark_assignment_submission(request, submission_id):
    submission = get_object_or_404(AssignmentSubmission, id=submission_id)
    course = submission.assignment.course
    
    if not course.can_be_managed_by(request.user):
        messages.error(request, "You do not have permission to mark this assignment.")
        return redirect('tutor_dashboard')
        
    if request.method == 'POST':
        raw_score = request.POST.get('score', '0')
        feedback = request.POST.get('feedback', '').strip()
        status = request.POST.get('status', 'marked')
        
        try:
            score = float(raw_score)
        except ValueError:
            score = 0.0
            
        max_marks = submission.assignment.total_marks
        if score > max_marks:
            messages.error(request, f"Score cannot exceed maximum assignment marks of {max_marks}.")
            return render(request, 'assignments/mark_submission.html', {
                'submission': submission,
                'assignment': submission.assignment,
                'course': course,
                'score_val': score,
                'feedback_val': feedback,
                'status_val': status,
            })
            
        if score < 0:
            score = 0.0
            
        submission.score = score
        submission.feedback = feedback
        submission.status = status
        submission.save()

        # Trigger grading notifications to student and guardian
        try:
            from notifications.services import create_notification
            from accounts.models import StudentProfile
            
            # Notify student
            create_notification(
                recipient=submission.student,
                title=f"Assignment Graded: {submission.assignment.title}",
                message=f"Your submission for assignment '{submission.assignment.title}' in course {course.title} has been graded. Score: {score}/{max_marks}.",
                notification_type="assignment",
                delivery_channel="both",
                related_course=course
            )
            
            # Notify guardian if linked
            profile = StudentProfile.objects.filter(user=submission.student).first()
            if profile and profile.guardian:
                create_notification(
                    recipient=profile.guardian,
                    title=f"Ward Assignment Graded: {submission.assignment.title}",
                    message=f"Your ward {submission.student.username}'s submission for assignment '{submission.assignment.title}' has been graded. Score: {score}/{max_marks}.",
                    notification_type="assignment",
                    delivery_channel="both",
                    related_course=course
                )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Assignment grading notification failed: {str(e)}")
            
        messages.success(request, f"Assignment submission for {submission.student.username} graded successfully!")
        return redirect('assignment_submission_detail', submission_id=submission.id)
        
    return render(request, 'assignments/mark_submission.html', {
        'submission': submission,
        'assignment': submission.assignment,
        'course': course,
    })
