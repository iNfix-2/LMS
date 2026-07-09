from django.contrib import admin
from .models import PricingPlan, CoursePricing, Invoice, PaymentTransaction, StudentSubscription, CourseAccess

@admin.register(PricingPlan)
class PricingPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'plan_type', 'price', 'currency', 'duration_days', 'is_active')
    list_filter = ('plan_type', 'is_active', 'currency')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(CoursePricing)
class CoursePricingAdmin(admin.ModelAdmin):
    list_display = ('course', 'price', 'currency', 'access_duration_days', 'is_active')
    list_filter = ('is_active', 'currency')
    search_fields = ('course__title',)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'user', 'invoice_type', 'amount', 'currency', 'status', 'paid_at', 'created_at')
    list_filter = ('invoice_type', 'status', 'currency', 'created_at')
    search_fields = ('invoice_number', 'user__username', 'user__email', 'notes')
    readonly_fields = ('invoice_number', 'created_at', 'updated_at')


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('reference', 'user', 'provider', 'amount', 'currency', 'status', 'paid_at', 'verified_at')
    list_filter = ('provider', 'status', 'currency', 'created_at')
    search_fields = ('reference', 'provider_reference', 'user__username', 'user__email', 'gateway_response')
    readonly_fields = ('reference', 'created_at', 'updated_at')


@admin.register(StudentSubscription)
class StudentSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('student', 'plan', 'status', 'starts_at', 'ends_at')
    list_filter = ('status', 'starts_at', 'ends_at')
    search_fields = ('student__username', 'student__email', 'plan__name')
    actions = ['cancel_subscriptions']

    @admin.action(description="Cancel selected subscriptions")
    def cancel_subscriptions(self, request, queryset):
        queryset.update(status='cancelled')
        self.message_user(request, "Selected subscriptions were successfully marked as cancelled.")


@admin.register(CourseAccess)
class CourseAccessAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'source', 'starts_at', 'expires_at', 'is_active')
    list_filter = ('source', 'is_active', 'starts_at', 'expires_at')
    search_fields = ('student__username', 'student__email', 'course__title')
    actions = ['deactivate_course_access']

    @admin.action(description="Mark selected course access as inactive")
    def deactivate_course_access(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, "Selected course accesses were successfully marked as inactive.")
