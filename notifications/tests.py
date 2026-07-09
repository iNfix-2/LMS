from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core import mail
from django.core.management import call_command
from unittest.mock import patch
import io

from notifications.models import Notification, EmailLog, ReminderRule, DocumentRecord
from notifications.services import create_notification
from payments.models import Invoice, StudentSubscription, PaymentTransaction, PricingPlan
from assignments.models import Assignment, AssignmentSubmission
from courses.models import Course, Subject, ClassLevel
from reports.models import StudentProgressReport
from accounts.models import StudentProfile, UserProfile

User = get_user_model()

class NotificationTestCase(TestCase):
    def setUp(self):
        # Create users
        self.student_user = User.objects.create_user(username='student1', email='student1@test.com', password='password')
        self.guardian_user = User.objects.create_user(username='guardian1', email='guardian1@test.com', password='password')
        self.tutor_user = User.objects.create_user(username='tutor1', email='tutor1@test.com', password='password')
        self.admin_user = User.objects.create_superuser(username='admin1', email='admin1@test.com', password='password')
        
        # UserProfiles
        UserProfile.objects.create(user=self.student_user, role='student')
        UserProfile.objects.create(user=self.guardian_user, role='guardian')
        UserProfile.objects.create(user=self.tutor_user, role='tutor')
        UserProfile.objects.create(user=self.admin_user, role='admin')
        
        # Link Student to Guardian
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            guardian=self.guardian_user
        )
        
        # Setup course data
        self.subject = Subject.objects.create(name="Maths", slug="maths")
        self.class_level = ClassLevel.objects.create(name="JSS1")
        self.course = Course.objects.create(
            title="Algebra",
            slug="algebra",
            subject=self.subject,
            class_level=self.class_level,
            created_by=self.tutor_user,
            is_published=True
        )
        
        self.client = Client()

    def test_create_notification_service(self):
        """Test that create_notification creates models correctly and sends mail."""
        mail.outbox = []
        notification = create_notification(
            recipient=self.student_user,
            title="Welcome to Edukom",
            message="Your account is set up.",
            notification_type="system",
            delivery_channel="both"
        )
        
        # Check database
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(Notification.objects.first().title, "Welcome to Edukom")
        
        # Check email log
        self.assertEqual(EmailLog.objects.count(), 1)
        self.assertEqual(EmailLog.objects.first().recipient_email, "student1@test.com")
        
        # Check django mail outbox
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Welcome to Edukom", mail.outbox[0].subject)

    def test_notification_views_and_read_status(self):
        """Test listing, viewing, and marking notifications as read."""
        notification = create_notification(
            recipient=self.student_user,
            title="Grade update",
            message="Your assignment was marked.",
            notification_type="assignment"
        )
        
        self.client.login(username='student1', password='password')
        
        # List view
        response = self.client.get(reverse('notifications:notification_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Grade update")
        
        # Detail view should mark as read
        response = self.client.get(reverse('notifications:notification_detail', args=[notification.id]))
        self.assertEqual(response.status_code, 200)
        
        notification.refresh_from_db()
        self.assertEqual(notification.status, 'read')
        self.assertIsNotNone(notification.read_at)

    def test_download_invoice_and_receipt_permissions(self):
        """Test that only authorized users can download invoice and receipt PDFs."""
        invoice = Invoice.objects.create(
            user=self.student_user,
            amount=5000.00,
            invoice_type="course_payment",
            course=self.course,
            status="paid"
        )
        payment = PaymentTransaction.objects.create(
            invoice=invoice,
            user=self.student_user,
            amount=5000.00,
            status="success",
            reference="TX-123"
        )
        
        # Login other student
        other_user = User.objects.create_user(username='other_student', email='other@test.com', password='password')
        UserProfile.objects.create(user=other_user, role='student')
        
        self.client.login(username='other_student', password='password')
        
        # Try to download PDF invoice of student1 -> should redirect with error/denied
        invoice_url = reverse('notifications:download_invoice_pdf', args=[invoice.id])
        response = self.client.get(invoice_url)
        self.assertEqual(response.status_code, 302) # redirects to homepage or elsewhere
        
        # Login owner student1 -> should succeed in generating/retrieving PDF
        self.client.login(username='student1', password='password')
        with patch('notifications.pdf.render_to_pdf') as mock_render:
            mock_render.return_value = b"%PDF-1.4 mock content"
            response = self.client.get(invoice_url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_send_due_reminders_command(self):
        """Test the send_due_reminders management command executes rules."""
        # Create an unpaid invoice
        invoice = Invoice.objects.create(
            user=self.student_user,
            amount=4000.00,
            invoice_type="manual",
            status="pending",
            due_date=timezone.now() + timezone.timedelta(days=2)
        )
        
        # Create an active ReminderRule for unpaid invoices (2 days before)
        rule = ReminderRule.objects.create(
            name="Unpaid invoice reminder (2 days)",
            reminder_type="unpaid_invoice",
            days_before=2,
            is_active=True,
            send_to_student=True,
            send_to_guardian=True
        )
        
        # Run management command
        out = io.StringIO()
        call_command('send_due_reminders', stdout=out)
        
        # The command output should report sending reminders
        self.assertIn("Sent 1 unpaid invoice reminders", out.getvalue())
        
        # Check that notifications were created
        notifications = Notification.objects.filter(related_invoice=invoice)
        # Should have notified student and guardian (since student has guardian linked)
        self.assertEqual(notifications.count(), 2)
        
        student_notif = notifications.filter(recipient=self.student_user).first()
        self.assertIsNotNone(student_notif)
        self.assertIn("Unpaid Invoice", student_notif.title)
        
        guardian_notif = notifications.filter(recipient=self.guardian_user).first()
        self.assertIsNotNone(guardian_notif)
        self.assertIn("Unpaid Ward Invoice", guardian_notif.title)
