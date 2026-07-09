from django.core.management.base import BaseCommand
from django.utils import timezone
from academics.models import AcademicSession, AcademicTerm, AcademicWeek
import datetime

class Command(BaseCommand):
    help = 'Seeds default primary academic calendar data (Session, Terms, Weeks)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Seeding academic calendar data..."))

        # 1. Create or retrieve Academic Session
        session_name = "2025/2026 Academic Session"
        session, created = AcademicSession.objects.get_or_create(
            name=session_name,
            defaults={
                'start_date': datetime.date(2025, 9, 1),
                'end_date': datetime.date(2026, 7, 31),
                'is_current': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created Session: {session_name}"))
        else:
            self.stdout.write(f"Session already exists: {session_name}")

        # 2. Create Terms
        terms_data = [
            {
                'name': 'First Term',
                'term_number': 1,
                'start_date': datetime.date(2025, 9, 1),
                'end_date': datetime.date(2025, 12, 15),
                'is_current': False
            },
            {
                'name': 'Second Term',
                'term_number': 2,
                'start_date': datetime.date(2026, 1, 5),
                'end_date': datetime.date(2026, 4, 10),
                'is_current': False
            },
            {
                'name': 'Third Term',
                'term_number': 3,
                'start_date': datetime.date(2026, 4, 27),
                'end_date': datetime.date(2026, 7, 24),
                'is_current': True
            }
        ]

        term_objects = {}
        for t_data in terms_data:
            term, t_created = AcademicTerm.objects.get_or_create(
                session=session,
                term_number=t_data['term_number'],
                defaults={
                    'name': t_data['name'],
                    'start_date': t_data['start_date'],
                    'end_date': t_data['end_date'],
                    'is_current': t_data['is_current']
                }
            )
            term_objects[term.term_number] = term
            if t_created:
                self.stdout.write(self.style.SUCCESS(f"Created Term: {term.name}"))
            else:
                self.stdout.write(f"Term already exists: {term.name}")

        # 3. Create Weeks for Third Term (Current Term)
        current_term = term_objects.get(3)
        if current_term:
            self.stdout.write("Generating weeks for Third Term...")
            week_activities = [
                ('normal', 'Introduction and Setup'),
                ('normal', 'Core Concepts Review'),
                ('normal', 'Advanced Topics and Modules'),
                ('normal', 'Mid-Term Assignments Prep'),
                ('normal', 'Mid-Term Project Work'),
                ('break', 'Mid-Term Revision & Break'),
                ('normal', 'Interactive Practical Workshops'),
                ('normal', 'Guest Lectures & Lab Session'),
                ('normal', 'Final Assessment Prep'),
                ('revision', 'Revision Week'),
                ('exam', 'Term Examinations'),
                ('report', 'Report Cards and Wrap-up'),
            ]

            start_base = current_term.start_date
            for idx, (week_type, activity) in enumerate(week_activities, start=1):
                week_start = start_base + datetime.timedelta(weeks=idx-1)
                week_end = week_start + datetime.timedelta(days=4)  # Weekday span (Mon-Fri)
                
                week, w_created = AcademicWeek.objects.get_or_create(
                    term=current_term,
                    week_number=idx,
                    defaults={
                        'start_date': week_start,
                        'end_date': week_end,
                        'activity': activity,
                        'description': f"Activities and schedules for academic week {idx}.",
                        'week_type': week_type
                    }
                )
                if w_created:
                    self.stdout.write(self.style.SUCCESS(f"Created Week {idx}: {activity} ({week_start} to {week_end})"))

        self.stdout.write(self.style.SUCCESS("Academic calendar seeding completed successfully."))
