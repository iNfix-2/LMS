import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib import messages

from .models import GuardianConsent, DataPrivacyRequest, ModerationLog
from enrollments.models import Enrollment
from discussion.models import Topic, Post, DirectMessage
from accounts.models import UserProfile, StudentProfile

def approve_guardian_consent(request, token):
    consent = get_object_or_404(GuardianConsent, consent_token=token)
    if not consent.is_approved:
        consent.is_approved = True
        consent.approved_at = timezone.now()
        consent.save()

        # Activate the student user account
        student = consent.student
        student.is_active = True
        student.save()

    return render(request, 'compliance/consent_approved.html', {
        'student': consent.student
    })

@login_required
def privacy_dashboard(request):
    requests = DataPrivacyRequest.objects.filter(user=request.user).order_by('-created_at')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'request_export':
            DataPrivacyRequest.objects.create(user=request.user, request_type='export')
            messages.success(request, "Your data export request has been submitted. You can download it below.")
            return redirect('privacy_dashboard')
        elif action == 'request_delete':
            DataPrivacyRequest.objects.create(user=request.user, request_type='delete')
            messages.warning(request, "Your account deletion request has been submitted.")
            return redirect('privacy_dashboard')
            
    return render(request, 'compliance/privacy_dashboard.html', {
        'privacy_requests': requests
    })

@login_required
def download_data_export(request):
    user = request.user
    
    # Collect user data
    data = {
        'personal_info': {
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'date_joined': user.date_joined.isoformat(),
        }
    }
    
    # Profile
    try:
        profile = user.profile
        data['profile'] = {
            'role': profile.role,
            'phone': profile.phone,
        }
    except UserProfile.DoesNotExist:
        pass
        
    # StudentProfile
    try:
        sprofile = user.student_profile
        data['student_profile'] = {
            'guardian_email': sprofile.guardian.email if sprofile.guardian else None,
            'class_level': sprofile.class_level,
            'date_of_birth': sprofile.date_of_birth.isoformat() if sprofile.date_of_birth else None,
        }
    except StudentProfile.DoesNotExist:
        pass

    # Enrollments
    enrollments = Enrollment.objects.filter(student=user)
    data['enrollments'] = [
        {
            'course': e.course.title,
            'status': e.status,
            'enrolled_at': e.enrolled_at.isoformat(),
            'progress': e.progress_percentage,
        } for e in enrollments
    ]

    # Discussion Topics created
    topics = Topic.objects.filter(creator=user)
    data['discussion_topics'] = [
        {
            'title': t.title,
            'content': t.content,
            'created_at': t.created_at.isoformat(),
        } for t in topics
    ]

    # Forum Posts
    posts = Post.objects.filter(creator=user)
    data['discussion_posts'] = [
        {
            'topic': p.topic.title,
            'content': p.content,
            'created_at': p.created_at.isoformat(),
        } for p in posts
    ]

    # DMs sent
    dms_sent = DirectMessage.objects.filter(sender=user)
    data['sent_direct_messages'] = [
        {
            'recipient': dm.recipient.username,
            'content': dm.content,
            'created_at': dm.created_at.isoformat(),
        } for dm in dms_sent
    ]

    response_content = json.dumps(data, indent=4)
    response = HttpResponse(response_content, content_type='application/json')
    response['Content-Disposition'] = f'attachment; filename="edukom_data_export_{user.username}.json"'
    
    # Mark the request as processed if one exists
    DataPrivacyRequest.objects.filter(user=user, request_type='export', status='pending').update(
        status='processed', processed_at=timezone.now()
    )
    
    return response

@login_required
def execute_privacy_delete(request):
    if request.method == 'POST':
        user = request.user
        
        # Mark pending delete request as processed
        DataPrivacyRequest.objects.filter(user=user, request_type='delete', status='pending').update(
            status='processed', processed_at=timezone.now()
        )
        
        # Anonymize User data
        user.first_name = "Deleted"
        user.last_name = "User"
        user.email = f"deleted_user_{user.id}@edukom.ng"
        user.is_active = False
        user.save()
        
        # Scrub UserProfile and StudentProfile
        try:
            profile = user.profile
            profile.phone = ""
            profile.profile_image = None
            profile.save()
        except UserProfile.DoesNotExist:
            pass
            
        try:
            sprofile = user.student_profile
            sprofile.date_of_birth = None
            sprofile.save()
        except StudentProfile.DoesNotExist:
            pass
            
        # Log out user
        from django.contrib.auth import logout
        logout(request)
        
        messages.success(request, "Your account has been deleted and anonymized.")
        return redirect('homepage')
        
    return redirect('privacy_dashboard')

@login_required
def moderation_admin_view(request):
    # Verify user permissions
    is_admin = False
    try:
        if request.user.is_staff or request.user.profile.role == 'admin':
            is_admin = True
    except Exception:
        pass

    if not is_admin:
        return redirect('/')
        
    logs = ModerationLog.objects.all().order_by('-created_at')
    
    if request.method == 'POST':
        log_id = request.POST.get('log_id')
        log = get_object_or_404(ModerationLog, id=log_id)
        log.resolved = True
        log.save()
        messages.success(request, f"Moderation log {log.id} marked as resolved.")
        return redirect('moderation_admin_view')
        
    return render(request, 'compliance/moderation_admin.html', {
        'moderation_logs': logs
    })
