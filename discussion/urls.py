from django.urls import path
from . import views

app_name = 'discussion'

urlpatterns = [
    path('course/<slug:course_slug>/', views.course_forum, name='course_forum'),
    path('topic/<slug:topic_slug>/', views.topic_detail, name='topic_detail'),
    path('messages/', views.direct_messages, name='direct_messages'),
]
