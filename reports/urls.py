from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/reports/', views.student_report_dashboard, name='student_report_dashboard'),
    path('dashboard/guardian/', views.guardian_dashboard, name='guardian_dashboard'),
    path('dashboard/tutor/', views.tutor_dashboard, name='tutor_dashboard'),
    path('dashboard/admin-lms/', views.admin_lms_dashboard, name='admin_lms_dashboard'),
    path('tutor/courses/<slug:course_slug>/learners/', views.course_learners, name='course_learners'),
    path('reports/generate/<int:student_id>/<slug:course_slug>/', views.generate_student_course_report, name='generate_student_course_report'),
    path('reports/<int:report_id>/', views.report_detail, name='student_progress_report_detail'),
]
