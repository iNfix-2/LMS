import logging
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import Notification, EmailLog

User = get_user_model()
logger = logging.getLogger(__name__)

TEMPLATE_MAPPING = {
    'enrollment': 'emails/enrollment_confirmation.html',
    'payment': 'emails/payment_receipt.html',
    'receipt': 'emails/payment_receipt.html',
    'invoice': 'emails/invoice_created.html',
    'assignment': 'emails/assignment_submitted.html',
    'assessment': 'emails/assessment_submitted.html',
    'progress_report': 'emails/progress_report_ready.html',
    'subscription': 'emails/subscription_expiry.html',
    'reminder': 'emails/unpaid_invoice_reminder.html',
}


def create_notification(
    recipient,
    title,
    message,
    notification_type="system",
    delivery_channel="in_app",
    sender=None,
    related_invoice=None,
    related_payment=None,
    related_course=None,
    related_report=None
):
    """
    Creates a Notification and schedules/sends email if necessary.
    """
    notification = Notification.objects.create(
        recipient=recipient,
        sender=sender,
        title=title,
        message=message,
        notification_type=notification_type,
        delivery_channel=delivery_channel,
        status='pending',
        related_invoice=related_invoice,
        related_payment=related_payment,
        related_course=related_course,
        related_report=related_report
    )

    if delivery_channel in ['email', 'both']:
        send_email_notification(notification)
    else:
        # If in_app only, we mark status as sent (meaning in-app is delivered)
        notification.status = 'sent'
        notification.save()

    return notification


def send_email_notification(notification, template_name=None, context=None):
    """
    Sends email for a specific notification.
    Ensures errors are caught, logged in EmailLog and error_message field,
    and doesn't crash the main request thread.
    """
    recipient = notification.recipient
    if not recipient.email:
        notification.status = 'failed'
        notification.error_message = f"Recipient {recipient.username} has no email address."
        notification.save()
        return False

    if not template_name:
        template_name = TEMPLATE_MAPPING.get(notification.notification_type, 'emails/base_email.html')

    if not context:
        context = {
            'notification': notification,
            'recipient': recipient,
            'title': notification.title,
            'message': notification.message,
            'site_url': getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
        }

    # If there are related entities, add them to context
    if notification.related_invoice:
        context['invoice'] = notification.related_invoice
    if notification.related_payment:
        context['payment'] = notification.related_payment
    if notification.related_course:
        context['course'] = notification.related_course
    if notification.related_report:
        context['report'] = notification.related_report

    # Attempt to attach PDF if receipt or invoice
    attachments = []
    try:
        from .models import DocumentRecord
        if notification.notification_type in ['receipt', 'payment'] and notification.related_payment:
            doc = DocumentRecord.objects.filter(payment=notification.related_payment, document_type='receipt_pdf').first()
            if doc and doc.file:
                attachments.append((doc.file.name.split('/')[-1], doc.file.read(), 'application/pdf'))
        elif notification.notification_type == 'invoice' and notification.related_invoice:
            doc = DocumentRecord.objects.filter(invoice=notification.related_invoice, document_type='invoice_pdf').first()
            if doc and doc.file:
                attachments.append((doc.file.name.split('/')[-1], doc.file.read(), 'application/pdf'))
        elif notification.notification_type == 'progress_report' and notification.related_report:
            doc = DocumentRecord.objects.filter(report=notification.related_report, document_type='progress_report_pdf').first()
            if doc and doc.file:
                attachments.append((doc.file.name.split('/')[-1], doc.file.read(), 'application/pdf'))
    except Exception as e:
        logger.warning(f"Failed to load attachment for email: {str(e)}")

    success = send_template_email(
        recipient_email=recipient.email,
        subject=notification.title,
        template_name=template_name,
        context=context,
        recipient_user=recipient,
        related_notification=notification,
        attachments=attachments
    )

    if success:
        notification.status = 'sent'
        notification.email_sent_at = timezone.now()
    else:
        notification.status = 'failed'
        # Error message is already logged on EmailLog, we can retrieve the latest one
        last_log = EmailLog.objects.filter(related_notification=notification).first()
        if last_log:
            notification.error_message = last_log.error_message
    notification.save()
    return success


def send_template_email(
    recipient_email,
    subject,
    template_name,
    context,
    recipient_user=None,
    related_notification=None,
    attachments=None
):
    """
    Renders an HTML template and dispatches email. Records EmailLog history.
    """
    email_log = EmailLog.objects.create(
        recipient_email=recipient_email,
        recipient_user=recipient_user,
        subject=subject,
        template_name=template_name,
        status='pending',
        related_notification=related_notification
    )

    try:
        html_content = render_to_string(template_name, context)
        
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'Edukom Learning <no-reply@edukomlearning.com>')
        email = EmailMessage(
            subject=subject,
            body=html_content,
            from_email=from_email,
            to=[recipient_email]
        )
        email.content_subtype = "html"

        if attachments:
            for filename, content, mimetype in attachments:
                email.attach(filename, content, mimetype)

        email.send(fail_silently=False)

        email_log.status = 'sent'
        email_log.sent_at = timezone.now()
        email_log.save()
        return True

    except Exception as e:
        logger.error(f"Email delivery failed: {str(e)}")
        email_log.status = 'failed'
        email_log.error_message = str(e)
        email_log.save()
        return False


def notify_admins(title, message, notification_type="system"):
    """
    Sends in-app and email notifications to all admins/staff, 
    and dispatches an email to ADMIN_NOTIFICATION_EMAIL.
    """
    # Fetch all admins and staff
    admins = User.objects.filter(Q(is_staff=True) | Q(is_superuser=True))
    
    # In-app and email to all staff/admins
    for admin in admins:
        create_notification(
            recipient=admin,
            title=title,
            message=message,
            notification_type=notification_type,
            delivery_channel='both'
        )

    # If there's an ADMIN_NOTIFICATION_EMAIL configure that is not a staff's email (or just as a direct copy)
    admin_email = getattr(settings, 'ADMIN_NOTIFICATION_EMAIL', None)
    if admin_email:
        # Check if we already sent to this email through the loop above
        if not admins.filter(email=admin_email).exists():
            send_template_email(
                recipient_email=admin_email,
                subject=title,
                template_name='emails/base_email.html',
                context={
                    'title': title,
                    'message': message,
                    'site_url': getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
                }
            )


def notify_guardian_of_ward_event(student, title, message, notification_type, related_course=None, related_report=None):
    """
    Finds the guardian of the student, and sends notification only to them.
    """
    try:
        from accounts.models import StudentProfile
        profile = StudentProfile.objects.filter(user=student).first()
        if profile and profile.guardian:
            guardian = profile.guardian
            create_notification(
                recipient=guardian,
                title=title,
                message=message,
                notification_type=notification_type,
                delivery_channel='both',
                related_course=related_course,
                related_report=related_report
            )
            return True
    except Exception as e:
        logger.error(f"Failed to notify guardian of ward event: {str(e)}")
    
    return False
