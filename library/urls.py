from django.urls import path
from . import views

app_name = 'library'

urlpatterns = [
    path('', views.library_list, name='library_list'),
    path('upload/', views.upload_resource, name='upload_resource'),
    path('download/<int:resource_id>/', views.download_resource, name='download_resource'),
    path('delete/<int:resource_id>/', views.delete_resource, name='delete_resource'),
]
