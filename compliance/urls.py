from django.urls import path
from . import views

urlpatterns = [
    path('consent/approve/<uuid:token>/', views.approve_guardian_consent, name='approve_guardian_consent'),
    path('privacy/', views.privacy_dashboard, name='privacy_dashboard'),
    path('privacy/export/download/', views.download_data_export, name='download_data_export'),
    path('privacy/delete/', views.execute_privacy_delete, name='execute_privacy_delete'),
    path('moderation/', views.moderation_admin_view, name='moderation_admin_view'),
]
