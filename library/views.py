from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, Http404, HttpResponseForbidden
from accounts.decorators import is_tutor_user, is_admin_user, get_user_role
from enrollments.models import Enrollment
from .models import Resource
from .forms import ResourceForm
from courses.models import Course

@login_required
def library_list(request):
    user = request.user
    role = get_user_role(user)
    is_tutor = is_tutor_user(user)
    is_admin = is_admin_user(user)

    # Get search query & filters
    query = request.GET.get('q', '')
    resource_type = request.GET.get('type', '')
    course_id = request.GET.get('course', '')

    resources = Resource.objects.all()

    if query:
        resources = resources.filter(title__icontains=query) | resources.filter(description__icontains=query)

    if resource_type:
        resources = resources.filter(resource_type=resource_type)

    if course_id:
        resources = resources.filter(course_id=course_id)

    # Annotate resources with has_access for the current user
    # A user has access if:
    # 1. User is admin or tutor of the resource course (or uploader)
    # 2. Resource is free (is_free = True)
    # 3. User is student enrolled in the resource course
    # 4. Resource has no course associated (general resource)
    
    enrolled_course_ids = set()
    if user.is_authenticated and not (is_tutor or is_admin):
        enrolled_course_ids = set(
            Enrollment.objects.filter(student=user, status='active').values_list('course_id', flat=True)
        )

    for r in resources:
        if is_admin:
            r.has_access = True
        elif is_tutor:
            # Tutors can access all resources, but can only manage resources they uploaded or courses they teach
            r.has_access = True
            r.can_manage = (r.uploaded_by == user) or (r.course and user in r.course.assigned_tutors.all())
        else:
            r.has_access = r.is_free or (r.course is None) or (r.course_id in enrolled_course_ids)
            r.can_manage = False

    courses = Course.objects.all()
    # If tutor, filter courses dropdown to their courses
    if is_tutor and not is_admin:
        courses = courses.filter(assigned_tutors=user)

    context = {
        'resources': resources,
        'courses': courses,
        'resource_types': Resource.RESOURCE_TYPES,
        'is_tutor': is_tutor,
        'is_admin': is_admin,
        'query': query,
        'selected_type': resource_type,
        'selected_course': course_id,
    }
    return render(request, 'library/library_list.html', context)

@login_required
def upload_resource(request):
    if not (is_tutor_user(request.user) or is_admin_user(request.user)):
        messages.error(request, "Only tutors and administrators can upload resources to the library.")
        return redirect('library:library_list')

    if request.method == 'POST':
        form = ResourceForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            resource = form.save(commit=False)
            resource.uploaded_by = request.user
            resource.save()
            messages.success(request, f"Successfully uploaded '{resource.title}' to the content library.")
            return redirect('library:library_list')
        else:
            messages.error(request, "Failed to upload resource. Please check the form errors.")
    else:
        form = ResourceForm(user=request.user)

    return render(request, 'library/upload_resource.html', {'form': form})

@login_required
def download_resource(request, resource_id):
    resource = get_object_or_404(Resource, id=resource_id)
    user = request.user
    
    # Check permissions
    is_tutor = is_tutor_user(user)
    is_admin = is_admin_user(user)
    
    has_access = False
    if is_admin or is_tutor:
        has_access = True
    elif resource.is_free or resource.course is None:
        has_access = True
    else:
        # Check student enrollment
        has_access = Enrollment.objects.filter(student=user, course=resource.course, status='active').exists()

    if not has_access:
        messages.error(request, "You must be enrolled in the course to download this learning resource.")
        return redirect('course_detail', slug=resource.course.slug)

    # Track download
    resource.download_count += 1
    resource.save(update_fields=['download_count'])

    try:
        response = FileResponse(resource.file.open('rb'), as_attachment=True)
        return response
    except FileNotFoundError:
        raise Http404("The requested file was not found on the server.")

@login_required
def delete_resource(request, resource_id):
    resource = get_object_or_404(Resource, id=resource_id)
    user = request.user
    
    # Check if user is admin or the tutor who uploaded it
    can_delete = is_admin_user(user) or (is_tutor_user(user) and resource.uploaded_by == user)
    
    if not can_delete:
        messages.error(request, "You do not have permission to delete this resource.")
        return redirect('library:library_list')

    title = resource.title
    resource.delete()
    messages.success(request, f"Successfully deleted '{title}' from the content library.")
    return redirect('library:library_list')
