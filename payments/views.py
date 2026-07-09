import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseForbidden

from courses.models import Course
from enrollments.models import Enrollment
from .models import PricingPlan, CoursePricing, Invoice, PaymentTransaction, StudentSubscription, CourseAccess
from .forms import ManualAccessGrantForm
from .services import user_has_course_access, grant_course_access, fulfill_successful_payment
from .providers.paystack import initialize_paystack_transaction, verify_paystack_transaction, verify_paystack_webhook_signature

@login_required
def course_checkout(request, course_slug):
    if request.user.is_staff or request.user.is_superuser:
        course = get_object_or_404(Course, slug=course_slug)
    else:
        course = get_object_or_404(Course, slug=course_slug, is_published=True)

    if course.is_free:
        grant_course_access(student=request.user, course=course, source='free')
        Enrollment.objects.get_or_create(student=request.user, course=course, defaults={'status': 'active'})
        messages.success(request, f"Successfully enrolled in free course: {course.title}!")
        return redirect('course_detail', slug=course.slug)

    if user_has_course_access(request.user, course):
        messages.info(request, "You already have access to this course.")
        return redirect('course_detail', slug=course.slug)

    pricing = getattr(course, 'pricing', None)
    if not pricing or not pricing.is_active:
        messages.error(request, "Pricing is not available for this course at this time.")
        return redirect('course_detail', slug=course.slug)

    # Get or create a pending invoice
    invoice, created = Invoice.objects.get_or_create(
        user=request.user,
        course=course,
        invoice_type='course_payment',
        status='pending',
        defaults={
            'amount': pricing.price,
            'currency': pricing.currency,
        }
    )

    if created:
        try:
            from notifications.pdf import generate_invoice_pdf
            from notifications.services import create_notification
            from accounts.models import StudentProfile
            
            generate_invoice_pdf(invoice)
            create_notification(
                recipient=request.user,
                title="New Invoice Created",
                message=f"A new invoice ({invoice.invoice_number}) has been created for amount ₦{invoice.amount}.",
                notification_type="invoice",
                delivery_channel="both",
                related_invoice=invoice
            )
            profile = StudentProfile.objects.filter(user=request.user).first()
            if profile and profile.guardian:
                create_notification(
                    recipient=profile.guardian,
                    title="New Ward Invoice Created",
                    message=f"A new invoice ({invoice.invoice_number}) has been created for your ward {request.user.username} for amount ₦{invoice.amount}.",
                    notification_type="invoice",
                    delivery_channel="both",
                    related_invoice=invoice
                )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Invoice notification failed: {str(e)}")

    # Get or create a pending transaction
    transaction, tx_created = PaymentTransaction.objects.get_or_create(
        invoice=invoice,
        user=request.user,
        amount=invoice.amount,
        currency=invoice.currency,
        provider='paystack',
        status='pending'
    )

    return render(request, 'payments/course_checkout.html', {
        'course': course,
        'pricing': pricing,
        'invoice': invoice,
        'transaction': transaction,
        'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY,
    })


@login_required
def plan_checkout(request, plan_slug):
    plan = get_object_or_404(PricingPlan, slug=plan_slug, is_active=True)

    # Check if student already has this subscription active
    active_sub = StudentSubscription.objects.filter(
        student=request.user,
        plan=plan,
        status='active'
    ).first()
    if active_sub and active_sub.is_valid:
        messages.info(request, f"You already have an active subscription to the {plan.name} plan.")
        return redirect('student_dashboard')

    invoice, created = Invoice.objects.get_or_create(
        user=request.user,
        plan=plan,
        invoice_type='subscription',
        status='pending',
        defaults={
            'amount': plan.price,
            'currency': plan.currency,
        }
    )

    if created:
        try:
            from notifications.pdf import generate_invoice_pdf
            from notifications.services import create_notification
            from accounts.models import StudentProfile
            
            generate_invoice_pdf(invoice)
            create_notification(
                recipient=request.user,
                title="New Subscription Invoice Created",
                message=f"A new invoice ({invoice.invoice_number}) has been created for your subscription to {plan.name} for amount ₦{invoice.amount}.",
                notification_type="invoice",
                delivery_channel="both",
                related_invoice=invoice
            )
            profile = StudentProfile.objects.filter(user=request.user).first()
            if profile and profile.guardian:
                create_notification(
                    recipient=profile.guardian,
                    title="New Ward Subscription Invoice Created",
                    message=f"A new invoice ({invoice.invoice_number}) has been created for your ward {request.user.username}'s subscription to {plan.name} for amount ₦{invoice.amount}.",
                    notification_type="invoice",
                    delivery_channel="both",
                    related_invoice=invoice
                )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Invoice notification failed: {str(e)}")

    transaction, tx_created = PaymentTransaction.objects.get_or_create(
        invoice=invoice,
        user=request.user,
        amount=invoice.amount,
        currency=invoice.currency,
        provider='paystack',
        status='pending'
    )

    return render(request, 'payments/plan_checkout.html', {
        'plan': plan,
        'invoice': invoice,
        'transaction': transaction,
        'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY,
    })


@login_required
def initialize_invoice_payment(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    if invoice.user != request.user and not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Permission denied.")
        return redirect('homepage')
        
    if invoice.status != 'pending':
        messages.error(request, f"This invoice is {invoice.status} and cannot be paid.")
        return redirect('payments:invoice_detail', invoice_id=invoice.id)
        
    try:
        auth_url = initialize_paystack_transaction(invoice, request)
        if auth_url:
            return redirect(auth_url)
        else:
            messages.error(request, "Failed to initialize payment with Paystack.")
            return redirect('payments:invoice_detail', invoice_id=invoice.id)
    except Exception as e:
        messages.error(request, f"Payment error: {str(e)}")
        return redirect('payments:invoice_detail', invoice_id=invoice.id)


@login_required
def paystack_callback(request):
    reference = request.GET.get('reference') or request.GET.get('trxref')
    if not reference:
        messages.error(request, "No transaction reference returned.")
        return redirect('payments:invoice_list')

    transaction = get_object_or_404(PaymentTransaction, reference=reference)
    if transaction.user != request.user and not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Permission denied.")
        return redirect('homepage')

    invoice = transaction.invoice

    try:
        verification_data = verify_paystack_transaction(reference)
        if verification_data.get('status') is True:
            data = verification_data.get('data', {})
            paystack_status = data.get('status')
            paystack_amount = data.get('amount')
            paystack_currency = data.get('currency')
            
            # Convert decimal amount to subunit integer to match Paystack's format
            expected_amount_subunit = int(invoice.amount * 100)
            
            if (paystack_status == 'success' and
                int(paystack_amount) == expected_amount_subunit and
                paystack_currency == invoice.currency and
                data.get('reference') == reference):
                
                transaction.gateway_response = data.get('gateway_response', '')
                transaction.channel = data.get('channel', '')
                transaction.raw_response = verification_data
                transaction.save()
                
                fulfill_successful_payment(transaction)
                
                return render(request, 'payments/payment_success.html', {
                    'invoice': invoice,
                    'transaction': transaction,
                })
            else:
                transaction.status = 'failed'
                transaction.gateway_response = f"Validation failed. Status: {paystack_status}"
                transaction.save()
                
                invoice.mark_failed()
                messages.error(request, f"Payment verification failed: status is {paystack_status}")
                return redirect('payments:invoice_detail', invoice_id=invoice.id)
        else:
            transaction.status = 'failed'
            transaction.gateway_response = verification_data.get('message', 'Failed verification')
            transaction.save()
            
            invoice.mark_failed()
            messages.error(request, f"Payment failed: {verification_data.get('message')}")
            return redirect('payments:invoice_detail', invoice_id=invoice.id)

    except Exception as e:
        messages.error(request, f"Verification failed: {str(e)}")
        return redirect('payments:invoice_detail', invoice_id=invoice.id)


@csrf_exempt
def paystack_webhook(request):
    if request.method != 'POST':
        return HttpResponse("Method not allowed", status=405)

    if not verify_paystack_webhook_signature(request):
        return HttpResponseForbidden("Signature verification failed")

    try:
        payload = json.loads(request.body)
        event = payload.get('event')
        
        if event == 'charge.success':
            data = payload.get('data', {})
            reference = data.get('reference')
            
            if reference:
                transaction = PaymentTransaction.objects.filter(reference=reference).first()
                if transaction:
                    invoice = transaction.invoice
                    verification_data = verify_paystack_transaction(reference)
                    if verification_data.get('status') is True:
                        v_data = verification_data.get('data', {})
                        paystack_status = v_data.get('status')
                        paystack_amount = v_data.get('amount')
                        paystack_currency = v_data.get('currency')
                        
                        expected_amount_subunit = int(invoice.amount * 100)
                        if (paystack_status == 'success' and
                            int(paystack_amount) == expected_amount_subunit and
                            paystack_currency == invoice.currency):
                            
                            transaction.gateway_response = v_data.get('gateway_response', '')
                            transaction.channel = v_data.get('channel', '')
                            transaction.raw_response = verification_data
                            transaction.save()
                            
                            fulfill_successful_payment(transaction)
    except Exception:
        pass
        
    return HttpResponse("Webhook Processed", status=200)


@login_required
def invoice_list(request):
    status_filter = request.GET.get('status')
    
    if request.user.is_staff or request.user.is_superuser:
        invoices = Invoice.objects.all()
    else:
        invoices = Invoice.objects.filter(user=request.user)
        
    if status_filter:
        invoices = invoices.filter(status=status_filter)
        
    return render(request, 'payments/invoice_list.html', {
        'invoices': invoices,
        'status_filter': status_filter,
    })


@login_required
def invoice_detail(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    if invoice.user != request.user and not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Permission denied.")
        return redirect('homepage')
        
    transactions = invoice.transactions.all()
    successful_transaction = transactions.filter(status='success').first()
    
    return render(request, 'payments/invoice_detail.html', {
        'invoice': invoice,
        'transactions': transactions,
        'successful_transaction': successful_transaction,
    })


@login_required
def payment_history(request):
    if request.user.is_staff or request.user.is_superuser:
        transactions = PaymentTransaction.objects.filter(status='success')
    else:
        transactions = PaymentTransaction.objects.filter(user=request.user, status='success')
        
    return render(request, 'payments/payment_history.html', {
        'transactions': transactions,
    })


@staff_member_required
def manual_access_grant(request):
    if request.method == 'POST':
        form = ManualAccessGrantForm(request.POST)
        if form.is_valid():
            student = form.cleaned_data['student']
            course = form.cleaned_data['course']
            duration_days = form.cleaned_data['duration_days']
            amount = form.cleaned_data['amount']
            notes = form.cleaned_data['notes']
            
            invoice = None
            payment = None
            
            if amount is not None and amount > 0:
                invoice = Invoice.objects.create(
                    user=student,
                    course=course,
                    invoice_type='manual',
                    amount=amount,
                    status='paid',
                    paid_at=timezone.now(),
                    notes=notes or "Manually granted course access with payment."
                )
                
                payment = PaymentTransaction.objects.create(
                    invoice=invoice,
                    user=student,
                    provider='manual',
                    amount=amount,
                    status='success',
                    paid_at=timezone.now(),
                    verified_at=timezone.now(),
                    gateway_response=notes or "Manually completed by staff"
                )
            
            grant_course_access(
                student=student,
                course=course,
                source='manual',
                invoice=invoice,
                payment=payment,
                duration_days=duration_days,
                granted_by=request.user
            )
            
            # Automatically enroll student
            enrollment, created = Enrollment.objects.get_or_create(
                student=student,
                course=course,
                defaults={'status': 'active'}
            )
            if not created and enrollment.status != 'active':
                enrollment.status = 'active'
                enrollment.save()
                
            messages.success(request, f"Successfully granted manual access to {student.username} for '{course.title}'!")
            return redirect('payments:manual_access_grant')
    else:
        form = ManualAccessGrantForm()
        
    return render(request, 'payments/manual_access_grant.html', {
        'form': form,
    })


def pricing_plans_list(request):
    plans = PricingPlan.objects.filter(is_active=True)
    return render(request, 'payments/pricing_plans_list.html', {
        'plans': plans,
    })

