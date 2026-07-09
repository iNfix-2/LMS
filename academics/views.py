import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.utils import timezone
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth import get_user_model

User = get_user_model()

from .models import (
    AcademicSession,
    AcademicTerm,
    AcademicWeek,
    TimetableSlot,
    LiveClass,
    AttendanceSession,
    AttendanceRecord
)
from .services import (
    get_current_academic_session,
    get_current_academic_term,
    get_class_timetable,
    get_student_timetable,
    get_tutor_timetable,
    get_student_live_classes,
    get_tutor_live_classes,
    calculate_student_attendance_percentage
)
from .forms import (
    TimetableSlotForm,
    LiveClassForm,
    AttendanceSessionForm,
    AttendanceRecordForm
)
from courses.models import ClassLevel, Course, Module, Lesson
from enrollments.models import Enrollment


@login_required
def academic_calendar(request):
    """Displays the academic calendar containing weeks, sessions, and terms."""
    current_session = get_current_academic_session()
    current_term = get_current_academic_term()
    
    is_staff_or_admin = request.user.is_staff or request.user.is_superuser or (
        hasattr(request.user, 'profile') and request.user.profile.role == 'admin'
    )
    
    terms = AcademicTerm.objects.all() if is_staff_or_admin else AcademicTerm.objects.filter(is_current=True)
    weeks = AcademicWeek.objects.filter(term__in=terms).order_by('week_number')
    
    context = {
        'current_session': current_session,
        'current_term': current_term,
        'terms': terms,
        'weeks': weeks,
    }
    return render(request, 'academics/academic_calendar.html', context)


@login_required
def my_timetable(request):
    """Renders the dashboard for the current user's timetable based on their role."""
    role = getattr(request.user.profile, 'role', 'student') if hasattr(request.user, 'profile') else 'student'
    is_admin = request.user.is_staff or request.user.is_superuser or role == 'admin'
    
    context = {
        'role': role,
        'is_admin': is_admin,
    }
    
    if is_admin:
        context['class_levels'] = ClassLevel.objects.all()
    elif role == 'tutor':
        context['timetable'] = get_tutor_timetable(request.user)
    elif role == 'guardian':
        wards_data = []
        for profile in request.user.wards.all():
            wards_data.append({
                'student': profile.user,
                'timetable': get_student_timetable(profile.user)
            })
        context['wards_data'] = wards_data
    else:  # student
        context['timetable'] = get_student_timetable(request.user)
        
    return render(request, 'academics/my_timetable.html', context)


@login_required
def class_timetable(request, class_level_id):
    """Displays the timetable for a specific class level with permission boundaries."""
    class_level = get_object_or_404(ClassLevel, id=class_level_id)
    user = request.user
    role = getattr(user.profile, 'role', 'student') if hasattr(user, 'profile') else 'student'
    is_admin = user.is_staff or user.is_superuser or role == 'admin'
    
    # Permission Check
    authorized = False
    if is_admin:
        authorized = True
    elif role == 'tutor':
        # Check if they manage any course in this class level
        authorized = Course.objects.filter(class_level=class_level).filter(
            Q(created_by=user) | Q(assigned_tutors=user)
        ).exists()
    elif role == 'student':
        # Check if the student's class level matches
        authorized = hasattr(user, 'student_profile') and user.student_profile.class_level.lower() == class_level.name.lower()
    elif role == 'guardian':
        # Check if any ward belongs to this class level
        authorized = user.wards.filter(class_level__iexact=class_level.name).exists()
        
    if not authorized:
        raise PermissionDenied("You are not authorized to view this class timetable.")
        
    timetable = get_class_timetable(class_level)
    context = {
        'class_level': class_level,
        'timetable': timetable,
    }
    return render(request, 'academics/class_timetable.html', context)


@login_required
def live_class_list(request):
    """Lists upcoming and current live virtual classes filtered by user permissions."""
    role = getattr(request.user.profile, 'role', 'student') if hasattr(request.user, 'profile') else 'student'
    is_admin = request.user.is_staff or request.user.is_superuser or role == 'admin'
    
    if is_admin:
        live_classes = LiveClass.objects.all().order_by('scheduled_start')
    elif role == 'tutor':
        live_classes = get_tutor_live_classes(request.user)
    else:  # student / guardian
        # Guardians can view wards' upcoming live classes. Let's merge active courses for all wards if guardian.
        if role == 'guardian':
            ward_users = [w.user for w in request.user.wards.all()]
            enrolled_course_ids = Enrollment.objects.filter(student__in=ward_users, status='active').values_list('course_id', flat=True)
            live_classes = LiveClass.objects.filter(
                course_id__in=enrolled_course_ids,
                is_published=True
            ).order_by('scheduled_start')
        else:
            live_classes = get_student_live_classes(request.user)
            
    context = {
        'live_classes': live_classes,
        'role': role,
        'is_admin': is_admin,
    }
    return render(request, 'academics/live_class_list.html', context)


@login_required
def live_class_detail(request, live_class_id):
    """Displays information and action routes for a scheduled live class."""
    live_class = get_object_or_404(LiveClass, id=live_class_id)
    user = request.user
    role = getattr(user.profile, 'role', 'student') if hasattr(user, 'profile') else 'student'
    is_admin = user.is_staff or user.is_superuser or role == 'admin'
    
    # Permission Check: does user have access to this course?
    has_access = False
    if is_admin:
        has_access = True
    elif role == 'tutor':
        has_access = live_class.course.can_be_managed_by(user)
    elif role == 'student':
        has_access = Enrollment.objects.filter(student=user, course=live_class.course, status='active').exists()
    elif role == 'guardian':
        ward_users = [w.user for w in user.wards.all()]
        has_access = Enrollment.objects.filter(student__in=ward_users, course=live_class.course, status='active').exists()
        
    if not has_access:
        raise PermissionDenied("You do not have access to this live class.")
        
    # Check if we show links/passcode
    show_sensitive_data = is_admin or role == 'tutor' or (role == 'student' and has_access)
    
    # Check if student is active (for joining)
    show_join = False
    if live_class.status in ['scheduled', 'live'] and (role == 'student' or role == 'tutor' or is_admin):
        show_join = True
        
    context = {
        'live_class': live_class,
        'show_sensitive_data': show_sensitive_data,
        'show_join': show_join,
        'is_admin': is_admin,
        'is_tutor': role == 'tutor' or is_admin,
    }
    return render(request, 'academics/live_class_detail.html', context)


@login_required
def join_live_class(request, live_class_id):
    """Redirects students to virtual classroom links and logs attendance."""
    live_class = get_object_or_404(LiveClass, id=live_class_id)
    user = request.user
    role = getattr(user.profile, 'role', 'student') if hasattr(user, 'profile') else 'student'
    is_admin = user.is_staff or user.is_superuser or role == 'admin'
    
    # Check course access/enrollment
    has_access = False
    if is_admin:
        has_access = True
    elif role == 'tutor':
        has_access = live_class.course.can_be_managed_by(user)
    elif role == 'student':
        has_access = Enrollment.objects.filter(student=user, course=live_class.course, status='active').exists()
        
    if not has_access:
        raise PermissionDenied("You are not authorized to join this live class.")
        
    # Log Attendance for Student
    if role == 'student':
        # Look for an attendance session for this live class or course today
        session = AttendanceSession.objects.filter(live_class=live_class).first()
        if not session:
            session = AttendanceSession.objects.filter(course=live_class.course, date=timezone.now().date()).first()
            
        if session:
            # Determine if present or late
            status = 'present'
            if live_class.scheduled_start:
                # If student is joining 15 minutes late, mark as late
                fifteen_minutes_after_start = live_class.scheduled_start + datetime.timedelta(minutes=15)
                if timezone.now() > fifteen_minutes_after_start:
                    status = 'late'
                    
            record, created = AttendanceRecord.objects.get_or_create(
                attendance_session=session,
                student=user,
                defaults={
                    'status': status,
                    'notes': 'Automatically marked on joining live class.'
                }
            )
            if not created:
                # Update status to present/late if not marked already
                if record.status == 'absent':
                    record.status = status
                    record.notes = 'Updated status on joining live class.'
                    record.save()
                    
    return HttpResponseRedirect(live_class.meeting_link)


@login_required
def create_live_class(request):
    """View to schedule a new live virtual class."""
    role = getattr(request.user.profile, 'role', 'student') if hasattr(request.user, 'profile') else 'student'
    is_admin = request.user.is_staff or request.user.is_superuser or role == 'admin'
    
    if not (is_admin or role == 'tutor'):
        raise PermissionDenied("Only tutors and administrators can create live classes.")
        
    if request.method == 'POST':
        form = LiveClassForm(request.POST)
        if form.is_valid():
            live_class = form.save(commit=False)
            
            # Verify tutor owns/manages course
            if not (is_admin or live_class.course.can_be_managed_by(request.user)):
                form.add_error('course', "You do not manage this course.")
            else:
                live_class.save()
                messages.success(request, f"Live class '{live_class.title}' scheduled successfully.")
                
                # Send notifications
                try:
                    from notifications.services import create_notification, notify_guardian_of_ward_event
                    # Notify enrolled students
                    enrollments = Enrollment.objects.filter(course=live_class.course, status='active')
                    for enrollment in enrollments:
                        create_notification(
                            recipient=enrollment.student,
                            title="New Live Class Scheduled",
                            message=f"A new live class '{live_class.title}' has been scheduled for {live_class.course.title} on {live_class.scheduled_start.strftime('%Y-%m-%d %H:%M')}.",
                            notification_type="system",
                            delivery_channel="both",
                            related_course=live_class.course
                        )
                        # Notify guardian
                        notify_guardian_of_ward_event(
                            student=enrollment.student,
                            title="New Live Class Scheduled",
                            message=f"A new live class '{live_class.title}' has been scheduled for your ward's course {live_class.course.title}.",
                            notification_type="system",
                            related_course=live_class.course
                        )
                    # Notify assigned tutor
                    create_notification(
                        recipient=live_class.tutor,
                        title="Live Class Scheduled",
                        message=f"You scheduled a live class '{live_class.title}' for {live_class.course.title}.",
                        notification_type="system",
                        delivery_channel="in_app",
                        related_course=live_class.course
                    )
                except ImportError:
                    pass
                    
                return redirect('academics:live_class_list')
    else:
        # Prepopulate tutor and restrict course choices for tutors
        initial = {'tutor': request.user}
        form = LiveClassForm(initial=initial)
        if not is_admin:
            managed_courses = Course.objects.filter(Q(created_by=request.user) | Q(assigned_tutors=request.user)).distinct()
            form.fields['course'].queryset = managed_courses
            form.fields['tutor'].queryset = User.objects.filter(id=request.user.id)
            
    context = {
        'form': form,
        'title': "Schedule Live Class",
    }
    return render(request, 'academics/live_class_form.html', context)


@login_required
def edit_live_class(request, live_class_id):
    """Enables editing details of an existing scheduled live class."""
    live_class = get_object_or_404(LiveClass, id=live_class_id)
    user = request.user
    role = getattr(user.profile, 'role', 'student') if hasattr(user, 'profile') else 'student'
    is_admin = user.is_staff or user.is_superuser or role == 'admin'
    
    # Permission check: tutor owns course or scheduled the live class
    if not (is_admin or live_class.tutor == user or live_class.course.can_be_managed_by(user)):
        raise PermissionDenied("You do not have permission to edit this live class.")
        
    old_status = live_class.status
    if request.method == 'POST':
        form = LiveClassForm(request.POST, instance=live_class)
        if form.is_valid():
            updated_class = form.save()
            messages.success(request, "Live class details updated successfully.")
            
            # Cancel notification hook
            if old_status != 'cancelled' and updated_class.status == 'cancelled':
                try:
                    from notifications.services import create_notification, notify_guardian_of_ward_event
                    enrollments = Enrollment.objects.filter(course=updated_class.course, status='active')
                    for enrollment in enrollments:
                        create_notification(
                            recipient=enrollment.student,
                            title="Live Class Cancelled",
                            message=f"The live class '{updated_class.title}' for {updated_class.course.title} has been cancelled.",
                            notification_type="system",
                            delivery_channel="both",
                            related_course=updated_class.course
                        )
                        notify_guardian_of_ward_event(
                            student=enrollment.student,
                            title="Live Class Cancelled",
                            message=f"The live class '{updated_class.title}' for your ward's course {updated_class.course.title} has been cancelled.",
                            notification_type="system",
                            related_course=updated_class.course
                        )
                except ImportError:
                    pass
                    
            return redirect('academics:live_class_detail', live_class_id=updated_class.id)
    else:
        form = LiveClassForm(instance=live_class)
        if not is_admin:
            managed_courses = Course.objects.filter(Q(created_by=user) | Q(assigned_tutors=user)).distinct()
            form.fields['course'].queryset = managed_courses
            
    context = {
        'form': form,
        'live_class': live_class,
        'title': "Edit Live Class",
    }
    return render(request, 'academics/live_class_form.html', context)


@login_required
def tutor_attendance_dashboard(request):
    """Renders attendance overview for courses managed by the logged-in tutor."""
    role = getattr(request.user.profile, 'role', 'student') if hasattr(request.user, 'profile') else 'student'
    is_admin = request.user.is_staff or request.user.is_superuser or role == 'admin'
    
    if not (is_admin or role == 'tutor'):
        raise PermissionDenied("Only tutors and administrators can access the attendance dashboard.")
        
    if is_admin:
        courses = Course.objects.all()
    else:
        courses = Course.objects.filter(Q(created_by=request.user) | Q(assigned_tutors=request.user)).distinct()
        
    recent_sessions = AttendanceSession.objects.filter(course__in=courses).order_by('-date')
    
    # Pending marking is defined as sessions with 0 records marked
    pending_sessions = [s for s in recent_sessions if s.records.count() == 0]
    
    context = {
        'courses': courses,
        'recent_sessions': recent_sessions,
        'pending_sessions': pending_sessions,
        'is_admin': is_admin,
    }
    return render(request, 'academics/tutor_attendance_dashboard.html', context)


@login_required
def create_attendance_session(request, course_slug):
    """Creates a roll-call attendance session for a specific course."""
    course = get_object_or_404(Course, slug=course_slug)
    user = request.user
    role = getattr(user.profile, 'role', 'student') if hasattr(user, 'profile') else 'student'
    is_admin = user.is_staff or user.is_superuser or role == 'admin'
    
    if not (is_admin or course.can_be_managed_by(user)):
        raise PermissionDenied("You do not have permission to manage attendance for this course.")
        
    if request.method == 'POST':
        form = AttendanceSessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.course = course
            session.created_by = user
            session.save()
            
            # Prepare records for active enrolled students
            enrollments = Enrollment.objects.filter(course=course, status='active')
            for enrollment in enrollments:
                AttendanceRecord.objects.get_or_create(
                    attendance_session=session,
                    student=enrollment.student,
                    defaults={'status': 'present'}
                )
                
            messages.success(request, f"Attendance session '{session.title}' created. Ready to mark roll.")
            return redirect('academics:mark_attendance', attendance_session_id=session.id)
    else:
        initial = {
            'course': course,
            'date': timezone.now().date(),
            'title': f"Roll Call — {timezone.now().strftime('%Y-%m-%d')}"
        }
        form = AttendanceSessionForm(initial=initial)
        form.fields['course'].queryset = Course.objects.filter(id=course.id)
        # Filter live classes and slots to only the matching course
        form.fields['live_class'].queryset = LiveClass.objects.filter(course=course)
        form.fields['timetable_slot'].queryset = TimetableSlot.objects.filter(course=course)
        
    context = {
        'form': form,
        'course': course,
    }
    return render(request, 'academics/create_attendance_session.html', context)


@login_required
def mark_attendance(request, attendance_session_id):
    """Enables tutors to set attendance status (present, late, absent, excused) for learners."""
    session = get_object_or_404(AttendanceSession, id=attendance_session_id)
    user = request.user
    role = getattr(user.profile, 'role', 'student') if hasattr(user, 'profile') else 'student'
    is_admin = user.is_staff or user.is_superuser or role == 'admin'
    
    if not (is_admin or session.course.can_be_managed_by(user)):
        raise PermissionDenied("You do not manage the course linked to this session.")
        
    records = session.records.select_related('student').order_by('student__username')
    
    if request.method == 'POST':
        for record in records:
            status_field = f"status_{record.id}"
            notes_field = f"notes_{record.id}"
            if status_field in request.POST:
                new_status = request.POST[status_field]
                old_status = record.status
                record.status = new_status
                record.notes = request.POST.get(notes_field, '')
                record.marked_by = user
                record.marked_at = timezone.now()
                record.save()
                
                # Check for student absence notifications
                if new_status == 'absent' and old_status != 'absent':
                    try:
                        from notifications.services import create_notification, notify_guardian_of_ward_event
                        # Notify Student
                        create_notification(
                            recipient=record.student,
                            title="Absent Notification",
                            message=f"You have been marked absent for {session.course.title} on {session.date}.",
                            notification_type="system",
                            delivery_channel="both",
                            related_course=session.course
                        )
                        # Notify Guardian
                        notify_guardian_of_ward_event(
                            student=record.student,
                            title="Ward Absent Notification",
                            message=f"Your ward {record.student.get_full_name() or record.student.username} was marked absent for {session.course.title} on {session.date}.",
                            notification_type="system",
                            related_course=session.course
                        )
                    except ImportError:
                        pass
                        
        messages.success(request, "Attendance sheet updated and notifications dispatched successfully.")
        return redirect('academics:tutor_attendance_dashboard')
        
    context = {
        'session': session,
        'records': records,
    }
    return render(request, 'academics/mark_attendance.html', context)


@login_required
def my_attendance(request):
    """Displays overall and course-by-course attendance summary statistics for students."""
    role = getattr(request.user.profile, 'role', 'student') if hasattr(request.user, 'profile') else 'student'
    if role != 'student':
        return HttpResponseForbidden("This view is for students only.")
        
    records = AttendanceRecord.objects.filter(student=request.user).select_related('attendance_session__course').order_by('-attendance_session__date')
    
    course_attendance = {}
    for r in records:
        c = r.attendance_session.course
        if c not in course_attendance:
            course_attendance[c] = []
        course_attendance[c].append(r)
        
    course_summaries = []
    for course, recs in course_attendance.items():
        pct = calculate_student_attendance_percentage(request.user, course)
        course_summaries.append({
            'course': course,
            'records': recs,
            'percentage': pct
        })
        
    overall_percentage = calculate_student_attendance_percentage(request.user)
    
    context = {
        'course_summaries': course_summaries,
        'overall_percentage': overall_percentage,
    }
    return render(request, 'academics/my_attendance.html', context)


@login_required
def ward_attendance(request, student_id):
    """Enables guardians to view ward attendance analytics and logs."""
    student = get_object_or_404(User, id=student_id)
    user = request.user
    role = getattr(user.profile, 'role', 'student') if hasattr(user, 'profile') else 'student'
    is_admin = user.is_staff or user.is_superuser or role == 'admin'
    
    # Permission verification
    is_ward = user.wards.filter(user=student).exists()
    if not (is_admin or is_ward):
        raise PermissionDenied("You are not authorized to view this student's attendance records.")
        
    records = AttendanceRecord.objects.filter(student=student).select_related('attendance_session__course').order_by('-attendance_session__date')
    
    course_attendance = {}
    for r in records:
        c = r.attendance_session.course
        if c not in course_attendance:
            course_attendance[c] = []
        course_attendance[c].append(r)
        
    course_summaries = []
    for course, recs in course_attendance.items():
        pct = calculate_student_attendance_percentage(student, course)
        course_summaries.append({
            'course': course,
            'records': recs,
            'percentage': pct
        })
        
    overall_percentage = calculate_student_attendance_percentage(student)
    
    context = {
        'student': student,
        'course_summaries': course_summaries,
        'overall_percentage': overall_percentage,
    }
    return render(request, 'academics/ward_attendance.html', context)


@login_required
def academic_admin_dashboard(request):
    """Renders high-level academic administrative metrics and calendars for school staff."""
    role = getattr(request.user.profile, 'role', 'student') if hasattr(request.user, 'profile') else 'student'
    is_admin = request.user.is_staff or request.user.is_superuser or role == 'admin'
    
    if not is_admin:
        raise PermissionDenied("Only administrators and staff can access the Academic Admin Dashboard.")
        
    today = timezone.now().date()
    current_session = get_current_academic_session()
    current_term = get_current_academic_term()
    
    total_slots = TimetableSlot.objects.count()
    live_classes_today = LiveClass.objects.filter(scheduled_start__date=today).count()
    attendance_sessions_today = AttendanceSession.objects.filter(date=today).count()
    
    absent_records_today = AttendanceRecord.objects.filter(
        attendance_session__date=today,
        status='absent'
    ).select_related('student', 'attendance_session__course')
    
    upcoming_weeks = AcademicWeek.objects.filter(
        week_type__in=['test', 'exam'],
        end_date__gte=today
    ).order_by('start_date')
    
    context = {
        'current_session': current_session,
        'current_term': current_term,
        'total_slots': total_slots,
        'live_classes_today': live_classes_today,
        'attendance_sessions_today': attendance_sessions_today,
        'absent_records_today': absent_records_today,
        'upcoming_weeks': upcoming_weeks,
    }
    return render(request, 'academics/academic_admin_dashboard.html', context)
