from django import forms
from django.contrib.auth.forms import UserCreationForm
from account.models import Account
from django.contrib.auth import authenticate
from account.utils import extract_name


class RegistrationForm(UserCreationForm):

    email = forms.EmailField(max_length=255,help_text='Enter a Valid Email.')
     # Add gender field to the form
    gender = forms.ChoiceField(
        choices=Account.GENDER_CHOICES,
        widget=forms.RadioSelect,
        initial='M',  # Set an initial value
        label='Gender'
    )

     # Add "Terms and Conditions" field to the form
    terms = forms.BooleanField(
        required=True,
        label='I accept the Terms and Conditions',
        initial=True # Set the initial value as needed
    )

    class Meta:
        model = Account
        fields = ('email', 'password1','password2','gender', 'terms')

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        college_email = email.split('.')[-1:]
        if not (college_email == ['edu']):
            college_email = email.split('.')[-2:]
            if not (college_email == ['edu', 'in'] or college_email == ['ac', 'in']):
                raise forms.ValidationError(f'Email must ends with either .edu or .edu.in or .ac.in')
        # college_email = email.split('.')[-2:]
        # if not (college_email == ['edu', 'in']):
        #     raise forms.ValidationError(f'Email must ends with .edu.in')
        try:
            account = Account.objects.get(email=email)
        except Account.DoesNotExist:
            return email
        raise forms.ValidationError(f'Email - {email} is already in use.')

       
    def save(self, commit=True):
        account = super(RegistrationForm, self).save(commit=False)
        email = self.cleaned_data['email'].lower()
        name = extract_name(email)
        
        # if '.' in name:
        #     name = name.split('.')[0].capitalize()
        account.name = name
        account.terms = self.cleaned_data['terms']
        account.email = self.cleaned_data['email'].lower()
        account.university_name = email.split('@')[-1:][0]
        if commit:
            account.save()
        return account

class AccountAuthenticationForm(forms.ModelForm):
    email = forms.EmailField(max_length=255,label='Email')
    password = forms.CharField(label='Password', widget=forms.PasswordInput)


    class Meta:
        model = Account
        fields = ('email', 'password')

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        college_email = email.split('.')[-1:]
        if not (college_email == ['edu']):
            college_email = email.split('.')[-2:]
            if not (college_email == ['edu', 'in'] or college_email == ['ac', 'in']):
                raise forms.ValidationError(f'Email must ends with either .edu or .edu.in or .ac.in')
        # email = self.cleaned_data['email'].lower()
        # college_email = email.split('.')[-2:]
        # if not (college_email == ['edu', 'in']):
        #     raise forms.ValidationError(f'Email must ends with .edu.in')
        try:
            account = Account.objects.get(email=email)
            return email
        except Account.DoesNotExist:
            raise forms.ValidationError(f'Account with Email - {email} - does not exist!')

    def clean(self):
        if self.is_valid():
            email = self.cleaned_data['email']
            password = self.cleaned_data['password']
            if not authenticate(email=email,password=password):
                raise forms.ValidationError("Invalid Credentials!")
            


