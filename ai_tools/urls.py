from django.urls import path
from . import views

app_name = 'ai_tools'

urlpatterns = [
    # Student AI tools
    path('ai/lesson/<slug:course_slug>/<slug:lesson_slug>/', views.lesson_ai_assistant, name='lesson_ai_assistant'),
    path('ai/lesson/<slug:course_slug>/<slug:lesson_slug>/summary/', views.lesson_ai_summary, name='lesson_ai_summary'),
    path('ai/lesson/<slug:course_slug>/<slug:lesson_slug>/practice/', views.generate_practice_questions, name='generate_practice_questions'),
    path('ai/study-recommendations/<slug:course_slug>/', views.student_study_recommendations, name='student_study_recommendations'),
    
    # Tutor AI tools
    path('ai/tutor/course/<slug:course_slug>/quiz-generator/', views.tutor_generate_quiz, name='tutor_generate_quiz'),
    path('ai/tutor/course/<slug:course_slug>/worksheet-generator/', views.tutor_generate_worksheet, name='tutor_generate_worksheet'),
    path('ai/tutor/reports/<int:report_id>/comment/', views.generate_report_comment, name='generate_report_comment'),
    
    # AI Review/Workflow tools
    path('ai/generated/<int:content_id>/', views.ai_generated_content_detail, name='ai_generated_content_detail'),
    path('ai/generated/<int:content_id>/approve/', views.approve_ai_generated_content, name='approve_ai_generated_content'),
    path('ai/generated/<int:content_id>/reject/', views.reject_ai_generated_content, name='reject_ai_generated_content'),
    path('ai/generated/<int:content_id>/publish-quiz/', views.publish_ai_quiz_draft, name='publish_ai_quiz_draft'),
    
    # Admin AI logs
    path('ai/admin/usage/', views.ai_usage_dashboard, name='ai_usage_dashboard'),
    path('ai/admin/safety-flags/', views.ai_safety_flags, name='ai_safety_flags'),
]
