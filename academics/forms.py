from django import forms
from .models import TimetableSlot, LiveClass, AttendanceSession, AttendanceRecord


class TimetableSlotForm(forms.ModelForm):
    class Meta:
        model = TimetableSlot
        fields = [
            'class_level',
            'subject',
            'course',
            'tutor',
            'day_of_week',
            'start_time',
            'end_time',
            'title',
            'slot_type',
            'room',
            'is_active'
        ]
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'class_level': forms.Select(attrs={'class': 'form-control'}),
            'subject': forms.Select(attrs={'class': 'form-control'}),
            'course': forms.Select(attrs={'class': 'form-control'}),
            'tutor': forms.Select(attrs={'class': 'form-control'}),
            'day_of_week': forms.Select(attrs={'class': 'form-control'}),
            'slot_type': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'room': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }


class LiveClassForm(forms.ModelForm):
    class Meta:
        model = LiveClass
        fields = [
            'course',
            'module',
            'lesson',
            'timetable_slot',
            'tutor',
            'title',
            'description',
            'scheduled_start',
            'scheduled_end',
            'provider',
            'meeting_link',
            'meeting_id',
            'passcode',
            'status',
            'recording_url',
            'is_published'
        ]
        widgets = {
            'scheduled_start': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'scheduled_end': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'course': forms.Select(attrs={'class': 'form-control'}),
            'module': forms.Select(attrs={'class': 'form-control'}),
            'lesson': forms.Select(attrs={'class': 'form-control'}),
            'timetable_slot': forms.Select(attrs={'class': 'form-control'}),
            'tutor': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'provider': forms.Select(attrs={'class': 'form-control'}),
            'meeting_link': forms.URLInput(attrs={'class': 'form-control'}),
            'meeting_id': forms.TextInput(attrs={'class': 'form-control'}),
            'passcode': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'recording_url': forms.URLInput(attrs={'class': 'form-control'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }


class AttendanceSessionForm(forms.ModelForm):
    class Meta:
        model = AttendanceSession
        fields = [
            'course',
            'live_class',
            'timetable_slot',
            'title',
            'date',
            'start_time',
            'end_time'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'course': forms.Select(attrs={'class': 'form-control'}),
            'live_class': forms.Select(attrs={'class': 'form-control'}),
            'timetable_slot': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'})
        }


class AttendanceRecordForm(forms.ModelForm):
    class Meta:
        model = AttendanceRecord
        fields = ['status', 'notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
        }
