from django import forms
from .models import Resource
from courses.models import Course

class ResourceForm(forms.ModelForm):
    class Meta:
        model = Resource
        fields = ['title', 'description', 'file', 'resource_type', 'course', 'is_free']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Resource Title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional description...'}),
            'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'resource_type': forms.Select(attrs={'class': 'form-select'}),
            'course': forms.Select(attrs={'class': 'form-select'}),
            'is_free': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            # Only show courses where the user is an assigned tutor (or admin)
            if user.is_staff or user.is_superuser:
                self.fields['course'].queryset = Course.objects.all()
            else:
                self.fields['course'].queryset = Course.objects.filter(assigned_tutors=user)
            self.fields['course'].empty_label = "General Resource (No Course)"
            self.fields['course'].required = False
