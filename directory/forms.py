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

SELECT_INPUT_CLASSES = (
    'mt-1 block w-full rounded-md border-gray-300 shadow-sm '
    'focus:border-blue-500 focus:ring-blue-500 bg-white text-gray-900 '
    'appearance-auto cursor-pointer relative z-10'
)

SELECT_INPUT_STYLE = '-webkit-appearance: menulist; appearance: auto;'


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
                'class': SELECT_INPUT_CLASSES,
                'style': SELECT_INPUT_STYLE,
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
                'class': SELECT_INPUT_CLASSES,
                'style': SELECT_INPUT_STYLE,
            }),
            'cold_plunge': forms.Select(attrs={
                'class': SELECT_INPUT_CLASSES,
                'style': SELECT_INPUT_STYLE,
            }),
            'dog_friendly': forms.Select(attrs={
                'class': SELECT_INPUT_CLASSES,
                'style': SELECT_INPUT_STYLE,
            }),
            'showers': forms.Select(attrs={
                'class': SELECT_INPUT_CLASSES,
                'style': SELECT_INPUT_STYLE,
            }),
            'changing_facilities': forms.Select(attrs={
                'class': SELECT_INPUT_CLASSES,
                'style': SELECT_INPUT_STYLE,
            }),
            'sea_view': forms.Select(attrs={
                'class': SELECT_INPUT_CLASSES,
                'style': SELECT_INPUT_STYLE,
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

        def set_dropdown_choices(field_name, placeholder, choices):
            # These are model CharFields rendered with Select widgets.
            # The options must be attached to the widget to render <option> tags.
            all_choices = [('', placeholder)] + choices
            self.fields[field_name].widget.choices = all_choices
            self.fields[field_name].choices = all_choices
        
        # Set choices for dropdown fields
        set_dropdown_choices('county', 'Select County', COUNTIES)
        set_dropdown_choices('heat_source', 'Select Heat Source', HEAT_SOURCE_CHOICES)
        set_dropdown_choices('cold_plunge', 'Select Option', YES_NO_CHOICES)
        set_dropdown_choices('dog_friendly', 'Select Option', YES_NO_CHOICES)
        set_dropdown_choices('showers', 'Select Option', YES_NO_CHOICES)
        set_dropdown_choices('changing_facilities', 'Select Option', YES_NO_CHOICES)
        set_dropdown_choices('sea_view', 'Select Option', YES_NO_CHOICES)
        
        # Set required fields
        self.fields['name'].required = True
        self.fields['city'].required = True
        self.fields['county'].required = True
        self.fields['heat_source'].required = True
        self.fields['submitter_email'].required = True


class PartnerInquiryForm(forms.Form):
    """Form for contacting about featured listing / partner programs"""
    
    sauna_name = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'placeholder': 'Your Sauna Name'
        })
    )
    contact_name = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'placeholder': 'Your Name'
        })
    )
    contact_email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'placeholder': 'your@email.com'
        })
    )
    phone = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'placeholder': '+353 1 234 5678'
        })
    )
    tier_interest = forms.ChoiceField(
        required=True,
        choices=[
            ('tier1', 'Tier 1: Featured Listing + Booking Link (€39/month)'),
            ('tier2_existing', 'Tier 2A: Featured + Embedded Booking (Bring your existing booking platform) (€49/month + €350 setup)'),
            ('tier2_managed', 'Tier 2B: Featured + Embedded Booking (We set you up on SimplyBook.me) (€49/month + €350 setup)'),
            ('all', 'Tell me more about all options'),
        ],
        widget=forms.RadioSelect(attrs={
            'class': 'mt-2'
        })
    )
    message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'placeholder': 'Tell us about your booking situation (optional)...',
            'rows': 4
        })
    )
