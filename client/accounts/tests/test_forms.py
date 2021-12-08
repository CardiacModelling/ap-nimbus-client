import pytest
from django.test.client import RequestFactory
from django.urls import reverse

from accounts.models import User
from accounts.forms import RegistrationForm, MyAccountForm



@pytest.fixture
def accounts_request():
 return RequestFactory().get('/accounts/register')

@pytest.mark.django_db
def test_RegistrationForm_create_user(client, accounts_request):
    rf = RequestFactory()
    data = {'email': 'test@test.com',
            'institution': 'uon',
            'full_name': 'testuser',
            'password1': 'qwertyuiopasdfghjkl',
            'password2': 'qwertyuiopasdfghjkl'}

    assert not User.objects.filter(email=data['email']).exists()
    form = RegistrationForm(data=data, request=accounts_request)
    assert form.is_valid()
    form.save()
    assert User.objects.filter(email=data['email']).exists()

@pytest.mark.django_db
def test_RegistrationForm_password_too_simple(client, accounts_request):
    rf = RequestFactory()
    data = {'email': 'test@test.com',
            'institution': 'uon',
            'full_name': 'testuser',
            'password1': 'password',
            'password2': 'password'}

    form = RegistrationForm(data=data, request=accounts_request)

@pytest.mark.django_db
def test_RegistrationForm_passwords_not_matching(client, accounts_request):
    rf = RequestFactory()
    data = {'email': 'test@test.com',
            'institution': 'uon',
            'full_name': 'testuser',
            'password1': 'Aqwertyuiopasdfghjk',
            'password2': 'qwertyuiopasdfghjkl'}

    form = RegistrationForm(data=data, request=accounts_request)

@pytest.mark.django_db
def test_RegistrationForm_no_passwords(client, accounts_request):
    rf = RequestFactory()
    data = {'email': 'test@test.com',
            'institution': 'uon',
            'full_name': 'testuser'}

    form = RegistrationForm(data=data, request=accounts_request)



@pytest.mark.django_db
def test_RegistrationForm_no_email(client, accounts_request):
    rf = RequestFactory()
    data = {'institution': 'uon',
            'full_name': 'testuser',
            'password1': 'qwertyuiopasdfghjkl',
            'password2': 'qwertyuiopasdfghjkl'}

    form = RegistrationForm(data=data, request=accounts_request)


@pytest.mark.django_db
def test_RegistrationForm_invalid_email(client, accounts_request):
    rf = RequestFactory()
    data = {'email': 'bla',
            'institution': 'uon',
            'full_name': 'testuser',
            'password1': 'qwertyuiopasdfghjkl',
            'password2': 'qwertyuiopasdfghjkl'}

    form = RegistrationForm(data=data, request=accounts_request)

@pytest.mark.django_db
def test_RegistrationForm_institution_optional(client, accounts_request):
    rf = RequestFactory()
    data = {'email': 'test@test.com',
            'full_name': 'testuser',
            'password1': 'qwertyuiopasdfghjkl',
            'password2': 'qwertyuiopasdfghjkl'}

    form = RegistrationForm(data=data, request=accounts_request)


@pytest.mark.django_db
def test_RegistrationForm_no_name(client, accounts_request):
    rf = RequestFactory()
    data = {'email': 'test@test.com',
            'institution': 'uon',
            'password1': 'qwertyuiopasdfghjkl',
            'password2': 'qwertyuiopasdfghjkl'}

    form = RegistrationForm(data=data, request=accounts_request)
