from tenancy.models import Tenant, TenantUserMapping, TenantCourseMapping
from django.contrib.auth.models import User
from courses.models import Course

tenant, created = Tenant.objects.get_or_create(
    subdomain='edukom',
    defaults={
        'name': 'Edukom',
        'theme_color': '#002769',
        'theme_accent': '#71A20A',
    }
)

if created:
    print(f"Created Tenant: {tenant.name}")
else:
    print(f"Tenant already exists: {tenant.name}")

# Map all existing users to this tenant
users = User.objects.all()
for u in users:
    mapping, m_created = TenantUserMapping.objects.get_or_create(user=u, tenant=tenant)
    if m_created:
        print(f"Mapped User {u.username} to {tenant.name}")

# Map all existing courses to this tenant
courses = Course.objects.all()
for c in courses:
    mapping, c_created = TenantCourseMapping.objects.get_or_create(course=c, tenant=tenant)
    if c_created:
        print(f"Mapped Course {c.title} to {tenant.name}")
