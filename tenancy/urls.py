from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.tenant_admin_dashboard, name='tenant_admin_dashboard'),
    path('settings/', views.tenant_update_settings, name='tenant_update_settings'),
]
