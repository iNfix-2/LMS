from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    path("checkout/course/<slug:course_slug>/", views.course_checkout, name="course_checkout"),
    path("checkout/plan/<slug:plan_slug>/", views.plan_checkout, name="plan_checkout"),
    path("initialize/invoice/<int:invoice_id>/", views.initialize_invoice_payment, name="initialize_invoice_payment"),
    path("paystack/callback/", views.paystack_callback, name="paystack_callback"),
    path("paystack/webhook/", views.paystack_webhook, name="paystack_webhook"),
    path("invoices/", views.invoice_list, name="invoice_list"),
    path("invoices/<int:invoice_id>/", views.invoice_detail, name="invoice_detail"),
    path("history/", views.payment_history, name="payment_history"),
    path("plans/", views.pricing_plans_list, name="pricing_plans_list"),
    path("admin/manual-access/", views.manual_access_grant, name="manual_access_grant"),
]
