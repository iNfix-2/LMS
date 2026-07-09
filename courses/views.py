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
    
    return render(request, 'courses/lesson_detail.html', {
        'course': course,
        'lesson': lesson,
        'enrollment': enrollment,
        'is_enrolled': is_enrolled,
        'progress': progress,
        'is_completed': is_completed,
        'prev_lesson': prev_lesson,
        'next_lesson': next_lesson,
    })
