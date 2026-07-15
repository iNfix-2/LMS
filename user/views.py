from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from datetime import date

from homepage import models
from tutors import models as tmodels
from accounts.models import UserProfile, StudentProfile
from tenancy.models import TenantUserMapping
from compliance.models import GuardianConsent
from .forms import StudentRegistrationForm

@login_required
def GuardianListView(request):
    guardian = models.Guardian.objects.all()
    tutor = tmodels.Tutor.objects.all()
    context = {
        'guardian':guardian,
        'tutor':tutor
    }
    return render(request, 'Request/list.html', context)


@login_required
def GuardianDetailView(request, uid):
    guardian = models.Guardian.objects.get(uid=uid)
    context = {
        'guardian':guardian
    }
    return render(request, 'Request/details.html', context)


@login_required
def TutorDetailView(request, uid):
    tutor = tmodels.Tutor.objects.get(uid=uid)
    context = {
        'tutor':tutor
    }
    return render(request, 'Request/tutordetail.html', context)


def StudentRegisterView(request):
    if request.user.is_authenticated:
        return redirect('/')

    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            # Save User
            user = form.save(commit=False)
            password = form.cleaned_data.get('password')
            user.set_password(password)
            
            dob = form.cleaned_data.get('date_of_birth')
            guardian_email = form.cleaned_data.get('guardian_email')

            # Calculate Age
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

            if age < 13:
                user.is_active = False  # Deactivate until parent/guardian consent
            
            user.save()

            # Create UserProfile
            profile = UserProfile.objects.create(user=user, role='student')
            
            # Create StudentProfile
            # Check if guardian email already exists in users (mapping if so)
            guardian_user = None
            if guardian_email:
                guardian_user = User.objects.filter(email=guardian_email, profile__role='guardian').first()
            
            StudentProfile.objects.create(
                user=user,
                guardian=guardian_user,
                date_of_birth=dob
            )

            # Map user to the current Tenant (from middleware)
            if request.tenant:
                TenantUserMapping.objects.create(user=user, tenant=request.tenant)

            # Handle COPPA / Under-13 flow
            if age < 13:
                # Create Guardian Consent record
                consent = GuardianConsent.objects.create(
                    student=user,
                    guardian_email=guardian_email
                )

                # Send approval email to guardian
                approve_url = request.build_absolute_uri(
                    reverse('approve_guardian_consent', args=[consent.consent_token])
                )
                subject = "Edukom LMS — Verifiable Parental Consent Required"
                message = (
                    f"Hello,\n\n"
                    f"Your ward '{user.get_full_name() or user.username}' has registered an account on "
                    f"Edukom LMS ({request.tenant.name if request.tenant else 'Edukom Learning'}).\n\n"
                    f"Because your ward is under 13 years of age, we require your consent to activate their account "
                    f"in compliance with COPPA (Children's Online Privacy Protection Act).\n\n"
                    f"Please click the link below to verify and approve their registration:\n"
                    f"{approve_url}\n\n"
                    f"If you did not authorize this registration, you can ignore this email.\n\n"
                    f"Best regards,\n"
                    f"The Edukom Learning Team"
                )
                try:
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [guardian_email],
                        fail_silently=True
                    )
                except Exception:
                    pass

                return render(request, 'account/consent_pending.html', {
                    'student_name': user.get_full_name() or user.username,
                    'guardian_email': guardian_email
                })

            else:
                # Age 13 or over: log them in and redirect
                login(request, user)
                return redirect('/')
    else:
        form = StudentRegistrationForm()

    return render(request, 'account/register.html', {'form': form})