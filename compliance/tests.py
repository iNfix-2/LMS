from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from datetime import date, timedelta
import json

from accounts.models import UserProfile, StudentProfile
from compliance.models import GuardianConsent, DataPrivacyRequest, ModerationLog
from compliance.utils import censor_content
from user.forms import StudentRegistrationForm

class ComplianceTestCase(TestCase):
    def setUp(self):
        # Create standard active user
        self.user = User.objects.create_user(
            username="student_normal",
            email="normal@student.com",
            password="password123"
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            role="student"
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.user,
            date_of_birth=date.today() - timedelta(days=365 * 15)  # 15 years old
        )

    def test_censor_profanity_and_pii(self):
        bad_text = "This is a shit message with badword and phone +2348033310626 and email test@test.com"
        censored, flagged, reasons = censor_content(bad_text)
        
        self.assertTrue(flagged)
        self.assertIn("PII detected: Email address", reasons)
        self.assertIn("PII detected: Phone number", reasons)
        self.assertIn("Profanity detected", reasons)
        
        self.assertNotIn("test@test.com", censored)
        self.assertNotIn("shit", censored)
        self.assertIn("****", censored)  # censored shit
        self.assertIn("[EMAIL REDACTED]", censored)
        self.assertIn("[PHONE REDACTED]", censored)

    def test_student_registration_under_13_flow(self):
        # Create registration data for a 10 year old
        dob = date.today() - timedelta(days=365 * 10)
        data = {
            'username': 'child_user',
            'email': 'child@student.com',
            'first_name': 'Child',
            'last_name': 'User',
            'password': 'password123',
            'confirm_password': 'password123',
            'date_of_birth': dob.isoformat(),
            'guardian_email': 'parent@guardian.com'
        }
        
        # Test form validation requires guardian email
        form_no_guardian = StudentRegistrationForm(data={**data, 'guardian_email': ''})
        self.assertFalse(form_no_guardian.is_valid())
        
        # Register child user
        response = self.client.post(reverse('register'), data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'account/consent_pending.html')
        
        # Verify user created but is inactive
        child = User.objects.get(username='child_user')
        self.assertFalse(child.is_active)
        
        # Verify consent record created
        consent = GuardianConsent.objects.get(student=child)
        self.assertEqual(consent.guardian_email, 'parent@guardian.com')
        self.assertFalse(consent.is_approved)

        # Approve consent using token
        approve_url = reverse('approve_guardian_consent', args=[consent.consent_token])
        approve_response = self.client.get(approve_url)
        self.assertEqual(approve_response.status_code, 200)
        self.assertTemplateUsed(approve_response, 'compliance/consent_approved.html')
        
        # Verify user is now active
        child.refresh_from_db()
        self.assertTrue(child.is_active)

    def test_gdpr_data_export_and_deletion(self):
        self.client.login(username="student_normal", password="password123")
        
        # Submit export request
        dashboard_url = reverse('privacy_dashboard')
        response = self.client.post(dashboard_url, {'action': 'request_export'})
        self.assertEqual(response.status_code, 302)
        
        self.assertTrue(DataPrivacyRequest.objects.filter(user=self.user, request_type='export').exists())
        
        # Download export
        export_url = reverse('download_data_export')
        export_response = self.client.get(export_url)
        self.assertEqual(export_response.status_code, 200)
        self.assertEqual(export_response['Content-Disposition'], f'attachment; filename="edukom_data_export_{self.user.username}.json"')
        
        # Verify JSON content contains personal info
        exported_data = json.loads(export_response.content)
        self.assertEqual(exported_data['personal_info']['username'], self.user.username)
        
        # Execute right to be forgotten (deletion)
        delete_url = reverse('execute_privacy_delete')
        delete_response = self.client.post(delete_url)
        self.assertEqual(delete_response.status_code, 302)
        
        # User should now be deactivated and anonymized
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertEqual(self.user.first_name, "Deleted")
        self.assertEqual(self.user.last_name, "User")
        self.assertNotEqual(self.user.email, "normal@student.com")
