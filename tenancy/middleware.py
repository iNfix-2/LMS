from .models import Tenant, TenantUserMapping

class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(':')[0]
        parts = host.split('.')
        tenant = None

        # Check if we have a subdomain on localhost
        if len(parts) > 1 and parts[-1] == 'localhost':
            subdomain = parts[0]
            if subdomain not in ('www', '127'):
                try:
                    tenant = Tenant.objects.get(subdomain=subdomain)
                except (Tenant.DoesNotExist, Exception):
                    pass

        # Fallback to mapped tenant for logged-in user if still not set
        if not tenant and request.user.is_authenticated:
            try:
                mapping = TenantUserMapping.objects.get(user=request.user)
                tenant = mapping.tenant
            except (TenantUserMapping.DoesNotExist, Exception):
                pass

        # Global fallback to the first tenant in database
        if not tenant:
            try:
                tenant = Tenant.objects.first()
            except Exception:
                pass

        request.tenant = tenant
        return self.get_response(request)
