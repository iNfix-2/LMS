from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from courses.models import Course, Subject, ClassLevel, Module, Lesson
from enrollments.models import Enrollment, LessonProgress
from interactive.models import (
    CoursePathSettings, CoursePrerequisite, LessonPrerequisite, InteractiveContent
)
from interactive.services import (
    check_course_prerequisites_met, check_lesson_prerequisites_met
)

from accounts.models import UserProfile

User = get_user_model()

class InteractiveContentTests(TestCase):
    def setUp(self):
        # Create users
        self.tutor = User.objects.create_user(username='tutor', password='password123', email='tutor@example.com')
        self.student = User.objects.create_user(username='student', password='password123', email='student@example.com')
        
        self.student_profile = UserProfile.objects.create(user=self.student, role='student')
        self.tutor_profile = UserProfile.objects.create(user=self.tutor, role='tutor')

        # Create Subject and ClassLevel
        self.subject = Subject.objects.create(name='Mathematics', slug='mathematics')
        self.class_level = ClassLevel.objects.create(name='Secondary')

        # Create courses
        self.course_a = Course.objects.create(
            title="Course A", slug="course-a", description="First Course", 
            is_published=True, created_by=self.tutor,
            subject=self.subject, class_level=self.class_level
        )
        self.course_b = Course.objects.create(
            title="Course B", slug="course-b", description="Second Course", 
            is_published=True, created_by=self.tutor,
            subject=self.subject, class_level=self.class_level
        )

        # Create modules and lessons
        self.module_a = Module.objects.create(course=self.course_a, title="Module A", order=1)
        self.lesson_a1 = Lesson.objects.create(module=self.module_a, title="Lesson A1", slug="lesson-a1", order=1)
        self.lesson_a2 = Lesson.objects.create(module=self.module_a, title="Lesson A2", slug="lesson-a2", order=2)

        self.module_b = Module.objects.create(course=self.course_b, title="Module B", order=1)
        self.lesson_b1 = Lesson.objects.create(module=self.module_b, title="Lesson B1", slug="lesson-b1", order=1)

        # Client
        self.client = Client()

    def test_course_prerequisite_validation(self):
        # Prevent self prerequisite
        prereq = CoursePrerequisite(course=self.course_a, prerequisite_course=self.course_a)
        with self.assertRaises(ValidationError):
            prereq.clean()

    def test_lesson_prerequisite_validation(self):
        # Prevent self prerequisite
        prereq = LessonPrerequisite(lesson=self.lesson_a1, prerequisite_lesson=self.lesson_a1)
        with self.assertRaises(ValidationError):
            prereq.clean()

        # Prevent cross-course lesson prerequisite
        prereq_cross = LessonPrerequisite(lesson=self.lesson_a1, prerequisite_lesson=self.lesson_b1)
        with self.assertRaises(ValidationError):
            prereq_cross.clean()

    def test_course_prerequisites_services(self):
        # Add Course A as prerequisite for Course B
        CoursePrerequisite.objects.create(course=self.course_b, prerequisite_course=self.course_a)

        # Check for student (not enrolled or completed Course A yet)
        met, unmet = check_course_prerequisites_met(self.student, self.course_b)
        self.assertFalse(met)
        self.assertIn(self.course_a, unmet)

        # Enroll in Course A and complete its lessons
        enrollment_a = Enrollment.objects.create(student=self.student, course=self.course_a, status='active')
        progress_a1 = LessonProgress.objects.create(enrollment=enrollment_a, lesson=self.lesson_a1, is_completed=True)
        progress_a2 = LessonProgress.objects.create(enrollment=enrollment_a, lesson=self.lesson_a2, is_completed=True)

        # Re-check prerequisites
        met, unmet = check_course_prerequisites_met(self.student, self.course_b)
        self.assertTrue(met)
        self.assertEqual(len(unmet), 0)

    def test_lesson_sequential_navigation(self):
        # Enable sequential navigation on Course A
        path_settings = CoursePathSettings.objects.get(course=self.course_a)
        path_settings.enforce_sequential = True
        path_settings.save()

        # Student enrolls in Course A
        enrollment_a = Enrollment.objects.create(student=self.student, course=self.course_a, status='active')

        # Try to access Lesson A2 before A1 is completed
        met, reason, unmet = check_lesson_prerequisites_met(self.student, self.lesson_a2)
        self.assertFalse(met)
        self.assertEqual(reason, 'sequential')
        self.assertIn(self.lesson_a1, unmet)

        # Complete A1
        progress_a1 = LessonProgress.objects.create(enrollment=enrollment_a, lesson=self.lesson_a1, is_completed=True)

        # Re-check Lesson A2
        met, reason, unmet = check_lesson_prerequisites_met(self.student, self.lesson_a2)
        self.assertTrue(met)

    def test_view_locks(self):
        # Set Course A as prerequisite for Course B
        CoursePrerequisite.objects.create(course=self.course_b, prerequisite_course=self.course_a)

        # Login student
        self.client.login(username='student', password='password123')

        # Try to enroll in Course B -> should block and redirect
        response = self.client.post(reverse('enroll_in_course', kwargs={'course_slug': self.course_b.slug}), follow=True)
        self.assertContains(response, "Cannot enroll. You must complete the following prerequisite courses first")

        # Check course detail page -> should show locked status context
        response = self.client.get(reverse('course_detail', kwargs={'slug': self.course_b.slug}))
        self.assertEqual(response.context['prereqs_met'], False)
        self.assertIn(self.course_a, response.context['unmet_prereq_courses'])
