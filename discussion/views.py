from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth import get_user_model
from courses.models import Course
from enrollments.models import Enrollment
from accounts.decorators import is_tutor_user, is_admin_user
from .models import Forum, Topic, Post, DirectMessage
from .forms import TopicForm, PostForm, DirectMessageForm

User = get_user_model()

def check_forum_access(user, course):
    """Checks if a user is enrolled in the course or is a tutor/admin."""
    if user.is_staff or user.is_superuser:
        return True
    if is_tutor_user(user) and user in course.assigned_tutors.all():
        return True
    return Enrollment.objects.filter(student=user, course=course, status='active').exists()

@login_required
def course_forum(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug)
    if not check_forum_access(request.user, course):
        messages.error(request, "You must be enrolled in this course to access its discussion forum.")
        return redirect('course_detail', slug=course.slug)

    forum, created = Forum.objects.get_or_create(course=course)
    topics = forum.topics.all().select_related('creator')

    if request.method == 'POST':
        form = TopicForm(request.POST)
        if form.is_valid():
            topic = form.save(commit=False)
            topic.forum = forum
            topic.creator = request.user
            topic.save()

            # Content Moderation check
            from compliance.utils import censor_content
            from compliance.models import ModerationLog
            c_title, f_t, r_t = censor_content(topic.title)
            c_content, f_c, r_c = censor_content(topic.content)
            if f_t or f_c:
                reasons = list(set(r_t + r_c))
                ModerationLog.objects.create(
                    user=request.user,
                    content_type='forum_topic',
                    object_id=topic.id,
                    original_text=f"Title: {topic.title} | Content: {topic.content}",
                    censored_text=f"Title: {c_title} | Content: {c_content}",
                    flagged_reasons=reasons
                )
                topic.title = c_title
                topic.content = c_content
                topic.save()

            messages.success(request, "Topic created successfully!")
            return redirect('discussion:course_forum', course_slug=course.slug)
    else:
        form = TopicForm()

    return render(request, 'discussion/course_forum.html', {
        'forum': forum,
        'course': course,
        'topics': topics,
        'form': form,
    })

@login_required
def topic_detail(request, topic_slug):
    topic = get_object_or_404(Topic, slug=topic_slug)
    course = topic.forum.course
    if not check_forum_access(request.user, course):
        messages.error(request, "You do not have access to this forum topic.")
        return redirect('homepage')

    posts = topic.posts.filter(parent_post=None).select_related('creator').prefetch_related('replies__creator')

    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.topic = topic
            post.creator = request.user
            
            parent_id = request.POST.get('parent_post_id')
            if parent_id:
                post.parent_post_id = parent_id

            post.save()

            # Content Moderation check
            from compliance.utils import censor_content
            from compliance.models import ModerationLog
            c_content, f_c, r_c = censor_content(post.content)
            if f_c:
                ModerationLog.objects.create(
                    user=request.user,
                    content_type='forum_post',
                    object_id=post.id,
                    original_text=post.content,
                    censored_text=c_content,
                    flagged_reasons=r_c
                )
                post.content = c_content
                post.save()

            messages.success(request, "Reply posted successfully!")
            return redirect('discussion:topic_detail', topic_slug=topic.slug)
    else:
        form = PostForm()

    return render(request, 'discussion/topic_detail.html', {
        'topic': topic,
        'course': course,
        'posts': posts,
        'form': form,
    })

@login_required
def direct_messages(request):
    user = request.user
    
    # Get all direct messages where user is sender or recipient
    dms = DirectMessage.objects.filter(
        Q(sender=user) | Q(recipient=user)
    ).select_related('sender', 'recipient').order_by('created_at')

    # Group messages by conversation partner
    conversations = {}
    for dm in dms:
        partner = dm.recipient if dm.sender == user else dm.sender
        if partner not in conversations:
            conversations[partner] = []
        conversations[partner].append(dm)

    # Handle sending a new message
    active_partner_id = request.GET.get('user_id')
    active_partner = None
    active_chat = []
    
    if active_partner_id:
        active_partner = get_object_or_404(User, id=active_partner_id)
        active_chat = conversations.get(active_partner, [])
        # Mark received messages as read
        DirectMessage.objects.filter(sender=active_partner, recipient=user, is_read=False).update(is_read=True)

    if request.method == 'POST':
        form = DirectMessageForm(request.POST)
        if form.is_valid():
            dm = form.save(commit=False)
            dm.sender = user
            dm.save()

            # Content Moderation check
            from compliance.utils import censor_content
            from compliance.models import ModerationLog
            c_content, f_c, r_c = censor_content(dm.content)
            if f_c:
                ModerationLog.objects.create(
                    user=request.user,
                    content_type='direct_message',
                    object_id=dm.id,
                    original_text=dm.content,
                    censored_text=c_content,
                    flagged_reasons=r_c
                )
                dm.content = c_content
                dm.save()

            messages.success(request, "Message sent successfully!")
            return redirect(f"{request.path}?user_id={dm.recipient.id}")
    else:
        initial = {}
        if active_partner:
            initial['recipient'] = active_partner
        form = DirectMessageForm(initial=initial)

    # Get list of possible message recipients (tutors and students they interact with)
    # For simplicity, we can list tutors and students
    users = User.objects.exclude(id=user.id)
    if not (user.is_staff or user.is_superuser):
        # Limit students to their peers/tutors in enrolled courses
        enrolled_courses = Enrollment.objects.filter(student=user, status='active').values_list('course_id', flat=True)
        tutors = User.objects.filter(assigned_courses__in=enrolled_courses)
        peers = User.objects.filter(enrollments__course__in=enrolled_courses, enrollments__status='active')
        users = (tutors | peers).exclude(id=user.id).distinct()

    return render(request, 'discussion/direct_messages.html', {
        'conversations': conversations,
        'active_partner': active_partner,
        'active_chat': active_chat,
        'form': form,
        'users': users,
    })
