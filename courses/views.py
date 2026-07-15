from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Course, Subject, ClassLevel, Lesson
from enrollments.models import Enrollment, LessonProgress

def course_list(request):
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        courses = Course.objects.all()
    else:
        courses = Course.objects.filter(is_published=True)

    if hasattr(request, 'tenant') and request.tenant:
        courses = courses.filter(tenant_mapping__tenant=request.tenant)
        
    subject_param = request.GET.get('subject')
    if subject_param:
        if subject_param.isdigit():
            courses = courses.filter(subject_id=subject_param)
        else:
            courses = courses.filter(subject__slug=subject_param)
            
    class_level_param = request.GET.get('class_level')
    if class_level_param:
        if class_level_param.isdigit():
            courses = courses.filter(class_level_id=class_level_param)
        else:
            courses = courses.filter(class_level__slug=class_level_param)
            
    subjects = Subject.objects.all()
    class_levels = ClassLevel.objects.all()
    
    return render(request, 'courses/course_list.html', {
        'courses': courses,
        'subjects': subjects,
        'class_levels': class_levels,
        'selected_subject': subject_param,
        'selected_class_level': class_level_param,
    })

def course_detail(request, slug):
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        course = get_object_or_404(Course, slug=slug)
    else:
        course = get_object_or_404(Course, slug=slug, is_published=True)
        
    is_enrolled = False
    enrollment = None
    completed_lesson_ids = []
    if request.user.is_authenticated:
        enrollment = Enrollment.objects.filter(student=request.user, course=course, status='active').first()
        is_enrolled = enrollment is not None
        if is_enrolled:
            completed_lesson_ids = list(enrollment.progress.filter(is_completed=True).values_list('lesson_id', flat=True))
        
    modules = course.modules.all().prefetch_related('lessons')
    
    first_lesson = None
    for module in modules:
        for lesson in module.lessons.all():
            first_lesson = lesson
            break
        if first_lesson:
            break
            
    from payments.services import user_has_course_access
    has_access = user_has_course_access(request.user, course) if request.user.is_authenticated else False
            
    # Sprint 8: Fetch timetable slots and live classes for this course
    timetable_slots = []
    live_classes = []
    try:
        from academics.models import TimetableSlot, LiveClass
        timetable_slots = TimetableSlot.objects.filter(course=course, is_active=True).order_by('day_of_week', 'start_time')
        live_classes = LiveClass.objects.filter(course=course, is_published=True).order_by('scheduled_start')
    except Exception:
        pass

    # Check course prerequisites
    from interactive.services import check_course_prerequisites_met
    prereqs_met, unmet_prereq_courses = check_course_prerequisites_met(request.user, course)

    # Fetch path settings for completion rules UI
    from interactive.models import CoursePathSettings, CoursePrerequisite
    path_settings = CoursePathSettings.objects.filter(course=course).first()
    enforce_sequential = path_settings.enforce_sequential if path_settings else False
    course_prerequisites = CoursePrerequisite.objects.filter(course=course).select_related('prerequisite_course')

    completion_rule = None
    try:
        from achievements.models import CourseCompletionRule
        completion_rule = CourseCompletionRule.objects.filter(course=course).first()
    except Exception:
        pass

    return render(request, 'courses/course_detail.html', {
        'course': course,
        'modules': modules,
        'is_enrolled': is_enrolled,
        'enrollment': enrollment,
        'completed_lesson_ids': completed_lesson_ids,
        'first_lesson': first_lesson,
        'has_access': has_access,
        'timetable_slots': timetable_slots,
        'live_classes': live_classes,
        'prereqs_met': prereqs_met,
        'unmet_prereq_courses': unmet_prereq_courses,
        'enforce_sequential': enforce_sequential,
        'course_prerequisites': course_prerequisites,
        'completion_rule': completion_rule,
    })


@login_required
def lesson_detail(request, course_slug, lesson_slug):
    if request.user.is_staff or request.user.is_superuser:
        course = get_object_or_404(Course, slug=course_slug)
    else:
        course = get_object_or_404(Course, slug=course_slug, is_published=True)
        
    lesson = get_object_or_404(Lesson, slug=lesson_slug, module__course=course)
    
    enrollment = Enrollment.objects.filter(student=request.user, course=course, status='active').first()
    is_enrolled = enrollment is not None
    
    from payments.services import user_has_course_access
    
    is_staff = request.user.is_staff or request.user.is_superuser
    is_preview = lesson.is_preview
    
    if not is_staff and not is_preview:
        if not user_has_course_access(request.user, course):
            messages.warning(request, "Access to this lesson requires an active subscription or purchase.")
            return redirect('payments:course_checkout', course_slug=course.slug)
            
        if not is_enrolled:
            messages.warning(request, "You must enroll in this course to access this lesson.")
            return redirect('course_detail', slug=course.slug)

        
    progress = None
    if is_enrolled:
        progress, created = LessonProgress.objects.get_or_create(
            enrollment=enrollment,
            lesson=lesson
        )
        progress.save()
        
    course_lessons = list(Lesson.objects.filter(module__course=course).order_by('module__order', 'order'))
    
    prev_lesson = None
    next_lesson = None
    try:
        current_index = course_lessons.index(lesson)
        if current_index > 0:
            prev_lesson = course_lessons[current_index - 1]
        if current_index < len(course_lessons) - 1:
            next_lesson = course_lessons[current_index + 1]
    except ValueError:
        pass
        
    is_completed = progress.is_completed if progress else False

    # Check if lesson is locked by prerequisites
    from interactive.services import check_lesson_prerequisites_met
    is_locked = False
    lock_reason = None
    unmet_prerequisites = []
    
    if is_enrolled and not is_staff:
        met, reason, unmet = check_lesson_prerequisites_met(request.user, lesson)
        if not met:
            from django.contrib import messages
            if reason == 'sequential':
                messages.warning(request, f"Prerequisite unmet: You must complete the previous lessons in sequence. Please complete '{unmet[0].title}' first.")
            elif reason == 'course_prereq':
                messages.warning(request, f"Prerequisite unmet: You must complete the prerequisite course '{unmet[0].title}' first.")
            elif reason == 'lesson_prereq':
                messages.warning(request, f"Prerequisite unmet: You must complete the prerequisite lesson '{unmet[0].title}' first.")
            else:
                messages.warning(request, "This lesson is locked because prerequisites have not been met.")
            return redirect('course_detail', slug=course.slug)

    # Fetch interactive content
    interactive_content = getattr(lesson, 'interactive_content', None)
    if interactive_content and not interactive_content.is_active:
        interactive_content = None
    
    return render(request, 'courses/lesson_detail.html', {
        'course': course,
        'lesson': lesson,
        'enrollment': enrollment,
        'is_enrolled': is_enrolled,
        'progress': progress,
        'is_completed': is_completed,
        'prev_lesson': prev_lesson,
        'next_lesson': next_lesson,
        'is_locked': is_locked,
        'lock_reason': lock_reason,
        'unmet_prerequisites': unmet_prerequisites,
        'interactive_content': interactive_content,
    })
