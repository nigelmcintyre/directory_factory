from django import forms
from .models import SaunaSubmission
from .niche_config import FILTERS


# Extract choices from niche_config
COUNTIES = [(county, county) for county in next((f["choices"] for f in FILTERS if f["key"] == "county"), [])]
HEAT_SOURCE_CHOICES = [(choice, choice) for choice in next((f["choices"] for f in FILTERS if f["key"] == "heat_source"), [])]
YES_NO_CHOICES = [
    ('yes', 'Yes'),
    ('no', 'No'),
    ('not listed', 'Not Listed'),
]


class SaunaSubmissionForm(forms.ModelForm):
    class Meta:
        model = SaunaSubmission
        fields = [
            'name', 'city', 'county', 'address', 'website', 'phone',
            'description', 'heat_source', 'cold_plunge', 'dog_friendly',
            'showers', 'changing_facilities', 'sea_view', 'opening_hours',
            'submitter_name', 'submitter_email'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'e.g., The Barrel Sauna'
            }),
            'city': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'e.g., Dublin'
            }),
            'county': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
            }),
            'address': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'Full address (optional)'
            }),
            'website': forms.URLInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'https://example.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': '+353 1 234 5678'
            }),
            'description': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'rows': 4,
                'placeholder': 'Tell us about this sauna - what makes it special, what amenities it has, etc.'
            }),
            'heat_source': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
            }),
            'cold_plunge': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
            }),
            'dog_friendly': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
            }),
            'showers': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
            }),
            'changing_facilities': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
            }),
            'sea_view': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
            }),
            'opening_hours': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'e.g., Monday-Friday: 9am-6pm, Saturday: 10am-4pm'
            }),
            'submitter_name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'Your name (optional)'
            }),
            'submitter_email': forms.EmailInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'your.email@example.com'
            }),
        }
        labels = {
            'name': 'Sauna Name *',
            'city': 'City *',
            'county': 'County *',
            'address': 'Address',
            'website': 'Website',
            'phone': 'Phone Number',
            'description': 'Description',
            'heat_source': 'Heat Source *',
            'cold_plunge': 'Cold Plunge Available?',
            'dog_friendly': 'Dog Friendly?',
            'showers': 'Showers Available?',
            'changing_facilities': 'Changing Facilities?',
            'sea_view': 'Sea View?',
            'opening_hours': 'Opening Hours',
            'submitter_name': 'Your Name',
            'submitter_email': 'Your Email *',
        }
        help_texts = {
            'description': 'Tell us what makes this sauna special',
            'opening_hours': 'If you know the opening hours, please share them',
            'submitter_email': 'We\'ll only use this to contact you about this submission',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set choices for dropdown fields
        self.fields['county'].choices = [('', 'Select County')] + COUNTIES
        self.fields['heat_source'].choices = [('', 'Select Heat Source')] + HEAT_SOURCE_CHOICES
        self.fields['cold_plunge'].choices = [('', 'Select Option')] + YES_NO_CHOICES
        self.fields['dog_friendly'].choices = [('', 'Select Option')] + YES_NO_CHOICES
        self.fields['showers'].choices = [('', 'Select Option')] + YES_NO_CHOICES
        self.fields['changing_facilities'].choices = [('', 'Select Option')] + YES_NO_CHOICES
        self.fields['sea_view'].choices = [('', 'Select Option')] + YES_NO_CHOICES
        
        # Set required fields
        self.fields['name'].required = True
        self.fields['city'].required = True
        self.fields['county'].required = True
        self.fields['heat_source'].required = True
        self.fields['submitter_email'].required = True
