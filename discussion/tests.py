from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from courses.models import Course
from enrollments.models import Enrollment
from discussion.models import Forum, Topic, Post, DirectMessage

User = get_user_model()

class DiscussionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = User.objects.create_user(username='student1', password='password123')
        self.student2 = User.objects.create_user(username='student2', password='password123')
        from courses.models import Subject, ClassLevel
        self.subject = Subject.objects.create(name='Science', slug='science')
        self.class_level = ClassLevel.objects.create(name='Grade 10')
        self.course = Course.objects.create(
            title='Introduction to Physics', 
            slug='intro-to-physics', 
            subject=self.subject,
            class_level=self.class_level,
            created_by=self.student,
            description='Test course', 
            is_published=True
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            status='active'
        )
        self.forum = Forum.objects.create(course=self.course)

    def test_course_forum_access_denied_if_not_enrolled(self):
        self.client.login(username='student2', password='password123')
        response = self.client.get(reverse('discussion:course_forum', args=[self.course.slug]))
        self.assertEqual(response.status_code, 302) # Redirected with error

    def test_course_forum_access_granted_if_enrolled(self):
        self.client.login(username='student1', password='password123')
        response = self.client.get(reverse('discussion:course_forum', args=[self.course.slug]))
        self.assertEqual(response.status_code, 200)

    def test_create_topic(self):
        self.client.login(username='student1', password='password123')
        response = self.client.post(
            reverse('discussion:course_forum', args=[self.course.slug]),
            {'title': 'How to calculate force?', 'content': 'Please give tips.'}
        )
        self.assertEqual(response.status_code, 302) # Success redirect
        self.assertTrue(Topic.objects.filter(title='How to calculate force?').exists())

    def test_post_reply(self):
        self.client.login(username='student1', password='password123')
        topic = Topic.objects.create(
            forum=self.forum,
            title='Force Tips',
            content='Discuss here',
            creator=self.student
        )
        response = self.client.post(
            reverse('discussion:topic_detail', args=[topic.slug]),
            {'content': 'Push the throttle forward.'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Post.objects.filter(topic=topic, content='Push the throttle forward.').exists())

    def test_direct_message_send_and_receive(self):
        self.client.login(username='student1', password='password123')
        response = self.client.post(
            reverse('discussion:direct_messages'),
            {'recipient': self.student2.id, 'content': 'Hey classmate!'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(DirectMessage.objects.filter(sender=self.student, recipient=self.student2, content='Hey classmate!').exists())
