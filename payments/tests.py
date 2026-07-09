from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch

from accounts.models import UserProfile
from courses.models import Course, ClassLevel, Subject
from payments.models import PricingPlan, CoursePricing, Invoice, PaymentTransaction, StudentSubscription, CourseAccess
from payments.services import user_has_course_access, grant_course_access

class PaymentSystemTests(TestCase):
    def setUp(self):
        # Create users
        self.user = User.objects.create_user(username='student1', email='student1@test.com', password='password123')
        self.profile = UserProfile.objects.create(user=self.user, role='student')
        self.tutor = User.objects.create_user(username='tutor1', email='tutor1@test.com', password='password123')
        UserProfile.objects.create(user=self.tutor, role='tutor')
        
        # Create Subject and Class Level
        self.subject = Subject.objects.create(name='Mathematics')
        self.class_level = ClassLevel.objects.create(name='JSS1')
        
        self.course = Course.objects.create(
            title='Intro to Mathematics',
            slug='intro-to-math',
            subject=self.subject,
            class_level=self.class_level,
            created_by=self.tutor,
            is_free=False,
            is_published=True
        )
        
        # Course pricing
        self.pricing = CoursePricing.objects.create(
            course=self.course,
            price=5000.00,
            currency='NGN',
            access_duration_days=90,
            is_active=True
        )
        
        # Pricing plan
        self.plan = PricingPlan.objects.create(
            name='Monthly Premium',
            slug='monthly-premium',
            plan_type='monthly_subscription',
            description='Access to all math courses',
            price=10000.00,
            currency='NGN',
            duration_days=30,
            is_active=True
        )
        self.plan.courses.add(self.course)

        self.client = Client()

    def test_user_has_course_access_default_false(self):
        # By default, a student doesn't have access to a paid course
        self.assertFalse(user_has_course_access(self.user, self.course))

    def test_user_has_course_access_free_course(self):
        # Free courses are accessible
        free_course = Course.objects.create(
            title='Free Intro',
            slug='free-intro',
            subject=self.subject,
            class_level=self.class_level,
            created_by=self.tutor,
            is_free=True,
            is_published=True
        )
        self.assertTrue(user_has_course_access(self.user, free_course))

    def test_user_has_course_access_manual_grant(self):
        # Manually grant access
        grant_course_access(self.user, self.course, source='manual', duration_days=30)
        self.assertTrue(user_has_course_access(self.user, self.course))

    def test_user_has_course_access_expired_grant(self):
        # Expired manual grant
        access = grant_course_access(self.user, self.course, source='manual', duration_days=30)
        access.expires_at = timezone.now() - timedelta(days=1)
        access.save()
        self.assertFalse(user_has_course_access(self.user, self.course))

    def test_user_has_course_access_subscription_grant(self):
        # Create an active subscription
        sub = StudentSubscription.objects.create(
            student=self.user,
            plan=self.plan,
            status='active',
            starts_at=timezone.now(),
            ends_at=timezone.now() + timedelta(days=30)
        )
        self.assertTrue(user_has_course_access(self.user, self.course))

    def test_course_checkout_view_authenticated(self):
        self.client.login(username='student1', password='password123')
        url = reverse('payments:course_checkout', kwargs={'course_slug': self.course.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/course_checkout.html')
        
        # Check that Invoice and PaymentTransaction are created
        self.assertTrue(Invoice.objects.filter(user=self.user, course=self.course).exists())
        self.assertTrue(PaymentTransaction.objects.filter(user=self.user, invoice__course=self.course).exists())

    def test_plan_checkout_view_authenticated(self):
        self.client.login(username='student1', password='password123')
        url = reverse('payments:plan_checkout', kwargs={'plan_slug': self.plan.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/plan_checkout.html')

    def test_invoice_list_view(self):
        self.client.login(username='student1', password='password123')
        invoice = Invoice.objects.create(
            user=self.user,
            course=self.course,
            invoice_type='course_payment',
            amount=5000.00,
            status='pending'
        )
        url = reverse('payments:invoice_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/invoice_list.html')
        self.assertContains(response, invoice.invoice_number)

    def test_invoice_detail_view(self):
        self.client.login(username='student1', password='password123')
        invoice = Invoice.objects.create(
            user=self.user,
            course=self.course,
            invoice_type='course_payment',
            amount=5000.00,
            status='pending'
        )
        url = reverse('payments:invoice_detail', kwargs={'invoice_id': invoice.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/invoice_detail.html')

    def test_payment_history_view(self):
        self.client.login(username='student1', password='password123')
        invoice = Invoice.objects.create(
            user=self.user,
            course=self.course,
            invoice_type='course_payment',
            amount=5000.00,
            status='paid'
        )
        PaymentTransaction.objects.create(
            invoice=invoice,
            user=self.user,
            amount=5000.00,
            status='success',
            paid_at=timezone.now()
        )
        url = reverse('payments:payment_history')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/payment_history.html')

    def test_pricing_plans_list_view(self):
        url = reverse('pricing_plans_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/pricing_plans_list.html')
        self.assertContains(response, self.plan.name)
