from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    # In-App Notifications
    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/<int:notification_id>/', views.notification_detail, name='notification_detail'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    
    # Secure Document PDF Downloads
    path('documents/invoice/<int:invoice_id>/download/', views.download_invoice_pdf, name='download_invoice_pdf'),
    path('documents/receipt/<int:payment_id>/download/', views.download_receipt_pdf, name='download_receipt_pdf'),
    path('documents/report/<int:report_id>/download/', views.download_progress_report_pdf, name='download_progress_report_pdf'),
    
    # Admin Logs & Reminders
    path('admin/notifications/email-logs/', views.email_log_list, name='email_log_list'),
    path('admin/notifications/reminders/', views.reminder_rule_list, name='reminder_rule_list'),
    path('admin/notifications/resend-email/<int:email_log_id>/', views.resend_email_log, name='resend_email_log'),
]
