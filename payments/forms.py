from django import forms
from django.contrib.auth.models import User
from courses.models import Course
from payments.models import PricingPlan

class ManualAccessGrantForm(forms.Form):
    student = forms.ModelChoiceField(
        queryset=User.objects.all().order_by('username'),
        label="Student",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    course = forms.ModelChoiceField(
        queryset=Course.objects.all().order_by('title'),
        label="Course",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    duration_days = forms.IntegerField(
        initial=90,
        required=False,
        label="Duration (Days)",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Leave blank for lifetime access'})
    )
    amount = forms.DecimalField(
        required=False,
        max_digits=12,
        decimal_places=2,
        label="Amount Paid (optional, creates manual invoice/payment record)",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Reason for manual grant'})
    )



class ManualPaymentForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=User.objects.all().order_by('username'),
        label="User / Student",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    course = forms.ModelChoiceField(
        queryset=Course.objects.all().order_by('title'),
        required=False,
        label="Course (optional if plan selected)",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    plan = forms.ModelChoiceField(
        queryset=PricingPlan.objects.all().order_by('name'),
        required=False,
        label="Pricing Plan (optional if course selected)",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        label="Amount Paid",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Reference number, receipt details, etc.'})
    )

    def clean(self):
        cleaned_data = super().clean()
        course = cleaned_data.get("course")
        plan = cleaned_data.get("plan")
        if not course and not plan:
            raise forms.ValidationError("You must select either a Course or a Pricing Plan.")
        if course and plan:
            raise forms.ValidationError("Please select either a Course or a Pricing Plan, not both.")
        return cleaned_data
