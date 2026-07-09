import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden, JsonResponse
from django.utils import timezone
from django.db import transaction

from courses.models import Course, Lesson, Module
from reports.models import StudentProgressReport
from assessments.models import Assessment, Question, Choice
from enrollments.models import Enrollment
from assessments.models import AssessmentAttempt
from assignments.models import AssignmentSubmission

from ai_tools.models import AIConversation, AIMessage, AIGeneratedContent, AIRequestLog, AISafetyFlag, AIUsageLimit
from ai_tools.services.openai_client import (
    generate_ai_response,
    generate_structured_ai_response,
    user_can_use_ai
)
from ai_tools.services.prompts import (
    build_lesson_assistant_prompt,
    build_lesson_summary_prompt,
    build_practice_question_prompt,
    build_quiz_generation_prompt,
    build_worksheet_prompt,
    build_report_comment_prompt,
    build_study_recommendation_prompt
)
from ai_tools.services.schemas import (
    PRACTICE_QUESTIONS_SCHEMA,
    QUIZ_DRAFT_SCHEMA,
    WORKSHEET_SCHEMA,
    REPORT_COMMENT_SCHEMA,
    STUDY_PLAN_SCHEMA
)
from payments.services import user_has_course_access


def check_course_access_or_403(user, course):
    """Utility to check if student has course access or tutor manages course."""
    if course.can_be_managed_by(user):
        return True
    if user_has_course_access(user, course):
        return True
    raise PermissionDenied("You do not have access to this course.")


def check_tutor_or_admin_or_403(user, course=None):
    """Utility to check if user is a tutor or admin."""
    if not user.is_authenticated:
        raise PermissionDenied("Login required.")
    if user.is_staff or user.is_superuser:
        return True
    if hasattr(user, 'profile') and user.profile.role in ['tutor', 'admin']:
        if course and not course.can_be_managed_by(user):
            raise PermissionDenied("You do not manage this course.")
        return True
    raise PermissionDenied("Tutor or admin access required.")


@login_required
def lesson_ai_assistant(request, course_slug, lesson_slug):
    course = get_object_or_404(Course, slug=course_slug)
    lesson = get_object_or_404(Lesson, slug=lesson_slug, module__course=course)
    check_course_access_or_403(request.user, course)

    # Get or create conversation
    conversation, created = AIConversation.objects.get_or_create(
        user=request.user,
        course=course,
        lesson=lesson,
        conversation_type='lesson_assistant',
        is_active=True,
        defaults={'title': f"Chat: {lesson.title}"}
    )

    if request.method == 'POST':
        user_question = request.POST.get('question', '').strip() or request.POST.get('message', '').strip()
        if user_question:
            # 1. Check rate limits
            if not user_can_use_ai(request.user):
                if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'message' in request.POST:
                    return JsonResponse({'error': 'You have reached your daily AI usage limit.'}, status=429)
                messages.error(request, "You have reached your daily AI usage limit. Please try again tomorrow.")
                return redirect(request.path)

            # 2. Save user message
            user_msg = AIMessage.objects.create(
                conversation=conversation,
                sender='user',
                content=user_question
            )

            # 3. Generate prompt & assistant response
            prompt = build_lesson_assistant_prompt(lesson, user_question, request.user)
            system_instruction = "You are a helpful, safe, and age-appropriate tutor assistant. Explain clearly and stay within scope."
            
            ai_text, metadata = generate_ai_response(
                prompt=prompt,
                system_instruction=system_instruction,
                user=request.user,
                context={'course': course, 'lesson': lesson},
                request_type='lesson_assistant'
            )

            # Check if prompt or response was blocked by moderation
            mod_status = 'safe'
            if metadata.get('status') == 'blocked':
                mod_status = 'blocked'
                user_msg.moderation_status = 'blocked'
                user_msg.save()
            elif metadata.get('status') == 'flagged':
                mod_status = 'flagged'

            # 4. Save assistant message
            AIMessage.objects.create(
                conversation=conversation,
                sender='assistant',
                content=ai_text,
                moderation_status=mod_status,
                tokens_input=metadata.get('tokens_input', 0),
                tokens_output=metadata.get('tokens_output', 0),
                model_used=metadata.get('model_used', '')
            )
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'message' in request.POST:
                return JsonResponse({'response': ai_text, 'status': mod_status})
                
            return redirect(request.path)

    messages_list = conversation.messages.all()
    return render(request, 'ai_tools/lesson_ai_assistant.html', {
        'conversation': conversation,
        'messages_list': messages_list,
        'course': course,
        'lesson': lesson
    })


@login_required
def lesson_ai_summary(request, course_slug, lesson_slug):
    course = get_object_or_404(Course, slug=course_slug)
    lesson = get_object_or_404(Lesson, slug=lesson_slug, module__course=course)
    check_course_access_or_403(request.user, course)

    # Check if a summary already exists as published content
    generated_content = AIGeneratedContent.objects.filter(
        generated_by=request.user,
        course=course,
        lesson=lesson,
        content_type='lesson_summary',
        status='published'
    ).first()

    if not generated_content:
        # Check limits
        if not user_can_use_ai(request.user):
            messages.error(request, "Daily AI limit reached.")
            return redirect('courses:lesson_detail', course_slug=course.slug, lesson_slug=lesson.slug)

        prompt = build_lesson_summary_prompt(lesson)
        system_instruction = "Generate a clear, structured lesson summary, key points, terms, and 5 revision questions in markdown."
        
        summary_text, metadata = generate_ai_response(
            prompt=prompt,
            system_instruction=system_instruction,
            user=request.user,
            context={'course': course, 'lesson': lesson},
            request_type='lesson_summary'
        )

        status = 'published'
        if metadata.get('status') in ['blocked', 'flagged']:
            status = 'rejected'

        generated_content = AIGeneratedContent.objects.create(
            generated_by=request.user,
            course=course,
            lesson=lesson,
            content_type='lesson_summary',
            title=f"Summary: {lesson.title}",
            prompt=prompt,
            raw_response=summary_text,
            status=status
        )

    return render(request, 'ai_tools/lesson_ai_summary.html', {
        'content': generated_content,
        'course': course,
        'lesson': lesson
    })


@login_required
def generate_practice_questions(request, course_slug, lesson_slug):
    course = get_object_or_404(Course, slug=course_slug)
    lesson = get_object_or_404(Lesson, slug=lesson_slug, module__course=course)
    check_course_access_or_403(request.user, course)

    difficulty = request.GET.get('difficulty', 'medium')
    
    # Check if questions already exist for this request
    generated_content = AIGeneratedContent.objects.filter(
        generated_by=request.user,
        course=course,
        lesson=lesson,
        content_type='practice_questions',
        status='published'
    ).first()

    if not generated_content or request.GET.get('regenerate') == '1':
        if not user_can_use_ai(request.user):
            messages.error(request, "Daily AI limit reached.")
            return redirect('courses:lesson_detail', course_slug=course.slug, lesson_slug=lesson.slug)

        prompt = build_practice_question_prompt(lesson, difficulty, 5)
        system_instruction = "Generate practice questions matching the provided JSON schema."
        
        parsed_json, metadata = generate_structured_ai_response(
            prompt=prompt,
            system_instruction=system_instruction,
            schema=PRACTICE_QUESTIONS_SCHEMA,
            user=request.user,
            context={'course': course, 'lesson': lesson},
            request_type='practice_questions'
        )

        status = 'published'
        if metadata.get('status') in ['blocked', 'flagged']:
            status = 'rejected'

        generated_content = AIGeneratedContent.objects.create(
            generated_by=request.user,
            course=course,
            lesson=lesson,
            content_type='practice_questions',
            title=f"Practice Questions: {lesson.title}",
            prompt=prompt,
            generated_content=parsed_json,
            raw_response=json.dumps(parsed_json),
            status=status
        )

    questions_data = generated_content.generated_content.get('questions', [])

    return render(request, 'ai_tools/practice_questions.html', {
        'content': generated_content,
        'questions_data': questions_data,
        'course': course,
        'lesson': lesson,
        'difficulty': difficulty
    })


@login_required
def tutor_generate_quiz(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug)
    check_tutor_or_admin_or_403(request.user, course)

    modules = course.modules.all()
    lessons = Lesson.objects.filter(module__course=course)

    if request.method == 'POST':
        module_id = request.POST.get('module')
        lesson_id = request.POST.get('lesson')
        question_count = int(request.POST.get('question_count', 5))
        difficulty = request.POST.get('difficulty', 'medium')

        module = get_object_or_404(Module, id=module_id) if module_id else None
        lesson = get_object_or_404(Lesson, id=lesson_id) if lesson_id else None

        if not user_can_use_ai(request.user):
            messages.error(request, "Daily AI limit reached.")
            return redirect(request.path)

        prompt = build_quiz_generation_prompt(course, module, lesson, question_count, difficulty)
        system_instruction = "Generate a multiple choice quiz draft matching the QuizDraftSchema."

        parsed_json, metadata = generate_structured_ai_response(
            prompt=prompt,
            system_instruction=system_instruction,
            schema=QUIZ_DRAFT_SCHEMA,
            user=request.user,
            context={'course': course, 'lesson': lesson},
            request_type='quiz_generation'
        )

        draft = AIGeneratedContent.objects.create(
            generated_by=request.user,
            course=course,
            lesson=lesson,
            content_type='quiz',
            title=parsed_json.get('title', f"AI Quiz Draft: {lesson.title if lesson else course.title}"),
            prompt=prompt,
            generated_content=parsed_json,
            raw_response=json.dumps(parsed_json),
            status='draft'
        )
        return redirect('ai_tools:ai_generated_content_detail', content_id=draft.id)

    return render(request, 'ai_tools/tutor_generate_quiz.html', {
        'course': course,
        'modules': modules,
        'lessons': lessons
    })


@login_required
def tutor_generate_worksheet(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug)
    check_tutor_or_admin_or_403(request.user, course)

    lessons = Lesson.objects.filter(module__course=course)

    if request.method == 'POST':
        lesson_id = request.POST.get('lesson')
        difficulty = request.POST.get('difficulty', 'medium')

        lesson = get_object_or_404(Lesson, id=lesson_id)

        if not user_can_use_ai(request.user):
            messages.error(request, "Daily AI limit reached.")
            return redirect(request.path)

        prompt = build_worksheet_prompt(course, lesson, difficulty)
        system_instruction = "Generate a worksheet matching the WorksheetSchema."

        parsed_json, metadata = generate_structured_ai_response(
            prompt=prompt,
            system_instruction=system_instruction,
            schema=WORKSHEET_SCHEMA,
            user=request.user,
            context={'course': course, 'lesson': lesson},
            request_type='worksheet_generation'
        )

        draft = AIGeneratedContent.objects.create(
            generated_by=request.user,
            course=course,
            lesson=lesson,
            content_type='worksheet',
            title=parsed_json.get('title', f"AI Worksheet Draft: {lesson.title}"),
            prompt=prompt,
            generated_content=parsed_json,
            raw_response=json.dumps(parsed_json),
            status='draft'
        )
        return redirect('ai_tools:ai_generated_content_detail', content_id=draft.id)

    return render(request, 'ai_tools/tutor_generate_worksheet.html', {
        'course': course,
        'lessons': lessons
    })


@login_required
def generate_report_comment(request, report_id):
    report = get_object_or_404(StudentProgressReport, id=report_id)
    course = report.course
    check_tutor_or_admin_or_403(request.user, course)

    # Compile metrics
    report_metrics = {
        'lesson_progress_percentage': report.lesson_progress_percentage,
        'assessment_average': report.assessment_average,
        'assignment_average': report.assignment_average,
        'overall_percentage': report.overall_percentage
    }

    if request.method == 'POST' and 'generate' in request.POST:
        if not user_can_use_ai(request.user):
            messages.error(request, "Daily AI limit reached.")
            return redirect(request.path)

        prompt = build_report_comment_prompt(report.student, course, report_metrics)
        system_instruction = "Generate progress report comment details matching the ReportCommentSchema."

        parsed_json, metadata = generate_structured_ai_response(
            prompt=prompt,
            system_instruction=system_instruction,
            schema=REPORT_COMMENT_SCHEMA,
            user=request.user,
            context={'course': course},
            request_type='report_comment'
        )

        draft = AIGeneratedContent.objects.create(
            generated_by=request.user,
            course=course,
            content_type='report_comment',
            title=f"AI Comment Draft: {report.student.username}",
            prompt=prompt,
            generated_content=parsed_json,
            raw_response=json.dumps(parsed_json),
            status='draft'
        )
        return redirect('ai_tools:generate_report_comment', report_id=report.id)

    # Get most recent draft if any
    draft = AIGeneratedContent.objects.filter(
        generated_by=request.user,
        course=course,
        content_type='report_comment'
    ).order_by('-created_at').first()

    # Handle applying comment to the report card
    if request.method == 'POST' and 'apply' in request.POST and draft:
        comment_text = request.POST.get('comment_text', '').strip()
        if comment_text:
            report.tutor_comment = comment_text
            report.save()
            messages.success(request, "Comment applied to the progress report card successfully.")
            return redirect('student_progress_report_detail', report_id=report.id)

    return render(request, 'ai_tools/report_comment_generator.html', {
        'report': report,
        'draft': draft,
        'course': course
    })


@login_required
def student_study_recommendations(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug)
    check_course_access_or_403(request.user, course)

    # Check if plan already exists for today
    generated_content = AIGeneratedContent.objects.filter(
        generated_by=request.user,
        course=course,
        content_type='study_plan',
        status='published'
    ).first()

    if not generated_content or request.GET.get('recalculate') == '1':
        if not user_can_use_ai(request.user):
            messages.error(request, "Daily AI limit reached.")
            return redirect('courses:course_detail', slug=course.slug)

        # 1. Fetch performance stats
        enrollment = Enrollment.objects.filter(student=request.user, course=course, status='active').first()
        unfinished_lessons = []
        if enrollment:
            # Simple list of unfinished lessons
            completed_lesson_ids = enrollment.completed_lessons.values_list('id', flat=True)
            unfinished_lessons = list(Lesson.objects.filter(module__course=course).exclude(id__in=completed_lesson_ids).values_list('title', flat=True)[:5])

        # Attempts
        attempts = AssessmentAttempt.objects.filter(student=request.user, assessment__course=course, status='submitted')
        assessment_results = "None"
        if attempts.exists():
            avg = sum(a.percentage for a in attempts) / attempts.count()
            assessment_results = f"Completed {attempts.count()} quizzes. Average score: {avg:.1f}%"

        # Submissions
        submissions = AssignmentSubmission.objects.filter(student=request.user, assignment__course=course)
        assignment_results = f"Submitted {submissions.count()} assignments."

        performance_data = {
            'unfinished_lessons': unfinished_lessons,
            'assessment_results': assessment_results,
            'assignment_results': assignment_results
        }

        prompt = build_study_recommendation_prompt(request.user, course, performance_data)
        system_instruction = "Generate study plan recommendation details matching the StudyPlanSchema."

        parsed_json, metadata = generate_structured_ai_response(
            prompt=prompt,
            system_instruction=system_instruction,
            schema=STUDY_PLAN_SCHEMA,
            user=request.user,
            context={'course': course},
            request_type='study_recommendation'
        )

        status = 'published'
        if metadata.get('status') in ['blocked', 'flagged']:
            status = 'rejected'

        generated_content = AIGeneratedContent.objects.create(
            generated_by=request.user,
            course=course,
            content_type='study_plan',
            title=f"Study Plan: {course.title}",
            prompt=prompt,
            generated_content=parsed_json,
            raw_response=json.dumps(parsed_json),
            status=status
        )

    plan_data = generated_content.generated_content

    return render(request, 'ai_tools/study_recommendations.html', {
        'content': generated_content,
        'plan_data': plan_data,
        'course': course
    })


@login_required
def ai_generated_content_detail(request, content_id):
    content = get_object_or_404(AIGeneratedContent, id=content_id)
    
    # Permission: Owner, tutor/admin, or staff
    is_owner = (content.generated_by == request.user)
    is_tutor_or_admin = (content.course and content.course.can_be_managed_by(request.user))
    
    if not (is_owner or is_tutor_or_admin or request.user.is_staff):
        raise PermissionDenied("You do not have access to view this generated content.")

    return render(request, 'ai_tools/generated_content_detail.html', {
        'content': content,
        'course': content.course,
        'is_tutor': is_tutor_or_admin
    })


@login_required
def approve_ai_generated_content(request, content_id):
    content = get_object_or_404(AIGeneratedContent, id=content_id)
    check_tutor_or_admin_or_403(request.user, content.course)

    content.status = 'approved'
    content.reviewed_by = request.user
    content.save()
    
    messages.success(request, f"Content draft '{content.title}' approved successfully.")
    return redirect('ai_tools:ai_generated_content_detail', content_id=content.id)


@login_required
def reject_ai_generated_content(request, content_id):
    content = get_object_or_404(AIGeneratedContent, id=content_id)
    check_tutor_or_admin_or_403(request.user, content.course)

    if request.method == 'POST':
        comment = request.POST.get('review_comment', '').strip()
        content.status = 'rejected'
        content.reviewed_by = request.user
        content.review_comment = comment
        content.save()
        messages.success(request, f"Content draft '{content.title}' rejected.")
    return redirect('ai_tools:ai_generated_content_detail', content_id=content.id)


@login_required
def publish_ai_quiz_draft(request, content_id):
    content = get_object_or_404(AIGeneratedContent, id=content_id)
    check_tutor_or_admin_or_403(request.user, content.course)

    if content.content_type != 'quiz':
        messages.error(request, "This action is only supported for Quiz drafts.")
        return redirect('ai_tools:ai_generated_content_detail', content_id=content.id)

    if content.status != 'approved':
        messages.error(request, "The quiz draft must be approved before publishing it.")
        return redirect('ai_tools:ai_generated_content_detail', content_id=content.id)

    # Begin publishing record transaction
    try:
        with transaction.atomic():
            quiz_data = content.generated_content
            
            # Create Assessment object (is_published=False by default)
            assessment = Assessment.objects.create(
                course=content.course,
                module=content.lesson.module if content.lesson else None,
                title=quiz_data.get('title', f"Quiz: {content.lesson.title if content.lesson else content.course.title}"),
                description=quiz_data.get('instructions', ''),
                assessment_type='quiz',
                is_published=False,
                created_by=request.user
            )

            # Create Questions and Choices
            for idx, q_item in enumerate(quiz_data.get('questions', [])):
                question = Question.objects.create(
                    assessment=assessment,
                    question_text=q_item.get('question_text', ''),
                    question_type='objective',
                    mark=q_item.get('mark', 1),
                    explanation=q_item.get('explanation', ''),
                    order=idx
                )

                correct_choice_text = q_item.get('correct_choice', '')
                for choice_idx, choice_text in enumerate(q_item.get('choices', [])):
                    Choice.objects.create(
                        question=question,
                        choice_text=choice_text,
                        is_correct=(choice_text == correct_choice_text),
                        order=choice_idx
                    )

            # Mark draft as published
            content.status = 'published'
            content.save()

            messages.success(request, f"Draft published successfully as Assessment: '{assessment.title}'. Note: It remains hidden from students until you publish it explicitly.")
            return redirect('assessments:course_assessments', course_slug=content.course.slug)

    except Exception as e:
        messages.error(request, f"Failed to publish quiz draft: {e}")
        return redirect('ai_tools:ai_generated_content_detail', content_id=content.id)


@login_required
def ai_usage_dashboard(request):
    if not request.user.is_staff and not request.user.is_superuser:
        return HttpResponseForbidden("Admin access required.")

    # Fetch stats
    today = timezone.localdate()
    requests_today = AIRequestLog.objects.filter(created_at__date=today).count()
    failed_today = AIRequestLog.objects.filter(created_at__date=today, status='failed').count()
    flagged_today = AIRequestLog.objects.filter(created_at__date=today, status='flagged').count()
    blocked_today = AIRequestLog.objects.filter(created_at__date=today, status='blocked').count()
    
    total_quizzes = AIGeneratedContent.objects.filter(content_type='quiz').count()
    total_worksheets = AIGeneratedContent.objects.filter(content_type='worksheet').count()

    latest_logs = AIRequestLog.objects.all()[:50]
    usage_limits = AIUsageLimit.objects.filter(date=today)

    return render(request, 'ai_tools/ai_usage_dashboard.html', {
        'requests_today': requests_today,
        'failed_today': failed_today,
        'flagged_today': flagged_today,
        'blocked_today': blocked_today,
        'total_quizzes': total_quizzes,
        'total_worksheets': total_worksheets,
        'latest_logs': latest_logs,
        'usage_limits': usage_limits
    })


@login_required
def ai_safety_flags(request):
    if not request.user.is_staff and not request.user.is_superuser:
        return HttpResponseForbidden("Admin access required.")

    if request.method == 'POST':
        flag_id = request.POST.get('flag_id')
        flag = get_object_or_404(AISafetyFlag, id=flag_id)
        flag.reviewed = True
        flag.reviewed_by = request.user
        flag.save()
        messages.success(request, f"Flag {flag.id} marked as reviewed.")
        return redirect(request.path)

    flags = AISafetyFlag.objects.all()
    return render(request, 'ai_tools/ai_safety_flags.html', {
        'flags': flags
    })
