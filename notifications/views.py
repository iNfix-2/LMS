from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, Http404
from django.utils import timezone
from django.contrib.auth.models import User
from accounts.decorators import role_required

from .models import Notification, EmailLog, ReminderRule, DocumentRecord
from .services import send_email_notification, send_template_email
from .pdf import generate_invoice_pdf, generate_receipt_pdf, generate_progress_report_pdf

# Import models from other apps lazily to avoid circular imports
from payments.models import Invoice, PaymentTransaction
from reports.models import StudentProgressReport
from accounts.models import StudentProfile


def is_staff_or_admin(user):
    return user.is_staff or user.is_superuser or (hasattr(user, 'profile') and user.profile.role == 'admin')


@login_required
def notification_list(request):
    user = request.user
    
    if is_staff_or_admin(user):
        # Admins see all, but can filter by user_id
        user_id = request.GET.get('user_id')
        if user_id:
            notifications = Notification.objects.filter(recipient_id=user_id)
            filtered_user = get_object_or_404(User, id=user_id)
        else:
            notifications = Notification.objects.all()
            filtered_user = None
    else:
        notifications = Notification.objects.filter(recipient=user)
        filtered_user = None
        
    unread_count = notifications.filter(status='pending').count()
    
    return render(request, 'notifications/notification_list.html', {
        'notifications': notifications,
        'unread_count': unread_count,
        'filtered_user': filtered_user,
        'is_admin': is_staff_or_admin(user)
    })


@login_required
def notification_detail(request, notification_id):
    user = request.user
    notification = get_object_or_404(Notification, id=notification_id)
    
    # Check permissions
    if not (notification.recipient == user or is_staff_or_admin(user)):
        messages.error(request, "You are not authorized to view this notification.")
        return redirect('notifications:notification_list')
        
    # Mark as read if not already read
    if notification.status in ['pending', 'sent', 'failed'] and notification.recipient == user:
        notification.status = 'read'
        notification.read_at = timezone.now()
        notification.save()
        
    return render(request, 'notifications/notification_detail.html', {
        'notification': notification
    })


@login_required
def mark_notification_read(request, notification_id):
    if request.method != 'POST':
        return redirect('notifications:notification_list')
        
    user = request.user
    notification = get_object_or_404(Notification, id=notification_id)
    
    # Check permissions
    if not (notification.recipient == user or is_staff_or_admin(user)):
        messages.error(request, "You are not authorized to modify this notification.")
        return redirect('notifications:notification_list')
        
    if notification.status != 'read':
        notification.status = 'read'
        notification.read_at = timezone.now()
        notification.save()
        messages.success(request, "Notification marked as read.")
        
    return redirect(request.META.get('HTTP_REFERER', 'notifications:notification_list'))


@login_required
def download_invoice_pdf(request, invoice_id):
    user = request.user
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    # Check permissions: owner or staff/admin
    if not (invoice.user == user or is_staff_or_admin(user)):
        messages.error(request, "You do not have permission to download this invoice.")
        return redirect('homepage')
        
    try:
        # Generate PDF if it doesn't exist
        record = generate_invoice_pdf(invoice, generated_by=user)
        
        response = HttpResponse(record.file.read(), content_type='application/pdf')
        filename = record.file.name.split('/')[-1]
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        messages.error(request, f"Error generating PDF invoice: {str(e)}")
        return redirect('payments:invoice_detail', invoice_id=invoice.id)


@login_required
def download_receipt_pdf(request, payment_id):
    user = request.user
    payment = get_object_or_404(PaymentTransaction, id=payment_id)
    
    # Check permissions: owner or staff/admin
    if not (payment.user == user or is_staff_or_admin(user)):
        messages.error(request, "You do not have permission to download this receipt.")
        return redirect('homepage')
        
    # Must be successful payment
    if payment.status != 'success':
        messages.error(request, "Receipts can only be generated for successful payments.")
        return redirect('payments:invoice_detail', invoice_id=payment.invoice.id)
        
    try:
        # Generate PDF if it doesn't exist
        record = generate_receipt_pdf(payment, generated_by=user)
        
        response = HttpResponse(record.file.read(), content_type='application/pdf')
        filename = record.file.name.split('/')[-1]
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        messages.error(request, f"Error generating PDF receipt: {str(e)}")
        return redirect('payments:invoice_detail', invoice_id=payment.invoice.id)


@login_required
def download_progress_report_pdf(request, report_id):
    user = request.user
    report = get_object_or_404(StudentProgressReport, id=report_id)
    
    # Authorization checks
    authorized = False
    if is_staff_or_admin(user):
        authorized = True
    elif report.student == user:
        authorized = True
    elif hasattr(user, 'profile') and user.profile.role == 'guardian':
        # Check if ward
        if StudentProfile.objects.filter(user=report.student, guardian=user).exists():
            authorized = True
    elif hasattr(user, 'profile') and user.profile.role == 'tutor':
        # Check if tutor can manage the course
        if report.course.can_be_managed_by(user):
            authorized = True
            
    if not authorized:
        messages.error(request, "You do not have permission to download this progress report.")
        return redirect('homepage')
        
    try:
        # Generate PDF if it doesn't exist
        record = generate_progress_report_pdf(report, generated_by=user)
        
        response = HttpResponse(record.file.read(), content_type='application/pdf')
        filename = record.file.name.split('/')[-1]
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        messages.error(request, f"Error generating PDF progress report: {str(e)}")
        return redirect('student_progress_report_detail', report_id=report.id)


@login_required
@role_required(allowed_roles=['admin'])
def email_log_list(request):
    logs = EmailLog.objects.all()
    status_filter = request.GET.get('status')
    if status_filter:
        logs = logs.filter(status=status_filter)
        
    return render(request, 'notifications/email_log_list.html', {
        'logs': logs,
        'status_filter': status_filter
    })


@login_required
@role_required(allowed_roles=['admin'])
def reminder_rule_list(request):
    rules = ReminderRule.objects.all()
    return render(request, 'notifications/reminder_rule_list.html', {
        'rules': rules
    })


@login_required
@role_required(allowed_roles=['admin'])
def resend_email_log(request, email_log_id):
    email_log = get_object_or_404(EmailLog, id=email_log_id)
    
    # Try resending the email
    success = False
    try:
        if email_log.related_notification:
            success = send_email_notification(email_log.related_notification)
        else:
            # Resend using direct rendering or stored subject/body
            success = send_template_email(
                recipient_email=email_log.recipient_email,
                subject=f"[Resend] {email_log.subject}",
                template_name=email_log.template_name or 'emails/base_email.html',
                context={
                    'title': email_log.subject,
                    'message': "This is a resent message.",
                    'site_url': '/'
                },
                recipient_user=email_log.recipient_user
            )
            
        if success:
            messages.success(request, f"Email to {email_log.recipient_email} resent successfully!")
        else:
            messages.error(request, "Failed to resend the email. Please inspect email logs for errors.")
    except Exception as e:
        messages.error(request, f"Error resending email: {str(e)}")
        
    return redirect('notifications:email_log_list')
