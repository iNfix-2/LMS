from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.views.decorators.clickjacking import xframe_options_sameorigin
from courses.models import Course, Lesson
from .models import CoursePathSettings, CoursePrerequisite, LessonPrerequisite, InteractiveContent
from .forms import InteractiveContentForm
from .utils import extract_and_parse_package

def _is_authorized(user, course):
    return user.is_staff or user.is_superuser or course.created_by == user or user in course.assigned_tutors.all()

@login_required
def path_manager(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug)
    if not _is_authorized(request.user, course):
        return HttpResponseForbidden("You are not authorized to manage this course path.")

    # Get settings or create
    path_settings, _ = CoursePathSettings.objects.get_or_create(course=course)
    
    current_prereqs = CoursePrerequisite.objects.filter(course=course)
    
    # Available courses for prerequisites (published courses that are not this course and not already a prerequisite)
    prereq_ids = current_prereqs.values_list('prerequisite_course_id', flat=True)
    available_courses = Course.objects.filter(is_published=True).exclude(id=course.id).exclude(id__in=prereq_ids)

    lessons = Lesson.objects.filter(module__course=course).order_by('module__order', 'order')
    lesson_prereqs = LessonPrerequisite.objects.filter(lesson__module__course=course)

    # Dictionary of interactive content mapped by lesson ID
    interactive_items = {}
    for item in InteractiveContent.objects.filter(lesson__module__course=course):
        interactive_items[item.lesson_id] = item

    return render(request, 'interactive/path_manager.html', {
        'course': course,
        'path_settings': path_settings,
        'current_prereqs': current_prereqs,
        'available_courses': available_courses,
        'lessons': lessons,
        'lesson_prereqs': lesson_prereqs,
        'interactive_items': interactive_items
    })


@login_required
@require_POST
def toggle_sequential(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug)
    if not _is_authorized(request.user, course):
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)

    settings, _ = CoursePathSettings.objects.get_or_create(course=course)
    settings.enforce_sequential = not settings.enforce_sequential
    settings.save()

    return JsonResponse({
        'status': 'success',
        'enforce_sequential': settings.enforce_sequential
    })


@login_required
@require_POST
def add_course_prerequisite(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug)
    if not _is_authorized(request.user, course):
        return HttpResponseForbidden("Unauthorized")

    prereq_course_id = request.POST.get('prerequisite_course_id')
    prereq_course = get_object_or_404(Course, id=prereq_course_id)

    try:
        CoursePrerequisite.objects.create(course=course, prerequisite_course=prereq_course)
        messages.success(request, f"Course '{prereq_course.title}' added as prerequisite.")
    except Exception as e:
        messages.error(request, f"Error: {e}")

    return redirect('interactive:path_manager', course_slug=course.slug)


@login_required
@require_POST
def remove_course_prerequisite(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug)
    if not _is_authorized(request.user, course):
        return HttpResponseForbidden("Unauthorized")

    prereq_course_id = request.POST.get('prerequisite_course_id')
    prereq_course = get_object_or_404(Course, id=prereq_course_id)

    CoursePrerequisite.objects.filter(course=course, prerequisite_course=prereq_course).delete()
    messages.success(request, f"Course prerequisite '{prereq_course.title}' removed.")
    
    return redirect('interactive:path_manager', course_slug=course.slug)


@login_required
@require_POST
def add_lesson_prerequisite(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug)
    if not _is_authorized(request.user, course):
        return HttpResponseForbidden("Unauthorized")

    lesson_id = request.POST.get('lesson_id')
    prereq_lesson_id = request.POST.get('prerequisite_lesson_id')

    lesson = get_object_or_404(Lesson, id=lesson_id, module__course=course)
    prereq_lesson = get_object_or_404(Lesson, id=prereq_lesson_id, module__course=course)

    try:
        LessonPrerequisite.objects.create(lesson=lesson, prerequisite_lesson=prereq_lesson)
        messages.success(request, f"Lesson prerequisite set successfully.")
    except Exception as e:
        messages.error(request, f"Error setting lesson prerequisite: {e}")

    return redirect('interactive:path_manager', course_slug=course.slug)


@login_required
@require_POST
def remove_lesson_prerequisite(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug)
    if not _is_authorized(request.user, course):
        return HttpResponseForbidden("Unauthorized")

    prereq_id = request.POST.get('prerequisite_id')
    LessonPrerequisite.objects.filter(id=prereq_id, lesson__module__course=course).delete()
    
    messages.success(request, "Lesson prerequisite removed.")
    return redirect('interactive:path_manager', course_slug=course.slug)


@login_required
def manage_lesson_interactive(request, course_slug, lesson_id):
    course = get_object_or_404(Course, slug=course_slug)
    if not _is_authorized(request.user, course):
        return HttpResponseForbidden("Unauthorized")

    lesson = get_object_or_404(Lesson, id=lesson_id, module__course=course)
    
    # Get existing or init new
    interactive_content, _ = InteractiveContent.objects.get_or_create(lesson=lesson)

    if request.method == 'POST':
        form = InteractiveContentForm(request.POST, request.FILES, instance=interactive_content)
        if form.is_valid():
            saved_content = form.save()
            # If package file uploaded, extract it
            if saved_content.package_file:
                extract_and_parse_package(saved_content)
            messages.success(request, "Interactive content settings saved successfully.")
            return redirect('interactive:path_manager', course_slug=course.slug)
    else:
        form = InteractiveContentForm(instance=interactive_content)

    return render(request, 'interactive/manage_interactive.html', {
        'course': course,
        'lesson': lesson,
        'form': form,
        'interactive_content': interactive_content
    })


@login_required
def h5p_player(request, content_id):
    content = get_object_or_404(InteractiveContent, id=content_id)
    # Check if student has access to course
    course = content.lesson.module.course
    
    # Just render the mockup player template
    return render(request, 'interactive/h5p_player.html', {
        'lesson': content.lesson,
        'interactive_content': content
    })
