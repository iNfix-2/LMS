from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, Http404, HttpResponseForbidden
from accounts.decorators import is_tutor_user, is_admin_user
from .models import Badge, StudentAchievement, Certificate
from courses.models import Course

@login_required
def my_achievements(request):
    user = request.user
    
    # Get achievements and certificates for the logged-in student
    achievements = StudentAchievement.objects.filter(student=user).select_related('badge', 'course')
    certificates = Certificate.objects.filter(student=user).select_related('course')
    
    # Get all possible badges to show what the student could earn (gamification!)
    all_badges = Badge.objects.all()
    earned_badge_ids = achievements.values_list('badge_id', flat=True)
    
    for b in all_badges:
        b.is_earned = b.id in earned_badge_ids

    context = {
        'achievements': achievements,
        'certificates': certificates,
        'all_badges': all_badges,
    }
    return render(request, 'achievements/my_achievements.html', context)

@login_required
def download_certificate(request, cert_id):
    certificate = get_object_or_404(Certificate, id=cert_id)
    user = request.user
    
    # Check permission (owner or tutor/admin)
    is_authorized = (certificate.student == user) or is_admin_user(user) or is_tutor_user(user)
    if not is_authorized:
        messages.error(request, "You do not have permission to download this certificate.")
        return redirect('achievements:my_achievements')
        
    if not certificate.pdf_file:
        # Re-generate it if missing
        from achievements.services import check_and_award_course_completion
        check_and_award_course_completion(certificate.student, certificate.course)
        # Re-fetch certificate
        certificate = get_object_or_404(Certificate, id=cert_id)
        if not certificate.pdf_file:
            messages.error(request, "Certificate PDF file is missing or failed to generate.")
            return redirect('achievements:my_achievements')

    try:
        response = FileResponse(certificate.pdf_file.open('rb'), as_attachment=True)
        return response
    except FileNotFoundError:
        raise Http404("The certificate PDF was not found on the server.")

def verify_certificate(request):
    query = request.GET.get('q', '').strip()
    certificate = None
    searched = False
    
    if query:
        searched = True
        certificate = Certificate.objects.filter(
            certificate_number__iexact=query
        ) | Certificate.objects.filter(
            verification_code__iexact=query
        )
        certificate = certificate.select_related('student', 'course').first()
        
    return render(request, 'achievements/verify_certificate.html', {
        'certificate': certificate,
        'query': query,
        'searched': searched,
    })
