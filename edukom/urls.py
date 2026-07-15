"""edukom URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static
from payments.views import pricing_plans_list

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('homepage.urls')),
    path('Tutor/', include('tutors.urls')),
    path('account/', include('user.urls')),
    path('learn/plans/', pricing_plans_list, name='pricing_plans_list'),
    path('learn/', include('courses.urls')),
    path('learn/', include('enrollments.urls')),
    path('learn/', include('assessments.urls')),
    path('learn/', include('assignments.urls')),
    path('learn/', include('reports.urls')),
    path('learn/', include('payments.urls')),
    path('learn/', include('notifications.urls')),
    path('learn/', include('ai_tools.urls')),
    path('learn/', include('academics.urls')),
    path('learn/', include('interactive.urls')),
    path('learn/library/', include('library.urls')),
    path('learn/achievements/', include('achievements.urls')),
    path('learn/discussion/', include('discussion.urls')),
]



admin.site.site_title = "EDUKOM Admin"
admin.site.site_header = "Edukom learning Admin Dashboard"
admin.site.index_title = "Admin Page"

urlpatterns += static(settings.STATIC_URL, document_root = settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root = settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)
