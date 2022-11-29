from django import forms
from django.contrib import admin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.contrib.auth.hashers import make_password

from .models import User


class UserForm(forms.ModelForm):
    """A form for creating/updating users. Includes all the fields on
    the user, but replaces the password field with admin's
    password hash display field and adds password 1 andpassword2 for setting a new password.
    """
    password = ReadOnlyPasswordHashField()
    password1 = forms.CharField(label='New password', widget=forms.PasswordInput, required=False)
    password2 = forms.CharField(label='New password confirmation', widget=forms.PasswordInput, required=False)

    class Meta:
        model = User
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        if not self.cleaned_data['password1'] \
                and not self.cleaned_data['password2'] \
                and not self.initial.get('password', None):
            raise forms.ValidationError("Password is required!")
        elif not self.cleaned_data['password1'] and not self.cleaned_data['password2']:
            cleaned_data['password'] = self.initial['password']
        elif self.cleaned_data['password1'] != self.cleaned_data['password2']:
            raise forms.ValidationError("Passwords don't match")
        else:
            cleaned_data['password'] = make_password(self.cleaned_data['password1'])
        return cleaned_data


class UserAdmin(admin.ModelAdmin):
    form = UserForm
    add_form = UserForm


# Now register the new UserAdmin...
admin.site.register(User, UserAdmin)
