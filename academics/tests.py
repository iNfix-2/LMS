from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from accounts.models import UserProfile, StudentProfile, TutorProfile
from courses.models import Course, ClassLevel, Subject
from enrollments.models import Enrollment
from academics.models import (
    AcademicSession, AcademicTerm, AcademicWeek,
    TimetableSlot, LiveClass, AttendanceSession, AttendanceRecord
)
import datetime


class AcademicsTests(TestCase):
    def setUp(self):
        # 1. Create Users & Profiles
        self.admin = User.objects.create_superuser('admin_user', 'admin@test.com', 'adminpass')
        UserProfile.objects.create(user=self.admin, role='admin')

        self.tutor = User.objects.create_user('tutor_user', 'tutor@test.com', 'tutorpass')
        UserProfile.objects.create(user=self.tutor, role='tutor')
        TutorProfile.objects.create(user=self.tutor, is_approved=True)

        self.guardian = User.objects.create_user('guardian_user', 'guardian@test.com', 'guardianpass')
        UserProfile.objects.create(user=self.guardian, role='guardian')

        self.student = User.objects.create_user('student_user', 'student@test.com', 'studentpass')
        UserProfile.objects.create(user=self.student, role='student')
        self.student_profile = StudentProfile.objects.create(
            user=self.student,
            guardian=self.guardian,
            class_level="Grade 10"
        )

        self.other_student = User.objects.create_user('other_student_user', 'other@test.com', 'otherpass')
        UserProfile.objects.create(user=self.other_student, role='student')
        StudentProfile.objects.create(user=self.other_student, class_level="Grade 11")

        # 2. Create Course Hierarchy
        self.class_level = ClassLevel.objects.create(name="Grade 10")
        self.other_class_level = ClassLevel.objects.create(name="Grade 11")
        self.subject = Subject.objects.create(name="Mathematics")
        
        self.course = Course.objects.create(
            title="Maths 10",
            slug="maths-10",
            description="Grade 10 maths",
            subject=self.subject,
            class_level=self.class_level,
            created_by=self.tutor,
            is_published=True
        )
        self.course.assigned_tutors.add(self.tutor)

        # 3. Create Enrollment
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            status='active'
        )

        # 4. Create Academic Session, Term, Week
        self.session = AcademicSession.objects.create(
            name="2025/2026 Session",
            start_date=datetime.date(2025, 9, 1),
            end_date=datetime.date(2026, 7, 31),
            is_current=True
        )
        self.term = AcademicTerm.objects.create(
            session=self.session,
            name="First Term",
            term_number=1,
            start_date=datetime.date(2025, 9, 1),
            end_date=datetime.date(2025, 12, 15),
            is_current=True
        )
        self.week = AcademicWeek.objects.create(
            term=self.term,
            week_number=1,
            start_date=datetime.date(2025, 9, 1),
            end_date=datetime.date(2025, 9, 5),
            activity="Intro to Algebra"
        )

        # 5. Create Timetable Slot
        self.slot = TimetableSlot.objects.create(
            class_level=self.class_level,
            subject=self.subject,
            course=self.course,
            tutor=self.tutor,
            day_of_week="Monday",
            start_time=datetime.time(9, 0),
            end_time=datetime.time(10, 30),
            title="Algebra Lecture",
            slot_type="lesson",
            room="Room 101"
        )

        # 6. Create Live Class
        self.live_class = LiveClass.objects.create(
            course=self.course,
            timetable_slot=self.slot,
            tutor=self.tutor,
            title="Linear Equations Interactive Session",
            scheduled_start=timezone.now() + datetime.timedelta(days=1),
            scheduled_end=timezone.now() + datetime.timedelta(days=1, hours=1),
            provider="zoom",
            meeting_link="https://zoom.us/j/123456",
            status="scheduled",
            is_published=True
        )

    def test_academic_calendar_view(self):
        # Student can view
        self.client.login(username='student_user', password='studentpass')
        response = self.client.get(reverse('academics:academic_calendar'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2025/2026 Session")

    def test_my_timetable_view(self):
        # Student
        self.client.login(username='student_user', password='studentpass')
        response = self.client.get(reverse('academics:my_timetable'))
        self.assertEqual(response.status_code, 200)
        
        # Tutor
        self.client.login(username='tutor_user', password='tutorpass')
        response = self.client.get(reverse('academics:my_timetable'))
        self.assertEqual(response.status_code, 200)

        # Guardian
        self.client.login(username='guardian_user', password='guardianpass')
        response = self.client.get(reverse('academics:my_timetable'))
        self.assertEqual(response.status_code, 200)

    def test_class_timetable_authorization(self):
        # Student can view their own class level
        self.client.login(username='student_user', password='studentpass')
        response = self.client.get(reverse('academics:class_timetable', args=[self.class_level.id]))
        self.assertEqual(response.status_code, 200)

        # Student cannot view other class level
        response = self.client.get(reverse('academics:class_timetable', args=[self.other_class_level.id]))
        self.assertEqual(response.status_code, 403) # PermissionDenied returns 403

        # Guardian can view ward's class level
        self.client.login(username='guardian_user', password='guardianpass')
        response = self.client.get(reverse('academics:class_timetable', args=[self.class_level.id]))
        self.assertEqual(response.status_code, 200)

    def test_live_class_list_and_detail(self):
        self.client.login(username='student_user', password='studentpass')
        
        response = self.client.get(reverse('academics:live_class_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Linear Equations Interactive Session")

        response = self.client.get(reverse('academics:live_class_detail', args=[self.live_class.id]))
        self.assertEqual(response.status_code, 200)

    def test_join_live_class_creates_attendance(self):
        # Create attendance session for today
        attendance_session = AttendanceSession.objects.create(
            course=self.course,
            live_class=self.live_class,
            title="Live Attendance",
            date=timezone.now().date(),
            created_by=self.tutor
        )

        self.client.login(username='student_user', password='studentpass')
        
        # Verify no attendance record initially
        self.assertFalse(AttendanceRecord.objects.filter(attendance_session=attendance_session, student=self.student).exists())

        # Join live class
        response = self.client.get(reverse('academics:join_live_class', args=[self.live_class.id]))
        self.assertEqual(response.status_code, 302) # Redirects to zoom link
        self.assertEqual(response.url, "https://zoom.us/j/123456")

        # Verify attendance record was automatically generated
        self.assertTrue(AttendanceRecord.objects.filter(attendance_session=attendance_session, student=self.student).exists())
        record = AttendanceRecord.objects.get(attendance_session=attendance_session, student=self.student)
        self.assertEqual(record.status, 'present')

    def test_attendance_marking_and_absence_notification(self):
        # Create attendance session
        attendance_session = AttendanceSession.objects.create(
            course=self.course,
            title="Mathematics Lesson Roll",
            date=timezone.now().date(),
            created_by=self.tutor
        )
        record = AttendanceRecord.objects.create(
            attendance_session=attendance_session,
            student=self.student,
            status='present'
        )

        # Login as Tutor
        self.client.login(username='tutor_user', password='tutorpass')

        # Post attendance update: mark as absent
        post_data = {
            f'status_{record.id}': 'absent',
            f'notes_{record.id}': 'Missed class without excuse.'
        }
        response = self.client.post(reverse('academics:mark_attendance', args=[attendance_session.id]), post_data)
        self.assertEqual(response.status_code, 302)

        # Verify record updated
        record.refresh_from_db()
        self.assertEqual(record.status, 'absent')

    def test_academic_admin_dashboard_authorization(self):
        # Admin can view
        self.client.login(username='admin_user', password='adminpass')
        response = self.client.get(reverse('academics:academic_admin_dashboard'))
        self.assertEqual(response.status_code, 200)

        # Student cannot view
        self.client.login(username='student_user', password='studentpass')
        response = self.client.get(reverse('academics:academic_admin_dashboard'))
        self.assertEqual(response.status_code, 403)

