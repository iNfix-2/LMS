from django.urls import path
from . import views

app_name = "academics"

urlpatterns = [
    path('calendar/', views.academic_calendar, name='academic_calendar'),
    path('timetable/', views.my_timetable, name='my_timetable'),
    path('timetable/class/<int:class_level_id>/', views.class_timetable, name='class_timetable'),
    
    path('live-classes/', views.live_class_list, name='live_class_list'),
    path('live-classes/<int:live_class_id>/', views.live_class_detail, name='live_class_detail'),
    path('live-classes/<int:live_class_id>/join/', views.join_live_class, name='join_live_class'),
    path('tutor/live-classes/create/', views.create_live_class, name='create_live_class'),
    path('tutor/live-classes/<int:live_class_id>/edit/', views.edit_live_class, name='edit_live_class'),
    
    path('tutor/attendance/', views.tutor_attendance_dashboard, name='tutor_attendance_dashboard'),
    path('tutor/attendance/create/<slug:course_slug>/', views.create_attendance_session, name='create_attendance_session'),
    path('tutor/attendance/<int:attendance_session_id>/mark/', views.mark_attendance, name='mark_attendance'),
    path('attendance/my/', views.my_attendance, name='my_attendance'),
    path('attendance/ward/<int:student_id>/', views.ward_attendance, name='ward_attendance'),
    
    path('admin/academics/', views.academic_admin_dashboard, name='academic_admin_dashboard'),
]
