from django.db import models
from django.contrib.auth.models import User
from courses.models import Course


class StudentProgressReport(models.Model):
    """LMS progress report for a student in a specific course."""

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress_reports')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='progress_reports')
    generated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_progress_reports'
    )
    title = models.CharField(max_length=300)
    summary = models.TextField(blank=True)
    lesson_progress_percentage = models.FloatField(default=0)
    assessment_average = models.FloatField(default=0)
    assignment_average = models.FloatField(default=0)
    overall_percentage = models.FloatField(default=0)
    tutor_comment = models.TextField(blank=True)
    guardian_comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.overall_percentage:.1f}%)"

    def calculate_report(self):
        from enrollments.models import Enrollment
        from assessments.models import AssessmentAttempt
        from assignments.models import AssignmentSubmission

        # 1. Lesson Progress
        enrollment = Enrollment.objects.filter(student=self.student, course=self.course, status='active').first()
        lesson_progress = enrollment.progress_percentage if enrollment else 0.0
        self.lesson_progress_percentage = float(lesson_progress)

        # 2. Assessment Average
        attempts = AssessmentAttempt.objects.filter(
            student=self.student,
            assessment__course=self.course,
            status='submitted'
        )
        if attempts.exists():
            assessment_avg = sum(attempt.percentage for attempt in attempts) / attempts.count()
            self.assessment_average = float(assessment_avg)
        else:
            self.assessment_average = 0.0

        # 3. Assignment Average
        submissions = AssignmentSubmission.objects.filter(
            student=self.student,
            assignment__course=self.course,
            status__in=['marked', 'returned']
        )
        sub_pcts = []
        for sub in submissions:
            if sub.assignment.total_marks > 0:
                sub_pcts.append((sub.score / sub.assignment.total_marks) * 100)
        
        if sub_pcts:
            assignment_avg = sum(sub_pcts) / len(sub_pcts)
            self.assignment_average = float(assignment_avg)
        else:
            self.assignment_average = 0.0

        # 4. Overall Percentage
        metrics = [self.lesson_progress_percentage]
        if attempts.exists():
            metrics.append(self.assessment_average)
        if sub_pcts:
            metrics.append(self.assignment_average)

        self.overall_percentage = sum(metrics) / len(metrics)
        self.save()
