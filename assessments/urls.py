from django.urls import path
from . import views

urlpatterns = [
    path('assessments/result/<int:attempt_id>/', views.assessment_result, name='assessment_result'),
    path('tutor/assessments/attempts/<int:attempt_id>/mark/', views.mark_attempt_view, name='mark_assessment_attempt'),
    path('assessments/<slug:course_slug>/', views.course_assessments, name='course_assessments'),
    path('assessments/<slug:course_slug>/<slug:assessment_slug>/', views.assessment_detail, name='assessment_detail'),
    path('assessments/<slug:course_slug>/<slug:assessment_slug>/start/', views.start_assessment, name='start_assessment'),
    path('assessments/<slug:course_slug>/<slug:assessment_slug>/submit/', views.submit_assessment, name='submit_assessment'),
]
