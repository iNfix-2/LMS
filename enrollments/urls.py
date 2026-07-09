from django.urls import path
from . import views

urlpatterns = [
    path('enroll/<slug:course_slug>/', views.enroll_in_course, name='enroll_in_course'),
    path('complete/<slug:course_slug>/<slug:lesson_slug>/', views.mark_lesson_complete, name='mark_lesson_complete'),
    path('dashboard/student/', views.student_dashboard, name='student_dashboard'),
]
