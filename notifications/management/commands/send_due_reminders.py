import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from notifications.models import ReminderRule
from notifications.services import create_notification
from payments.models import Invoice, StudentSubscription
from assignments.models import Assignment, AssignmentSubmission
from enrollments.models import Enrollment
from accounts.models import StudentProfile

logger = logging.getLogger(__name__)
User = get_user_model()

class Command(BaseCommand):
    help = 'Processes active reminder rules and sends out notifications to users'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting reminder rule processing..."))
        
        active_rules = ReminderRule.objects.filter(is_active=True)
        if not active_rules.exists():
            self.stdout.write(self.style.SUCCESS("No active reminder rules found."))
            return
            
        for rule in active_rules:
            self.stdout.write(self.style.NOTICE(f"Processing rule: {rule.name} ({rule.reminder_type})"))
            try:
                if rule.reminder_type == 'unpaid_invoice':
                    self.process_unpaid_invoices(rule)
                elif rule.reminder_type == 'subscription_expiry':
                    self.process_subscription_expiry(rule)
                elif rule.reminder_type == 'assignment_due':
                    self.process_assignments_due(rule)
                else:
                    self.stdout.write(f"Skipping rule type '{rule.reminder_type}' (not implemented or no due dates)")
            except Exception as e:
                logger.error(f"Error processing rule {rule.name}: {str(e)}")
                self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
                
        self.stdout.write(self.style.SUCCESS("Reminder rule processing completed successfully."))

    def process_unpaid_invoices(self, rule):
        today = timezone.now().date()
        target_due_date = today + timezone.timedelta(days=rule.days_before)
        target_creation_date = today - timezone.timedelta(days=rule.days_before)
        
        # Invoices pending
        pending_invoices = Invoice.objects.filter(status='pending')
        count = 0
        
        for inv in pending_invoices:
            should_warn = False
            if inv.due_date and inv.due_date.date() == target_due_date:
                should_warn = True
            elif not inv.due_date and inv.created_at.date() == target_creation_date:
                should_warn = True
                
            if should_warn:
                # Dispatch reminders
                if rule.send_to_student:
                    create_notification(
                        recipient=inv.user,
                        title=f"Reminder: Unpaid Invoice {inv.invoice_number}",
                        message=f"You have an outstanding invoice {inv.invoice_number} of ₦{inv.amount} due. Please complete payment.",
                        notification_type="reminder",
                        delivery_channel="both",
                        related_invoice=inv
                    )
                
                if rule.send_to_guardian:
                    profile = StudentProfile.objects.filter(user=inv.user).first()
                    if profile and profile.guardian:
                        create_notification(
                            recipient=profile.guardian,
                            title=f"Reminder: Unpaid Ward Invoice {inv.invoice_number}",
                            message=f"Your ward {inv.user.username} has an outstanding invoice {inv.invoice_number} of ₦{inv.amount}. Please complete payment.",
                            notification_type="reminder",
                            delivery_channel="both",
                            related_invoice=inv
                        )
                count += 1
        self.stdout.write(f"Sent {count} unpaid invoice reminders.")

    def process_subscription_expiry(self, rule):
        today = timezone.now().date()
        target_expiry_date = today + timezone.timedelta(days=rule.days_before)
        
        active_subs = StudentSubscription.objects.filter(status='active', ends_at__isnull=False)
        count = 0
        
        for sub in active_subs:
            if sub.ends_at.date() == target_expiry_date:
                if rule.send_to_student:
                    create_notification(
                        recipient=sub.student,
                        title=f"Reminder: Subscription Expiry",
                        message=f"Your subscription to the plan '{sub.plan.name}' is expiring on {sub.ends_at.date()}. Please renew to keep access.",
                        notification_type="reminder",
                        delivery_channel="both",
                        related_invoice=sub.invoice
                    )
                if rule.send_to_guardian:
                    profile = StudentProfile.objects.filter(user=sub.student).first()
                    if profile and profile.guardian:
                        create_notification(
                            recipient=profile.guardian,
                            title=f"Reminder: Ward Subscription Expiry",
                            message=f"Your ward {sub.student.username}'s subscription to '{sub.plan.name}' is expiring on {sub.ends_at.date()}.",
                            notification_type="reminder",
                            delivery_channel="both",
                            related_invoice=sub.invoice
                        )
                count += 1
        self.stdout.write(f"Sent {count} subscription expiry reminders.")

    def process_assignments_due(self, rule):
        today = timezone.now().date()
        target_due_date = today + timezone.timedelta(days=rule.days_before)
        
        due_assignments = Assignment.objects.filter(is_published=True, due_date__isnull=False)
        count = 0
        
        for assignment in due_assignments:
            if assignment.due_date.date() == target_due_date:
                # Find all active enrollments for this course
                enrollments = Enrollment.objects.filter(course=assignment.course, status='active')
                for enr in enrollments:
                    student = enr.student
                    # Check if already submitted
                    submitted = AssignmentSubmission.objects.filter(assignment=assignment, student=student).exists()
                    if not submitted:
                        if rule.send_to_student:
                            create_notification(
                                recipient=student,
                                title=f"Reminder: Assignment '{assignment.title}' Due Soon",
                                message=f"The assignment '{assignment.title}' for course '{assignment.course.title}' is due on {assignment.due_date.date()}.",
                                notification_type="reminder",
                                delivery_channel="both",
                                related_course=assignment.course
                            )
                        if rule.send_to_guardian:
                            profile = StudentProfile.objects.filter(user=student).first()
                            if profile and profile.guardian:
                                create_notification(
                                    recipient=profile.guardian,
                                    title=f"Reminder: Ward Assignment '{assignment.title}' Due Soon",
                                    message=f"Your ward {student.username}'s assignment '{assignment.title}' is due on {assignment.due_date.date()}.",
                                    notification_type="reminder",
                                    delivery_channel="both",
                                    related_course=assignment.course
                                )
                        count += 1
        self.stdout.write(f"Sent {count} assignment due reminders.")
