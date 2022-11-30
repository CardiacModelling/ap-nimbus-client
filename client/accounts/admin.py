import csv

import magic
from django import forms
from django.contrib import admin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.contrib.auth.hashers import make_password
from django.core.files.uploadedfile import TemporaryUploadedFile

from .models import User


class UserForm(forms.ModelForm):
    """A form for creating/updating users. Includes all the fields on
    the user, but replaces the password field with admin's
    password hash display field and adds password 1 andpassword2 for setting a new password.
    """
    password = ReadOnlyPasswordHashField()
    password1 = forms.CharField(label='New password', widget=forms.PasswordInput, required=False)
    password2 = forms.CharField(label='New password confirmation', widget=forms.PasswordInput, required=False)
    tsv = forms.FileField(label='Bulk upload user accounts (TSV: email password)', required=False)

    class Meta:
        model = User
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tsv'].widget.attrs = {'accept': ('.txt,.tsv')}
        if self.initial:
            self.fields['tsv'].widget = self.fields['tsv'].hidden_widget()
        self.fields['email'].required = False
        self.fields['full_name'].required = False
        self.fields['date_joined'].required = False

    def clean(self):
        cleaned_data = super().clean()
        users = []
        if self.cleaned_data.get('tsv', None) and isinstance(self.cleaned_data['tsv'], TemporaryUploadedFile):
            tsv = self.cleaned_data['tsv']
            # check mime type of any uploaded file
            mime_type = str(magic.from_buffer(tsv.file.read(), mime=True))
            if mime_type not in ['text/plain', 'text/tsv']:
                raise forms.ValidationError(
                    'Invalid TSV file. Unsupported file type, expecting a (UTF-8 text-based) TSV file.'
                )
            with open(tsv.temporary_file_path()) as file:
                tsv_file = tuple(csv.reader(file, delimiter="\t"))
                for line in tsv_file:
                    email = None
                    for i, col in enumerate(line):
                        if email and col != '':
                            institution = email.split('@')[-1]
                            if institution in ('gmail.com', 'yahoo.com', 'hotmail.com'):
                                institution = ''
                            if not User.objects.filter(email=email).exists():
                                users.append((email, email.split('@')[0], institution, col))
                            break
                        if '@' in col:
                            email = col
            if not users:
                raise forms.ValidationError('TSV file did not contain (new) user accounts.')
            user = users.pop()
            self.cleaned_data['email'] = user[0]
            self.cleaned_data['full_name'] = user[1]
            self.cleaned_data['institution'] = user[2]
            self.cleaned_data['password'] = make_password(user[3])
            for user in users:
                User.objects.create(email=user[0],
                                    full_name=user[1],
                                    institution=user[2],
                                    password=make_password(user[3]))

        elif not all((self.cleaned_data.get('email', None),
                      self.cleaned_data.get('full_name', None),
                      self.cleaned_data.get('date_joined', None))):
            raise forms.ValidationError("Email, Full Name and Date Joined are required!")
        elif not any((self.cleaned_data.get('password1', None),
                      self.cleaned_data.get('password2', None),
                      self.initial.get('password', None))):
            raise forms.ValidationError("Password is required!")
        elif not self.cleaned_data.get('password1', None) and not self.cleaned_data.get('password2', None):
            cleaned_data['password'] = self.initial['password']
        elif self.cleaned_data.get('password1', None) != self.cleaned_data.get('password2', False):
            raise forms.ValidationError("Passwords don't match")
        else:
            cleaned_data['password'] = make_password(self.cleaned_data['password1'])
        return cleaned_data


class UserAdmin(admin.ModelAdmin):
    form = UserForm
    add_form = UserForm


# Now register the new UserAdmin...
admin.site.register(User, UserAdmin)
