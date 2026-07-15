from django.urls import path
from . import views

app_name = 'interactive'

urlpatterns = [
    path('course/<slug:course_slug>/path-manager/', views.path_manager, name='path_manager'),
    path('course/<slug:course_slug>/toggle-sequential/', views.toggle_sequential, name='toggle_sequential'),
    path('course/<slug:course_slug>/prerequisite/add-course/', views.add_course_prerequisite, name='add_course_prerequisite'),
    path('course/<slug:course_slug>/prerequisite/remove-course/', views.remove_course_prerequisite, name='remove_course_prerequisite'),
    path('course/<slug:course_slug>/prerequisite/add-lesson/', views.add_lesson_prerequisite, name='add_lesson_prerequisite'),
    path('course/<slug:course_slug>/prerequisite/remove-lesson/', views.remove_lesson_prerequisite, name='remove_lesson_prerequisite'),
    path('course/<slug:course_slug>/lesson/<int:lesson_id>/interactive/', views.manage_lesson_interactive, name='manage_lesson_interactive'),
    path('h5p-player/<int:content_id>/', views.h5p_player, name='h5p_player'),
]
