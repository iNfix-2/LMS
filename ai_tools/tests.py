from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from unittest.mock import patch, MagicMock
from accounts.models import UserProfile
from courses.models import Course, Subject, ClassLevel, Module, Lesson
from enrollments.models import Enrollment
from reports.models import StudentProgressReport
from ai_tools.models import AIRequestLog, AIUsageLimit, AISafetyFlag, AIGeneratedContent
from ai_tools.services.openai_client import (
    moderate_text,
    generate_ai_response,
    generate_structured_ai_response,
    user_can_use_ai,
    increment_ai_usage
)
from ai_tools.services.prompts import clean_pii_from_text


class AIToolsServiceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='student1', password='password1')
        self.profile = UserProfile.objects.create(user=self.user, role='student')

    def test_clean_pii_from_text(self):
        text = "Hello, my email is test@example.com and phone is +2348012345678. Card number is 4111-2222-3333-4444."
        cleaned = clean_pii_from_text(text)
        self.assertNotIn("test@example.com", cleaned)
        self.assertNotIn("+2348012345678", cleaned)
        self.assertNotIn("4111-2222-3333-4444", cleaned)
        self.assertIn("[REDACTED EMAIL]", cleaned)

    @patch('ai_tools.services.openai_client.get_openai_client')
    def test_moderate_text_safe(self, mock_get_openai_client):
        # Mocking moderation response
        mock_client = MagicMock()
        mock_get_openai_client.return_value = mock_client
        mock_results = MagicMock()
        mock_results.flagged = False
        mock_results.categories = MagicMock()
        mock_results.categories.__dict__ = {}
        mock_response = MagicMock()
        mock_response.results = [mock_results]
        mock_client.moderations.create.return_value = mock_response

        res = moderate_text("I love learning Django.", user=self.user)
        self.assertFalse(res["flagged"])
        self.assertEqual(res["categories"], {})

    @patch('ai_tools.services.openai_client.get_openai_client')
    def test_moderate_text_flagged(self, mock_get_openai_client):
        mock_client = MagicMock()
        mock_get_openai_client.return_value = mock_client
        mock_results = MagicMock()
        mock_results.flagged = True
        mock_results.categories = MagicMock()
        # Mock categories attributes
        mock_results.categories.__dict__ = {'violence': True, 'sexual': False}
        mock_response = MagicMock()
        mock_response.results = [mock_results]
        mock_client.moderations.create.return_value = mock_response

        res = moderate_text("Some harmful text.", user=self.user)
        self.assertTrue(res["flagged"])
        self.assertTrue(res["categories"]['violence'])

    def test_usage_limit_and_increment(self):
        allowed = user_can_use_ai(self.user)
        self.assertTrue(allowed)
        
        increment_ai_usage(self.user, tokens_input=50, tokens_output=50)
        limit_obj = AIUsageLimit.objects.get(user=self.user)
        self.assertEqual(limit_obj.requests_count, 1)
        self.assertEqual(limit_obj.tokens_used, 100)

        # Set requests count to max limit to trigger limit blocking
        limit_obj.requests_count = 30
        limit_obj.save()

        allowed_again = user_can_use_ai(self.user)
        self.assertFalse(allowed_again)


class AIToolsViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Create users
        self.tutor_user = User.objects.create_user(username='tutor1', password='password1')
        self.tutor_profile = UserProfile.objects.create(user=self.tutor_user, role='tutor')

        self.student_user = User.objects.create_user(username='student1', password='password1')
        self.student_profile = UserProfile.objects.create(user=self.student_user, role='student')

        # Create Course objects
        self.subject = Subject.objects.create(name="Math")
        self.class_level = ClassLevel.objects.create(name="Grade 5")
        self.course = Course.objects.create(
            title="Algebra Basics",
            slug="algebra-basics",
            subject=self.subject,
            class_level=self.class_level,
            created_by=self.tutor_user,
            is_free=True
        )
        self.module = Module.objects.create(course=self.course, title="Module 1", order=1)
        self.lesson = Lesson.objects.create(
            module=self.module,
            title="Introduction to X",
            slug="intro-to-x",
            content="Welcome to algebra.",
            order=1
        )

        # Enroll Student
        self.enrollment = Enrollment.objects.create(
            student=self.student_user,
            course=self.course,
            status='active'
        )

        # Report
        self.report = StudentProgressReport.objects.create(
            student=self.student_user,
            course=self.course,
            title="Math Progress Report",
            lesson_progress_percentage=100,
            assessment_average=90,
            assignment_average=85,
            overall_percentage=91.6,
            generated_by=self.tutor_user
        )

    @patch('ai_tools.services.openai_client.get_openai_client')
    def test_lesson_ai_assistant_get(self, mock_get_openai_client):
        self.client.login(username='student1', password='password1')
        response = self.client.get(reverse('ai_tools:lesson_ai_assistant', kwargs={
            'course_slug': self.course.slug,
            'lesson_slug': self.lesson.slug
        }))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ai_tools/lesson_ai_assistant.html')

    @patch('ai_tools.services.openai_client.get_openai_client')
    def test_lesson_ai_assistant_post_success(self, mock_get_openai_client):
        # Mock moderation
        mock_client = MagicMock()
        mock_get_openai_client.return_value = mock_client
        mock_results = MagicMock()
        mock_results.flagged = False
        mock_results.categories = MagicMock()
        mock_results.categories.__dict__ = {}
        mock_mod_response = MagicMock()
        mock_mod_response.results = [mock_results]
        mock_client.moderations.create.return_value = mock_mod_response

        # Mock chat completion
        mock_message = MagicMock()
        mock_message.content = "This is a helpful educational answer."
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_chat_response = MagicMock()
        mock_chat_response.choices = [mock_choice]
        mock_chat_response.usage = MagicMock()
        mock_chat_response.usage.prompt_tokens = 100
        mock_chat_response.usage.completion_tokens = 50
        mock_client.chat.completions.create.return_value = mock_chat_response

        self.client.login(username='student1', password='password1')
        response = self.client.post(reverse('ai_tools:lesson_ai_assistant', kwargs={
            'course_slug': self.course.slug,
            'lesson_slug': self.lesson.slug
        }), {'message': "Explain variable X to me."})

        self.assertEqual(response.status_code, 200)
        self.assertIn("This is a helpful educational answer.", response.json()['response'])

    @patch('ai_tools.services.openai_client.get_openai_client')
    def test_generate_report_comment_post_success(self, mock_get_openai_client):
        mock_client = MagicMock()
        mock_get_openai_client.return_value = mock_client
        mock_results = MagicMock()
        mock_results.flagged = False
        mock_results.categories = MagicMock()
        mock_results.categories.__dict__ = {}
        mock_mod_response = MagicMock()
        mock_mod_response.results = [mock_results]
        mock_client.moderations.create.return_value = mock_mod_response

        # Mock structured json response
        mock_message = MagicMock()
        mock_message.content = '{"summary": "Doing great", "strengths": "Math", "areas_for_improvement": "speed", "recommendation": "practice", "tutor_comment": "Excellent student progress!"}'
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_chat_response = MagicMock()
        mock_chat_response.choices = [mock_choice]
        mock_chat_response.usage = MagicMock()
        mock_chat_response.usage.prompt_tokens = 100
        mock_chat_response.usage.completion_tokens = 50
        mock_client.chat.completions.create.return_value = mock_chat_response

        self.client.login(username='tutor1', password='password1')
        response = self.client.post(reverse('ai_tools:generate_report_comment', kwargs={
            'report_id': self.report.id
        }), {'generate': '1'}, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Excellent student progress!")
