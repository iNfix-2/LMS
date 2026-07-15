from django.urls import path
from . import views

app_name = 'achievements'

urlpatterns = [
    path('', views.my_achievements, name='my_achievements'),
    path('download/<int:cert_id>/', views.download_certificate, name='download_certificate'),
    path('verify/', views.verify_certificate, name='verify_certificate'),
]
