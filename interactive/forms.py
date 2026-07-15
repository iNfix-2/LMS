from django import forms
from .models import InteractiveContent

class InteractiveContentForm(forms.ModelForm):
    class Meta:
        model = InteractiveContent
        fields = ['content_type', 'package_file', 'embed_url']
        widgets = {
            'content_type': forms.Select(attrs={'class': 'form-select'}),
            'package_file': forms.FileInput(attrs={'class': 'form-control'}),
            'embed_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://h5p.org/h5p/embed/...'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        content_type = cleaned_data.get('content_type')
        package_file = cleaned_data.get('package_file')
        embed_url = cleaned_data.get('embed_url')

        if content_type in ['scorm', 'h5p'] and not package_file:
            self.add_error('package_file', 'Please upload a ZIP file package for SCORM/H5P.')
        elif content_type == 'h5p_embed' and not embed_url:
            self.add_error('embed_url', 'Please specify the H5P embed URL.')
        return cleaned_data
