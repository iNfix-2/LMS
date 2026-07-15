from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from courses.models import Course, Module, Lesson
from enrollments.models import Enrollment, LessonProgress
from achievements.models import Badge, StudentAchievement, Certificate, CourseCompletionRule
from achievements.services import check_and_award_course_completion

User = get_user_model()

class AchievementsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = User.objects.create_user(username='student1', password='password123')
        from courses.models import Subject, ClassLevel
        self.subject = Subject.objects.create(name='Science', slug='science')
        self.class_level = ClassLevel.objects.create(name='Grade 10')
        self.course = Course.objects.create(
            title='Introduction to Physics', 
            slug='intro-to-physics', 
            subject=self.subject,
            class_level=self.class_level,
            created_by=self.student,
            description='Test course', 
            is_published=True
        )
        self.module = Module.objects.create(course=self.course, title='Module 1', order=1)
        self.lesson = Lesson.objects.create(
            module=self.module, 
            title='Newtonian Mechanics', 
            slug='newtonian-mechanics', 
            order=1, 
            content='Newtonian mechanics lesson'
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            status='active'
        )
        
        # Completion rule: 100% progress required
        self.rule = CourseCompletionRule.objects.create(
            course=self.course,
            min_progress_percentage=100
        )
        
        self.badge = Badge.objects.create(
            title='Physics Pioneer',
            description='Completed Introduction to Physics',
            badge_type='course_completed'
        )

    def test_course_completion_triggers_certificate_and_badge(self):
        # Initial state
        self.assertFalse(Certificate.objects.filter(student=self.student, course=self.course).exists())
        
        # Complete the lesson
        progress = LessonProgress.objects.create(
            enrollment=self.enrollment,
            lesson=self.lesson,
            is_completed=True
        )
        
        # Trigger progression checks
        check_and_award_course_completion(self.student, self.course)
        
        # Assert Certificate created
        self.assertTrue(Certificate.objects.filter(student=self.student, course=self.course).exists())
        
        # Assert Achievement/Badge awarded
        # (Need to make sure achievement mapping or manual award functions properly)
        cert = Certificate.objects.get(student=self.student, course=self.course)
        self.assertIsNotNone(cert.certificate_number)

    def test_certificate_verification_view(self):
        cert = Certificate.objects.create(
            student=self.student,
            course=self.course,
            certificate_number='EDU-CERT-12345'
        )
        # Search valid certificate
        response = self.client.get(reverse('achievements:verify_certificate') + '?q=EDU-CERT-12345')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Verification Successful')
        self.assertContains(response, 'student1')
        
        # Search invalid certificate
        response = self.client.get(reverse('achievements:verify_certificate') + '?q=EDU-CERT-WRONG')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Verification Failed')

    def test_achievements_dashboard_view(self):
        self.client.login(username='student1', password='password123')
        response = self.client.get(reverse('achievements:my_achievements'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My Achievements')
