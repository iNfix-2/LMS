from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from courses.models import Course
from .models import Resource

User = get_user_model()

class LibraryTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='student1', password='password123')
        from courses.models import Subject, ClassLevel
        self.subject = Subject.objects.create(name='Aviation', slug='aviation')
        self.class_level = ClassLevel.objects.create(name='PPL')
        self.course = Course.objects.create(
            title='Intro to Flying', 
            slug='intro-to-flying', 
            subject=self.subject,
            class_level=self.class_level,
            created_by=self.user,
            description='Test course', 
            is_published=True
        )
        
        # Create a mock file
        self.test_file = SimpleUploadedFile(
            "flight_manual.pdf", 
            b"file_content", 
            content_type="application/pdf"
        )
        
        self.resource = Resource.objects.create(
            title='Cessna 172 Manual',
            description='Operating handbook',
            resource_type='pdf',
            course=self.course,
            file=self.test_file,
            is_free=True,
            uploaded_by=self.user,
            download_count=0
        )

    def test_library_list_view(self):
        self.client.login(username='student1', password='password123')
        response = self.client.get(reverse('library:library_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cessna 172 Manual')

    def test_library_filter_resource_type(self):
        self.client.login(username='student1', password='password123')
        response = self.client.get(reverse('library:library_list') + '?type=pdf')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cessna 172 Manual')

    def test_library_search(self):
        self.client.login(username='student1', password='password123')
        response = self.client.get(reverse('library:library_list') + '?q=Cessna')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cessna 172 Manual')

    def test_resource_download_increments_count(self):
        self.client.login(username='student1', password='password123')
        initial_downloads = self.resource.download_count
        response = self.client.get(reverse('library:download_resource', args=[self.resource.id]))
        self.assertEqual(response.status_code, 200)
        
        self.resource.refresh_from_db()
        self.assertEqual(self.resource.download_count, initial_downloads + 1)
