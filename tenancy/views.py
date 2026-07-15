from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
import uuid

from .models import Tenant, TenantUserMapping, TenantCourseMapping, TenantPayout
from courses.models import Course
from payments.models import Invoice

@login_required
def tenant_admin_dashboard(request):
    try:
        user_role = request.user.profile.role
    except Exception:
        user_role = None

    if not (request.user.is_staff or user_role == 'admin'):
        return redirect('/')

    mapping = get_object_or_404(TenantUserMapping, user=request.user)
    tenant = mapping.tenant

    # Fetch courses belonging to tenant
    courses = Course.objects.filter(tenant_mapping__tenant=tenant)

    # Fetch tutors belonging to tenant
    tutor_mappings = TenantUserMapping.objects.filter(tenant=tenant, user__profile__role='tutor')
    tutors = [m.user for m in tutor_mappings]

    # Fetch students belonging to tenant
    student_mappings = TenantUserMapping.objects.filter(tenant=tenant, user__profile__role='student')
    students = [m.user for m in student_mappings]

    # Fetch invoices/payments belonging to tenant courses
    invoices = Invoice.objects.filter(course__tenant_mapping__tenant=tenant).order_by('-created_at')
    
    # Calculate revenue
    total_earnings = sum(inv.amount for inv in invoices.filter(status='paid'))
    
    # Payouts
    payouts = TenantPayout.objects.filter(tenant=tenant).order_by('-created_at')

    # Handle payout request
    if request.method == 'POST' and 'request_payout' in request.POST:
        amount_str = request.POST.get('amount')
        try:
            amount = float(amount_str)
            if amount <= 0 or amount > total_earnings:
                messages.error(request, "Invalid payout amount.")
            else:
                reference = f"PAYOUT-{uuid.uuid4().hex[:8].upper()}"
                TenantPayout.objects.create(
                    tenant=tenant,
                    amount=amount,
                    status='pending',
                    reference=reference
                )
                messages.success(request, f"Payout request of {amount} successfully submitted.")
        except ValueError:
            messages.error(request, "Please enter a valid number.")
        return redirect('tenant_admin_dashboard')

    return render(request, 'tenancy/dashboard.html', {
        'tenant': tenant,
        'courses': courses,
        'tutors': tutors,
        'students': students,
        'invoices': invoices,
        'total_earnings': total_earnings,
        'payouts': payouts,
    })

@login_required
def tenant_update_settings(request):
    try:
        user_role = request.user.profile.role
    except Exception:
        user_role = None

    if not (request.user.is_staff or user_role == 'admin'):
        return redirect('/')

    mapping = get_object_or_404(TenantUserMapping, user=request.user)
    tenant = mapping.tenant

    if request.method == 'POST':
        name = request.POST.get('name')
        theme_color = request.POST.get('theme_color')
        theme_accent = request.POST.get('theme_accent')
        payout_account_number = request.POST.get('payout_account_number')
        payout_bank_code = request.POST.get('payout_bank_code')
        logo = request.FILES.get('logo')

        tenant.name = name
        tenant.theme_color = theme_color
        tenant.theme_accent = theme_accent
        tenant.payout_account_number = payout_account_number
        tenant.payout_bank_code = payout_bank_code
        if logo:
            tenant.logo = logo
        tenant.save()

        messages.success(request, "Branding and payment settings updated successfully.")
        return redirect('tenant_admin_dashboard')

    return render(request, 'tenancy/settings_form.html', {
        'tenant': tenant
    })
