from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.urls import reverse
from accounts.models import UserProfile
from tenancy.models import Tenant, TenantUserMapping
from tenancy.middleware import TenantMiddleware

class TenancyTestCase(TestCase):
    def setUp(self):
        # Create a test tenant
        self.tenant = Tenant.objects.create(
            name="Edukom",
            subdomain="edukom",
            theme_color="#002769",
            theme_accent="#71A20A"
        )
        # Create an admin user
        self.admin_user = User.objects.create_superuser(
            username="admin_user",
            email="admin@edukom.com",
            password="password123"
        )
        # Create profile
        self.admin_profile = UserProfile.objects.create(
            user=self.admin_user,
            role="admin"
        )
        # Map admin to tenant
        TenantUserMapping.objects.create(
            user=self.admin_user,
            tenant=self.tenant
        )
        self.factory = RequestFactory()

    def test_tenant_middleware_subdomain(self):
        # Test request with tenant subdomain
        request = self.factory.get('/', HTTP_HOST='edukom.localhost:8000')
        request.user = self.admin_user
        
        middleware = TenantMiddleware(lambda req: req)
        response_req = middleware(request)
        
        self.assertEqual(response_req.tenant, self.tenant)

    def test_tenant_middleware_fallback(self):
        # Test request on base domain with mapped authenticated user
        request = self.factory.get('/', HTTP_HOST='localhost:8000')
        request.user = self.admin_user
        
        middleware = TenantMiddleware(lambda req: req)
        response_req = middleware(request)
        
        # Should fallback to mapped tenant
        self.assertEqual(response_req.tenant, self.tenant)

    def test_tenant_admin_dashboard_view(self):
        self.client.login(username="admin_user", password="password123")
        url = reverse('tenant_admin_dashboard')
        response = self.client.get(url, HTTP_HOST='edukom.localhost:8000')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Edukom")

    def test_tenant_branding_update_view(self):
        self.client.login(username="admin_user", password="password123")
        url = reverse('tenant_update_settings')
        
        # Post update
        post_data = {
            'name': 'Updated Academy Name',
            'theme_color': '#ff0000',
            'theme_accent': '#00ff00',
            'payout_account_number': '1234567890',
            'payout_bank_code': '044'
        }
        response = self.client.post(url, post_data, HTTP_HOST='edukom.localhost:8000')
        
        # Verify redirect to dashboard
        self.assertRedirects(response, reverse('tenant_admin_dashboard'))
        
        # Refresh and verify
        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.name, 'Updated Academy Name')
        self.assertEqual(self.tenant.theme_color, '#ff0000')
        self.assertEqual(self.tenant.payout_account_number, '1234567890')
