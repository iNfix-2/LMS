from django.utils import timezone
from enrollments.models import Enrollment
from .models import CourseAccess, StudentSubscription, Invoice, PaymentTransaction

def get_active_course_access(user, course):
    if not user or not user.is_authenticated:
        return None
    if user.is_staff or user.is_superuser:
        # Return a temporary in-memory CourseAccess object to signify staff/admin access
        return CourseAccess(student=user, course=course, source='manual', is_active=True)
    
    # Check valid direct CourseAccess
    access = CourseAccess.objects.filter(
        student=user,
        course=course,
        is_active=True
    ).order_by('-created_at').first()
    if access and access.is_valid:
        return access
        
    return None


def user_has_course_access(user, course):
    if course.is_free:
        return True
    if not user or not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
        
    # Check if they have a valid CourseAccess object
    access = CourseAccess.objects.filter(
        student=user,
        course=course,
        is_active=True
    )
    for acc in access:
        if acc.is_valid:
            return True
            
    # Check valid StudentSubscription whose plan grants the course
    subscriptions = StudentSubscription.objects.filter(
        student=user,
        status='active'
    )
    for sub in subscriptions:
        if sub.is_valid and sub.plan.grants_course(course):
            return True
            
    return False


def grant_course_access(student, course, source, invoice=None, payment=None, subscription=None, granted_by=None, duration_days=None):
    now = timezone.now()
    expires_at = None
    if duration_days:
        expires_at = now + timezone.timedelta(days=int(duration_days))

    # Look for existing active access for this student and course
    access = CourseAccess.objects.filter(
        student=student,
        course=course,
        is_active=True
    ).first()

    if access:
        access.source = source
        if invoice:
            access.invoice = invoice
        if payment:
            access.payment = payment
        if subscription:
            access.subscription = subscription
        if granted_by:
            access.granted_by = granted_by
        if expires_at:
            access.expires_at = expires_at
        access.save()
    else:
        access = CourseAccess.objects.create(
            student=student,
            course=course,
            source=source,
            invoice=invoice,
            payment=payment,
            subscription=subscription,
            granted_by=granted_by,
            starts_at=now,
            expires_at=expires_at,
            is_active=True
        )
    return access


def fulfill_successful_payment(payment_transaction):
    invoice = payment_transaction.invoice
    
    # Mark payment transaction success
    if payment_transaction.status != 'success':
        payment_transaction.status = 'success'
        payment_transaction.paid_at = timezone.now()
        payment_transaction.save()
        
    if invoice.status == 'paid':
        return {'status': 'already_fulfilled', 'invoice_id': invoice.id}
        
    invoice.mark_paid()
    student = payment_transaction.user
    
    if invoice.invoice_type == 'course_payment':
        course = invoice.course
        if course:
            duration_days = None
            if hasattr(course, 'pricing') and course.pricing.is_active:
                duration_days = course.pricing.access_duration_days
            
            grant_course_access(
                student=student,
                course=course,
                source='course_payment',
                invoice=invoice,
                payment=payment_transaction,
                duration_days=duration_days
            )
            
            # Create or activate Enrollment
            enrollment, created = Enrollment.objects.get_or_create(
                student=student,
                course=course,
                defaults={'status': 'active'}
            )
            if not created and enrollment.status != 'active':
                enrollment.status = 'active'
                enrollment.save()
                
            return {'status': 'fulfilled_course_access', 'invoice_id': invoice.id, 'course_id': course.id}
            
    elif invoice.invoice_type == 'subscription':
        plan = invoice.plan
        if plan:
            now = timezone.now()
            ends_at = now + timezone.timedelta(days=plan.duration_days)
            
            subscription, created = StudentSubscription.objects.get_or_create(
                student=student,
                plan=plan,
                defaults={
                    'invoice': invoice,
                    'payment': payment_transaction,
                    'status': 'active',
                    'starts_at': now,
                    'ends_at': ends_at
                }
            )
            if not created:
                subscription.status = 'active'
                subscription.invoice = invoice
                subscription.payment = payment_transaction
                subscription.starts_at = now
                subscription.ends_at = ends_at
                subscription.save()
                
            # Grant access to all courses in the plan
            courses_to_grant = list(plan.courses.all())
            for cl in plan.class_levels.all():
                for c in cl.courses.all():
                    if c not in courses_to_grant:
                        courses_to_grant.append(c)
                        
            for course in courses_to_grant:
                grant_course_access(
                    student=student,
                    course=course,
                    source='subscription',
                    invoice=invoice,
                    payment=payment_transaction,
                    subscription=subscription,
                    duration_days=plan.duration_days
                )
                
                enrollment, created = Enrollment.objects.get_or_create(
                    student=student,
                    course=course,
                    defaults={'status': 'active'}
                )
                if not created and enrollment.status != 'active':
                    enrollment.status = 'active'
                    enrollment.save()
                    
            res = {'status': 'fulfilled_subscription', 'invoice_id': invoice.id, 'plan_id': plan.id}
        else:
            res = {'status': 'fulfilled_other', 'invoice_id': invoice.id}
    else:
        res = {'status': 'fulfilled_other', 'invoice_id': invoice.id}

    # Trigger Notifications & Document Generation
    try:
        from notifications.pdf import generate_receipt_pdf
        from notifications.services import create_notification
        from accounts.models import StudentProfile
        import logging
        logger = logging.getLogger(__name__)

        # Generate receipt PDF
        generate_receipt_pdf(payment_transaction)

        # Notify Student
        create_notification(
            recipient=student,
            title="Payment Successful",
            message=f"Thank you for your payment of ₦{payment_transaction.amount}. Your reference: {payment_transaction.reference}.",
            notification_type="receipt",
            delivery_channel="both",
            related_payment=payment_transaction,
            related_invoice=invoice
        )

        # Notify Guardian if linked
        profile = StudentProfile.objects.filter(user=student).first()
        if profile and profile.guardian:
            create_notification(
                recipient=profile.guardian,
                title="Ward Payment Successful",
                message=f"A payment of ₦{payment_transaction.amount} has been successfully processed for your ward {student.username}.",
                notification_type="receipt",
                delivery_channel="both",
                related_payment=payment_transaction,
                related_invoice=invoice
            )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Fulfillment notification failed: {str(e)}")

    return res
