from django.contrib import admin
from .models import Tenant, TenantUserMapping, TenantCourseMapping, TenantPayout

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('name', 'subdomain', 'theme_color', 'created_at')
    search_fields = ('name', 'subdomain')

@admin.register(TenantUserMapping)
class TenantUserMappingAdmin(admin.ModelAdmin):
    list_display = ('user', 'tenant')
    search_fields = ('user__username', 'tenant__name')

@admin.register(TenantCourseMapping)
class TenantCourseMappingAdmin(admin.ModelAdmin):
    list_display = ('course', 'tenant')
    search_fields = ('course__title', 'tenant__name')

@admin.register(TenantPayout)
class TenantPayoutAdmin(admin.ModelAdmin):
    list_display = ('reference', 'tenant', 'amount', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('reference', 'tenant__name')
