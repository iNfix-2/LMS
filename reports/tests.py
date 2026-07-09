from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from accounts.models import UserProfile, StudentProfile, TutorProfile
from courses.models import Course, Subject, ClassLevel, Module, Lesson
from enrollments.models import Enrollment, LessonProgress
from assessments.models import Assessment, Question, AssessmentAttempt, StudentAnswer
from assignments.models import Assignment, AssignmentSubmission
from reports.models import StudentProgressReport

class Sprint4LMSIntegrationTests(TestCase):
    def setUp(self):
        # 1. Create Users
        self.student_user = User.objects.create_user(username='student_test', password='password123')
        self.tutor_user = User.objects.create_user(username='tutor_test', password='password123')
        self.guardian_user = User.objects.create_user(username='guardian_test', password='password123')
        self.admin_user = User.objects.create_superuser(username='admin_test', password='password123')

        # 2. Create User Profiles
        self.student_profile = UserProfile.objects.create(user=self.student_user, role='student', phone='123')
        self.tutor_profile = UserProfile.objects.create(user=self.tutor_user, role='tutor', phone='456')
        self.guardian_profile = UserProfile.objects.create(user=self.guardian_user, role='guardian', phone='789')
        self.admin_profile = UserProfile.objects.create(user=self.admin_user, role='admin', phone='000')

        # 3. Create Student & Tutor Profiles
        self.student_profile_details = StudentProfile.objects.create(
            user=self.student_user,
            guardian=self.guardian_user,
            class_level='Junior Secondary'
        )
        self.tutor_profile_details = TutorProfile.objects.create(
            user=self.tutor_user,
            bio='Expert math tutor',
            subjects='Mathematics',
            is_approved=True
        )

        # 4. Create Subject & Course
        self.subject = Subject.objects.create(name='Mathematics', slug='mathematics')
        self.class_level = ClassLevel.objects.create(name='Junior Secondary')
        self.course = Course.objects.create(
            title='Algebra 101',
            slug='algebra-101',
            subject=self.subject,
            class_level=self.class_level,
            description='Basic Algebra',
            created_by=self.tutor_user,
            is_published=True
        )
        self.course.assigned_tutors.add(self.tutor_user)

        # 5. Create Module & Lesson
        self.module = Module.objects.create(course=self.course, title='Variables', order=1)
        self.lesson = Lesson.objects.create(module=self.module, title='Intro to X', slug='intro-to-x', order=1)

        # 6. Enroll Student
        self.enrollment = Enrollment.objects.create(student=self.student_user, course=self.course, status='active')
        self.lesson_progress = LessonProgress.objects.create(enrollment=self.enrollment, lesson=self.lesson, is_completed=True)

        # 7. Create Assessment & Theory Question
        self.assessment = Assessment.objects.create(
            course=self.course,
            title='Algebra Quiz 1',
            description='Test variables',
            pass_mark=50,
            show_corrections=True,
            created_by=self.tutor_user,
            is_published=True
        )
        self.theory_question = Question.objects.create(
            assessment=self.assessment,
            question_text='Describe how variables work.',
            question_type='theory',
            mark=10,
            order=1
        )
        self.attempt = AssessmentAttempt.objects.create(
            student=self.student_user,
            assessment=self.assessment,
            status='submitted',
            score=0,
            total_marks=10
        )
        self.student_answer = StudentAnswer.objects.create(
            attempt=self.attempt,
            question=self.theory_question,
            text_answer='Variables represent unknown quantities.',
            is_graded=False,
            mark_awarded=0
        )

        # 8. Create Assignment & Submission
        self.assignment = Assignment.objects.create(
            course=self.course,
            title='Algebra Assignment 1',
            description='Solve equations',
            total_marks=20,
            created_by=self.tutor_user,
            is_published=True
        )
        self.submission = AssignmentSubmission.objects.create(
            student=self.student_user,
            assignment=self.assignment,
            answer_text='x = 5',
            status='submitted'
        )

    def test_student_report_dashboard(self):
        self.client.login(username='student_test', password='password123')
        response = self.client.get(reverse('student_report_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'reports/student_report_dashboard.html')
        self.assertIn('course_data', response.context)

    def test_guardian_dashboard(self):
        self.client.login(username='guardian_test', password='password123')
        response = self.client.get(reverse('guardian_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'reports/guardian_dashboard.html')
        self.assertIn('ward_data', response.context)

    def test_tutor_dashboard(self):
        self.client.login(username='tutor_test', password='password123')
        response = self.client.get(reverse('tutor_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'reports/tutor_dashboard.html')
        self.assertIn('course_list', response.context)

    def test_course_learners_view(self):
        self.client.login(username='tutor_test', password='password123')
        response = self.client.get(reverse('course_learners', args=[self.course.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'reports/course_learners.html')
        self.assertIn('pending_attempts', response.context)
        self.assertIn('pending_submissions', response.context)

    def test_admin_lms_dashboard(self):
        self.client.login(username='admin_test', password='password123')
        response = self.client.get(reverse('admin_lms_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'reports/admin_lms_dashboard.html')

    def test_manual_assessment_grading(self):
        self.client.login(username='tutor_test', password='password123')
        # Check GET request
        response = self.client.get(reverse('mark_assessment_attempt', args=[self.attempt.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'assessments/mark_attempt.html')

        # Check POST request
        post_data = {
            f'mark_{self.student_answer.id}': 8,
            f'feedback_{self.student_answer.id}': 'Excellent description!'
        }
        response = self.client.post(reverse('mark_assessment_attempt', args=[self.attempt.id]), post_data)
        # Should redirect back to assessment_result
        self.assertRedirects(response, reverse('assessment_result', args=[self.attempt.id]))

        # Check database updates
        self.student_answer.refresh_from_db()
        self.assertEqual(self.student_answer.mark_awarded, 8)
        self.assertEqual(self.student_answer.feedback, 'Excellent description!')
        self.assertTrue(self.student_answer.is_graded)

        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.score, 8)
        self.assertEqual(self.attempt.status, 'submitted')

    def test_manual_assignment_grading(self):
        self.client.login(username='tutor_test', password='password123')
        # Check GET request
        response = self.client.get(reverse('mark_assignment_submission', args=[self.submission.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'assignments/mark_submission.html')

        # Check POST request
        post_data = {
            'score': 18,
            'status': 'marked',
            'feedback': 'Good job!'
        }
        response = self.client.post(reverse('mark_assignment_submission', args=[self.submission.id]), post_data)
        # Should redirect back to assignment_submission_detail
        self.assertRedirects(response, reverse('assignment_submission_detail', args=[self.submission.id]))

        # Check database updates
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.score, 18)
        self.assertEqual(self.submission.status, 'marked')
        self.assertEqual(self.submission.feedback, 'Good job!')

    def test_report_generation_and_details(self):
        self.client.login(username='tutor_test', password='password123')
        # Generate report
        response = self.client.get(reverse('generate_student_course_report', args=[self.student_user.id, self.course.slug]))
        # Should redirect to report detail view
        latest_report = StudentProgressReport.objects.filter(student=self.student_user, course=self.course).latest('created_at')
        self.assertRedirects(response, reverse('student_progress_report_detail', args=[latest_report.id]))

        # Verify detail page
        response = self.client.get(reverse('student_progress_report_detail', args=[latest_report.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'reports/student_progress_report_detail.html')

        # Add comment
        post_data = {
            'tutor_comment': 'Great job overall!'
        }
        response = self.client.post(reverse('student_progress_report_detail', args=[latest_report.id]), post_data)
        # Detail view redirects or renders 200 depending on views.py. report_detail redirects to detail on POST success.
        # Let's verify redirection: redirect('student_progress_report_detail', report_id=report.id)
        self.assertRedirects(response, reverse('student_progress_report_detail', args=[latest_report.id]))
        latest_report.refresh_from_db()
        self.assertEqual(latest_report.tutor_comment, 'Great job overall!')
