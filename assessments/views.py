from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from courses.models import Course
from enrollments.models import Enrollment
from .models import Assessment, Question, Choice, AssessmentAttempt, StudentAnswer

def check_enrollment(user, course):
    if user.is_staff or user.is_superuser:
        return True
    return Enrollment.objects.filter(student=user, course=course, status='active').exists()

@login_required
def course_assessments(request, course_slug):
    if request.user.is_staff or request.user.is_superuser:
        course = get_object_or_404(Course, slug=course_slug)
    else:
        course = get_object_or_404(Course, slug=course_slug, is_published=True)
        
    if not check_enrollment(request.user, course):
        messages.error(request, "You must be enrolled in this course to view assessments.")
        return redirect('course_detail', slug=course.slug)
        
    assessments = Assessment.objects.filter(course=course, is_published=True)
    return render(request, 'assessments/course_assessments.html', {
        'course': course,
        'assessments': assessments,
    })

@login_required
def assessment_detail(request, course_slug, assessment_slug):
    if request.user.is_staff or request.user.is_superuser:
        course = get_object_or_404(Course, slug=course_slug)
    else:
        course = get_object_or_404(Course, slug=course_slug, is_published=True)
        
    if not check_enrollment(request.user, course):
        messages.error(request, "You must be enrolled in this course to view this assessment.")
        return redirect('course_detail', slug=course.slug)
        
    assessment = get_object_or_404(Assessment, course=course, slug=assessment_slug, is_published=True)
    attempts = AssessmentAttempt.objects.filter(assessment=assessment, student=request.user)
    
    return render(request, 'assessments/assessment_detail.html', {
        'course': course,
        'assessment': assessment,
        'attempts': attempts,
    })

@login_required
def start_assessment(request, course_slug, assessment_slug):
    if request.user.is_staff or request.user.is_superuser:
        course = get_object_or_404(Course, slug=course_slug)
    else:
        course = get_object_or_404(Course, slug=course_slug, is_published=True)
        
    if not check_enrollment(request.user, course):
        messages.error(request, "You must be enrolled in this course to take this assessment.")
        return redirect('course_detail', slug=course.slug)
        
    assessment = get_object_or_404(Assessment, course=course, slug=assessment_slug, is_published=True)
    
    # Get or create attempt in progress
    attempt, created = AssessmentAttempt.objects.get_or_create(
        assessment=assessment,
        student=request.user,
        status='in_progress',
        defaults={'started_at': timezone.now()}
    )
    
    if created:
        messages.success(request, f"Started assessment: {assessment.title}")
    
    questions = assessment.questions.all().prefetch_related('choices')
    
    return render(request, 'assessments/take_assessment.html', {
        'course': course,
        'assessment': assessment,
        'attempt': attempt,
        'questions': questions,
    })

@login_required
def submit_assessment(request, course_slug, assessment_slug):
    if request.method != 'POST':
        return redirect('course_list')
        
    if request.user.is_staff or request.user.is_superuser:
        course = get_object_or_404(Course, slug=course_slug)
    else:
        course = get_object_or_404(Course, slug=course_slug, is_published=True)
        
    if not check_enrollment(request.user, course):
        messages.error(request, "You must be enrolled in this course to submit this assessment.")
        return redirect('course_detail', slug=course.slug)
        
    assessment = get_object_or_404(Assessment, course=course, slug=assessment_slug, is_published=True)
    attempt = get_object_or_404(AssessmentAttempt, assessment=assessment, student=request.user, status='in_progress')
    
    # Delete any existing answers for this attempt in case they are re-submitting an active session
    attempt.answers.all().delete()
    
    questions = assessment.questions.all()
    for question in questions:
        field_name = f"question_{question.id}"
        ans_text = request.POST.get(field_name, '').strip()
        
        selected_choice = None
        text_answer = ""
        
        if question.question_type == 'objective':
            if ans_text:
                selected_choice = Choice.objects.filter(question=question, id=ans_text).first()
        elif question.question_type == 'true_false':
            if ans_text:
                # selected_choice can match choice matching text_answer
                selected_choice = Choice.objects.filter(question=question, choice_text__iexact=ans_text).first()
                text_answer = ans_text
        else:
            # theory or short answer
            text_answer = ans_text
            
        StudentAnswer.objects.create(
            attempt=attempt,
            question=question,
            selected_choice=selected_choice,
            text_answer=text_answer
        )
        
    # Calculate score
    attempt.calculate_score()
    
    # Trigger notifications
    try:
        from notifications.services import create_notification
        from accounts.models import StudentProfile
        
        pending_marking = attempt.answers.filter(question__question_type__in=['short_answer', 'theory'], is_graded=False).exists()
        
        # 1. Notify student
        if pending_marking:
            msg = f"You submitted the assessment '{assessment.title}'. Your response is awaiting manual marking by your tutor."
        else:
            msg = f"You completed the assessment '{assessment.title}'. Score: {attempt.percentage}% ({attempt.score_obtained}/{attempt.total_score})."
            
        create_notification(
            recipient=request.user,
            title=f"Assessment Submitted: {assessment.title}",
            message=msg,
            notification_type="assessment",
            delivery_channel="both",
            related_course=course
        )
        
        # 2. Notify guardian
        if pending_marking:
            g_msg = f"Your ward {request.user.username} submitted the assessment '{assessment.title}'. The response is awaiting manual marking by the tutor."
        else:
            g_msg = f"Your ward {request.user.username} completed the assessment '{assessment.title}'. Score: {attempt.percentage}%."
            
        profile = StudentProfile.objects.filter(user=request.user).first()
        if profile and profile.guardian:
            create_notification(
                recipient=profile.guardian,
                title=f"Ward Assessment Submitted: {assessment.title}",
                message=g_msg,
                notification_type="assessment",
                delivery_channel="both",
                related_course=course
            )
            
        # 3. Notify tutor(s)
        tutors = set()
        if course.created_by:
            tutors.add(course.created_by)
        for t in course.assigned_tutors.all():
            tutors.add(t)
            
        for tutor in tutors:
            t_msg = f"Student {request.user.username} has submitted the assessment: {assessment.title}."
            if pending_marking:
                t_msg += " This assessment requires manual marking."
            create_notification(
                recipient=tutor,
                title=f"Student Assessment Submission: {assessment.title}",
                message=t_msg,
                notification_type="assessment",
                delivery_channel="both",
                related_course=course
            )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Assessment submission notification failed: {str(e)}")

    messages.success(request, f"Assessment '{assessment.title}' submitted successfully!")
    return redirect('assessment_result', attempt_id=attempt.id)

@login_required
def assessment_result(request, attempt_id):
    attempt = get_object_or_404(AssessmentAttempt, id=attempt_id)
    
    is_guardian = False
    try:
        from accounts.models import StudentProfile
        is_guardian = StudentProfile.objects.filter(user=attempt.student, guardian=request.user).exists()
    except Exception:
        pass

    if not (request.user == attempt.student or 
            request.user.is_staff or 
            request.user.is_superuser or 
            attempt.assessment.course.can_be_managed_by(request.user) or
            is_guardian):
        messages.error(request, "You are not authorized to view these results.")
        return redirect('course_list')
        
    passed = attempt.percentage >= attempt.assessment.pass_mark
    answers = attempt.answers.all().select_related('question').prefetch_related('question__choices')
    
    # Check if there are any pending manual marks
    pending_marking = attempt.answers.filter(question__question_type__in=['short_answer', 'theory'], is_graded=False).exists()
    
    return render(request, 'assessments/assessment_result.html', {
        'attempt': attempt,
        'assessment': attempt.assessment,
        'course': attempt.assessment.course,
        'passed': passed,
        'answers': answers,
        'pending_marking': pending_marking,
    })

from accounts.decorators import role_required

@login_required
@role_required(allowed_roles=['tutor', 'admin'])
def mark_attempt_view(request, attempt_id):
    attempt = get_object_or_404(AssessmentAttempt, id=attempt_id)
    course = attempt.assessment.course
    
    if not course.can_be_managed_by(request.user):
        messages.error(request, "You do not have permission to mark this assessment.")
        return redirect('tutor_dashboard')
        
    answers = attempt.answers.all().select_related('question')
    
    if request.method == 'POST':
        for ans in answers:
            if ans.question.question_type in ['short_answer', 'theory']:
                mark_field = f"mark_{ans.id}"
                feedback_field = f"feedback_{ans.id}"
                
                raw_mark = request.POST.get(mark_field, '0')
                try:
                    mark = float(raw_mark)
                except ValueError:
                    mark = 0.0
                    
                max_mark = ans.question.mark
                if mark > max_mark:
                    mark = float(max_mark)
                elif mark < 0:
                    mark = 0.0
                    
                ans.mark_awarded = mark
                ans.feedback = request.POST.get(feedback_field, '').strip()
                ans.is_graded = True
                ans.is_correct = (mark == max_mark)
                ans.save()
                
        attempt.recalculate_manual_score()
        
        # Trigger notifications
        try:
            from notifications.services import create_notification
            from accounts.models import StudentProfile
            
            # Notify student
            create_notification(
                recipient=attempt.student,
                title=f"Assessment Graded: {attempt.assessment.title}",
                message=f"Your assessment '{attempt.assessment.title}' in course {course.title} has been graded. Final Score: {attempt.percentage}% ({attempt.score_obtained}/{attempt.total_score}).",
                notification_type="assessment",
                delivery_channel="both",
                related_course=course
            )
            
            # Notify guardian
            profile = StudentProfile.objects.filter(user=attempt.student).first()
            if profile and profile.guardian:
                create_notification(
                    recipient=profile.guardian,
                    title=f"Ward Assessment Graded: {attempt.assessment.title}",
                    message=f"Your ward {attempt.student.username}'s assessment '{attempt.assessment.title}' has been graded. Final Score: {attempt.percentage}%.",
                    notification_type="assessment",
                    delivery_channel="both",
                    related_course=course
                )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Assessment manual grading notification failed: {str(e)}")

        messages.success(request, f"Assessment attempt for {attempt.student.username} graded successfully!")
        return redirect('assessment_result', attempt_id=attempt.id)
        
    return render(request, 'assessments/mark_attempt.html', {
        'attempt': attempt,
        'course': course,
        'answers': answers,
    })
