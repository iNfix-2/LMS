from enrollments.models import Enrollment
from assessments.models import AssessmentAttempt
from assignments.models import AssignmentSubmission


def get_student_course_progress(student, course):
    enrollment = Enrollment.objects.filter(student=student, course=course, status='active').first()
    if enrollment:
        return enrollment.progress_percentage
    return 0


def get_course_assessment_average(student, course):
    attempts = AssessmentAttempt.objects.filter(
        student=student,
        assessment__course=course,
        status='submitted'
    )
    if attempts.exists():
        return round(sum(attempt.percentage for attempt in attempts) / attempts.count(), 1)
    return 0.0


def get_course_assignment_average(student, course):
    submissions = AssignmentSubmission.objects.filter(
        student=student,
        assignment__course=course,
        status__in=['marked', 'returned']
    )
    sub_pcts = []
    for sub in submissions:
        if sub.assignment.total_marks > 0:
            sub_pcts.append((sub.score / sub.assignment.total_marks) * 100)
    
    if sub_pcts:
        return round(sum(sub_pcts) / len(sub_pcts), 1)
    return 0.0


def get_pending_assessment_marking_count(course):
    return AssessmentAttempt.objects.filter(
        assessment__course=course,
        status='submitted',
        answers__question__question_type__in=['short_answer', 'theory'],
        answers__is_graded=False
    ).distinct().count()


def get_pending_assignment_marking_count(course):
    return AssignmentSubmission.objects.filter(
        assignment__course=course,
        status='submitted'
    ).count()
