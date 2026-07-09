from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from accounts.models import UserProfile
from courses.models import Course, ClassLevel, Subject
from academics.models import TimetableSlot, LiveClass
import datetime

class Command(BaseCommand):
    help = 'Seeds primary academic timetable data (slots and live classes)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Seeding academic timetable data..."))

        # 1. Ensure ClassLevel and Subject exist
        class_level, _ = ClassLevel.objects.get_or_create(
            name="Grade 10"
        )
        subject, _ = Subject.objects.get_or_create(
            name="Mathematics",
            defaults={'description': 'Core Mathematics Subject'}
        )

        # 2. Ensure Tutor exists
        tutor = User.objects.filter(profile__role='tutor').first()
        if not tutor:
            tutor = User.objects.filter(is_superuser=True).first()
        if not tutor:
            tutor, created = User.objects.get_or_create(
                username='tutor_primary',
                defaults={
                    'email': 'tutor_primary@edukom.com',
                    'first_name': 'Primary',
                    'last_name': 'Tutor'
                }
            )
            tutor.set_password('edukom123')
            tutor.save()
            
            # Ensure UserProfile exists
            UserProfile.objects.get_or_create(
                user=tutor,
                defaults={'role': 'tutor'}
            )
            self.stdout.write(self.style.SUCCESS(f"Created default tutor user: {tutor.username}"))

        # 3. Ensure Course exists
        course = Course.objects.filter(subject=subject, class_level=class_level).first()
        if not course:
            course = Course.objects.first()
        if not course:
            course = Course.objects.create(
                title="Introductory Mathematics Grade 10",
                slug="intro-maths-g10",
                description="An introductory course to Grade 10 mathematics.",
                subject=subject,
                class_level=class_level,
                is_published=True,
                created_by=tutor
            )
            self.stdout.write(self.style.SUCCESS(f"Created default Course: {course.title}"))

        # 4. Clear existing timetable slots for this class level to avoid duplicates
        TimetableSlot.objects.filter(class_level=class_level).delete()

        # 5. Create Timetable Slots
        slots_data = [
            # Monday
            {'day': 'Monday', 'start': '09:00:00', 'end': '10:30:00', 'type': 'lesson', 'title': 'Maths Lecture', 'room': 'Room A1'},
            {'day': 'Monday', 'start': '10:30:00', 'end': '11:00:00', 'type': 'break', 'title': 'Morning Recess', 'room': ''},
            {'day': 'Monday', 'start': '11:00:00', 'end': '12:30:00', 'type': 'lesson', 'title': 'Maths Lab', 'room': 'Lab 2'},
            # Tuesday
            {'day': 'Tuesday', 'start': '09:00:00', 'end': '10:30:00', 'type': 'lesson', 'title': 'Maths Practice', 'room': 'Room A1'},
            # Wednesday
            {'day': 'Wednesday', 'start': '09:00:00', 'end': '10:30:00', 'type': 'lesson', 'title': 'Maths Seminar', 'room': 'Seminar Hall'},
            # Thursday
            {'day': 'Thursday', 'start': '09:00:00', 'end': '10:30:00', 'type': 'lesson', 'title': 'Advanced Maths', 'room': 'Room A1'},
            # Friday
            {'day': 'Friday', 'start': '09:00:00', 'end': '10:30:00', 'type': 'lesson', 'title': 'Weekly Revision', 'room': 'Room A1'},
            {'day': 'Friday', 'start': '10:30:00', 'end': '11:00:00', 'type': 'break', 'title': 'Assembly/Fellowship', 'room': 'Main Hall'},
        ]

        created_slots = []
        for s in slots_data:
            slot = TimetableSlot.objects.create(
                class_level=class_level,
                subject=subject if s['type'] == 'lesson' else None,
                course=course if s['type'] == 'lesson' else None,
                tutor=tutor if s['type'] == 'lesson' else None,
                day_of_week=s['day'],
                start_time=datetime.datetime.strptime(s['start'], '%H:%M:%S').time(),
                end_time=datetime.datetime.strptime(s['end'], '%H:%M:%S').time(),
                title=s['title'],
                slot_type=s['type'],
                room=s['room'],
                is_active=True
            )
            created_slots.append(slot)
            self.stdout.write(self.style.SUCCESS(f"Created TimetableSlot: {slot}"))

        # 6. Create Live Classes
        LiveClass.objects.filter(course=course).delete()
        
        now = timezone.now()
        
        # Live Class 1: Completed (yesterday)
        LiveClass.objects.create(
            course=course,
            tutor=tutor,
            title="Algebra Basics Review",
            description="Recap of the fundamental concepts of algebra.",
            scheduled_start=now - datetime.timedelta(days=1, hours=2),
            scheduled_end=now - datetime.timedelta(days=1),
            provider='google_meet',
            meeting_link="https://meet.google.com/abc-defg-hij",
            status='completed',
            is_published=True
        )

        # Live Class 2: Live Now (started 30 mins ago)
        live_slot = next((s for s in created_slots if s.slot_type == 'lesson'), None)
        LiveClass.objects.create(
            course=course,
            timetable_slot=live_slot,
            tutor=tutor,
            title="Linear Equations Live Session",
            description="Solving live equations step-by-step.",
            scheduled_start=now - datetime.timedelta(minutes=30),
            scheduled_end=now + datetime.timedelta(hours=1),
            provider='zoom',
            meeting_link="https://zoom.us/j/1234567890",
            meeting_id="123 456 7890",
            passcode="EDUKOM",
            status='live',
            is_published=True
        )

        # Live Class 3: Scheduled (tomorrow)
        LiveClass.objects.create(
            course=course,
            tutor=tutor,
            title="Quadratic Equations Introduction",
            description="Introducing the quadratic formula and factorization.",
            scheduled_start=now + datetime.timedelta(days=1, hours=3),
            scheduled_end=now + datetime.timedelta(days=1, hours=4, minutes=30),
            provider='zoom',
            meeting_link="https://zoom.us/j/9876543210",
            meeting_id="987 654 3210",
            passcode="MATHS",
            status='scheduled',
            is_published=True
        )

        self.stdout.write(self.style.SUCCESS("Timetable and live classes seeding completed successfully."))
