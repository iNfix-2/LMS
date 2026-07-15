from enrollments.models import Enrollment, LessonProgress
from courses.models import Lesson
from .models import CoursePrerequisite, LessonPrerequisite, CoursePathSettings

def check_course_prerequisites_met(student, course):
    """
    Checks if a student has completed all prerequisite courses.
    Returns: (bool, list_of_unmet_courses)
    """
    if not student or not student.is_authenticated:
        return True, []

    # Staff/Superuser bypass
    if student.is_staff or student.is_superuser:
        return True, []

    # Get all prerequisite courses
    prereqs = CoursePrerequisite.objects.filter(course=course)
    if not prereqs.exists():
        return True, []

    unmet_courses = []
    for p in prereqs:
        required = p.prerequisite_course
        # Check if student completed this course.
        enrollment = Enrollment.objects.filter(student=student, course=required).first()
        if not enrollment:
            unmet_courses.append(required)
        else:
            # Check if all lessons are completed
            total_lessons = Lesson.objects.filter(module__course=required).count()
            completed_count = LessonProgress.objects.filter(
                enrollment=enrollment, is_completed=True
            ).count()
            if total_lessons > 0 and completed_count < total_lessons:
                unmet_courses.append(required)

    return len(unmet_courses) == 0, unmet_courses


def check_lesson_prerequisites_met(student, lesson):
    """
    Checks if a student has met all progression prerequisites for a lesson.
    Returns: (bool, reason_code, list_of_unmet_items)
    """
    if not student or not student.is_authenticated:
        return True, None, []

    if student.is_staff or student.is_superuser:
        return True, None, []

    # 1. Course prerequisites
    course_met, unmet_courses = check_course_prerequisites_met(student, lesson.module.course)
    if not course_met:
        return False, 'course_prereq', unmet_courses

    # Find student enrollment
    enrollment = Enrollment.objects.filter(
        student=student, course=lesson.module.course, status='active'
    ).first()
    if not enrollment:
        return True, None, []

    # 2. Sequential progression check
    path_settings = CoursePathSettings.objects.filter(course=lesson.module.course).first()
    if path_settings and path_settings.enforce_sequential:
        all_lessons = list(Lesson.objects.filter(
            module__course=lesson.module.course
        ).order_by('module__order', 'order'))
        
        try:
            curr_index = all_lessons.index(lesson)
            uncompleted_previous = []
            for prev_lesson in all_lessons[:curr_index]:
                progress = LessonProgress.objects.filter(
                    enrollment=enrollment, lesson=prev_lesson, is_completed=True
                ).exists()
                if not progress:
                    uncompleted_previous.append(prev_lesson)
            if uncompleted_previous:
                return False, 'sequential', uncompleted_previous
        except ValueError:
            pass

    # 3. Custom Lesson Prerequisites
    lesson_prereqs = LessonPrerequisite.objects.filter(lesson=lesson)
    unmet_lessons = []
    for lp in lesson_prereqs:
        required = lp.prerequisite_lesson
        progress = LessonProgress.objects.filter(
            enrollment=enrollment, lesson=required, is_completed=True
        ).exists()
        if not progress:
            unmet_lessons.append(required)

    if unmet_lessons:
        return False, 'lesson_prereq', unmet_lessons

    return True, None, []
