import hmac
import hashlib
import requests
from django.conf import settings
from django.urls import reverse
from payments.models import PaymentTransaction

def initialize_paystack_transaction(invoice, request):
    """
    Initialize a transaction on Paystack.
    Creates/updates a PaymentTransaction object and returns the authorization URL.
    """
    # Fetch or create the transaction
    transaction, created = PaymentTransaction.objects.get_or_create(
        invoice=invoice,
        user=invoice.user,
        amount=invoice.amount,
        currency=invoice.currency,
        provider='paystack',
        status='pending'
    )

    # Convert amount to subunit (NGN uses kobo, multiply by 100)
    amount_subunit = int(transaction.amount * 100)
    
    # Callback URL
    callback_url = settings.SITE_URL.rstrip('/') + reverse("payments:paystack_callback")
    
    url = f"{settings.PAYSTACK_BASE_URL.rstrip('/')}/transaction/initialize"
    
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    # Guarantee a valid email format
    email = invoice.user.email
    if not email or '@' not in email:
        email = f"{invoice.user.username}@edukom.ng"
        
    metadata = {
        "invoice_id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "user_id": invoice.user.id,
    }
    if invoice.course:
        metadata["course_id"] = invoice.course.id
    if invoice.plan:
        metadata["plan_id"] = invoice.plan.id
        
    payload = {
        "email": email,
        "amount": amount_subunit,
        "reference": transaction.reference,
        "currency": transaction.currency,
        "callback_url": callback_url,
        "metadata": metadata
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        resp_data = response.json()
        
        if resp_data.get("status"):
            data = resp_data.get("data", {})
            transaction.authorization_url = data.get("authorization_url", "")
            transaction.access_code = data.get("access_code", "")
            transaction.provider_reference = data.get("reference", transaction.reference)
            transaction.save()
            return transaction.authorization_url
        else:
            raise Exception(f"Paystack initialization failed: {resp_data.get('message')}")
            
    except requests.exceptions.RequestException as e:
        raise Exception(f"Paystack service unavailable: {str(e)}")


def verify_paystack_transaction(reference):
    """
    Verify transaction status on Paystack server-side.
    """
    url = f"{settings.PAYSTACK_BASE_URL.rstrip('/')}/transaction/verify/{reference}"
    
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Paystack verification request failed: {str(e)}")


def verify_paystack_webhook_signature(request):
    """
    Verify the signature of incoming webhooks from Paystack.
    """
    paystack_signature = request.headers.get("x-paystack-signature") or request.META.get("HTTP_X_PAYSTACK_SIGNATURE")
    if not paystack_signature:
        return False
        
    payload = request.body
    secret = settings.PAYSTACK_SECRET_KEY.encode('utf-8')
    computed_sig = hmac.new(secret, payload, hashlib.sha512).hexdigest()
    
    return hmac.compare_digest(computed_sig, paystack_signature)
