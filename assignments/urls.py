from django.urls import path
from . import views

urlpatterns = [
    path('assignments/<slug:course_slug>/', views.course_assignments, name='course_assignments'),
    path('assignments/<slug:course_slug>/<slug:assignment_slug>/', views.assignment_detail, name='assignment_detail'),
    path('assignments/<slug:course_slug>/<slug:assignment_slug>/submit/', views.submit_assignment, name='submit_assignment'),
    path('submissions/<int:submission_id>/', views.assignment_submission_detail, name='assignment_submission_detail'),
    path('tutor/assignments/submissions/<int:submission_id>/mark/', views.mark_assignment_submission, name='mark_assignment_submission'),
]
