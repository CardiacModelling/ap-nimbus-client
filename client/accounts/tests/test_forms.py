import pytest
from accounts.forms import MyAccountForm, RegistrationForm
from accounts.models import User
from django.test.client import RequestFactory


@pytest.mark.django_db
class TestRegistrationForm:
    @pytest.fixture
    def accounts_request(self):
        return RequestFactory().get('/accounts/register')

    def test_create_user(self, accounts_request):
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
        form = RegistrationForm(data=data, request=accounts_request)
        assert not form.is_valid()  # can't register same email twice

    def test_create_user_no_commit(self, accounts_request):
        data = {'email': 'test@test.com',
                'institution': 'uon',
                'full_name': 'testuser',
                'password1': 'qwertyuiopasdfghjkl',
                'password2': 'qwertyuiopasdfghjkl'}
        assert not User.objects.filter(email=data['email']).exists()
        form = RegistrationForm(data=data, request=accounts_request)
        assert form.is_valid()
        form.save(commit=False)
        assert not User.objects.filter(email=data['email']).exists()

    def test_password_too_simple(self, accounts_request):
        data = {'email': 'test@test.com',
                'institution': 'uon',
                'full_name': 'testuser',
                'password1': 'password',
                'password2': 'password'}
        form = RegistrationForm(data=data, request=accounts_request)
        assert not form.is_valid()

    def test_passwords_not_matching(self, accounts_request):
        data = {'email': 'test@test.com',
                'institution': 'uon',
                'full_name': 'testuser',
                'password1': 'Aqwertyuiopasdfghjk',
                'password2': 'qwertyuiopasdfghjkl'}
        form = RegistrationForm(data=data, request=accounts_request)
        assert not form.is_valid()

    def test_no_passwords(self, accounts_request):
        data = {'email': 'test@test.com',
                'institution': 'uon',
                'full_name': 'testuser'}
        form = RegistrationForm(data=data, request=accounts_request)
        assert not form.is_valid()

    def test_no_email(self, accounts_request):
        data = {'institution': 'uon',
                'full_name': 'testuser',
                'password1': 'qwertyuiopasdfghjkl',
                'password2': 'qwertyuiopasdfghjkl'}
        form = RegistrationForm(data=data, request=accounts_request)
        assert not form.is_valid()

    def test_invalid_email(self, accounts_request):
        data = {'email': 'bla',
                'institution': 'uon',
                'full_name': 'testuser',
                'password1': 'qwertyuiopasdfghjkl',
                'password2': 'qwertyuiopasdfghjkl'}
        form = RegistrationForm(data=data, request=accounts_request)
        assert not form.is_valid()

    def test_institution_optional(self, accounts_request):
        data = {'email': 'test@test.com',
                'full_name': 'testuser',
                'password1': 'qwertyuiopasdfghjkl',
                'password2': 'qwertyuiopasdfghjkl'}
        form = RegistrationForm(data=data, request=accounts_request)
        assert form.is_valid()

    def test_no_name(self, accounts_request):
        data = {'email': 'test@test.com',
                'institution': 'uon',
                'password1': 'qwertyuiopasdfghjkl',
                'password2': 'qwertyuiopasdfghjkl'}
        form = RegistrationForm(data=data, request=accounts_request)
        assert not form.is_valid()


@pytest.mark.django_db
class TestMyAccountForm:
    def data_equals_user(data, usr):
        return data['email'] == usr.email and \
            data['full_name'] == usr.full_name and \
            data['institution'] == usr.institution

    def test_modify_user(self, user):
        data = {'email': 'new@email.com',
                'full_name': 'new name',
                'institution': 'new institution'}
        assert not TestMyAccountForm.data_equals_user(data, user)
        form = MyAccountForm(instance=user, data=data)
        assert form.is_valid()
        form.save()
        assert TestMyAccountForm.data_equals_user(data, user)

    def test_same_email_user(self, user, admin_user):
        data = {'email': admin_user.email,
                'full_name': user.full_name,
                'institution': user.institution}
        assert not TestMyAccountForm.data_equals_user(data, user)
        form = MyAccountForm(instance=user, data=data)
        assert not form.is_valid()  # can't change email to one of an existing user

    def test_no_email(self, user):
        data = {'institution': 'uon',
                'full_name': 'testuser'}
        form = MyAccountForm(instance=user, data=data)
        assert not form.is_valid()

    def test_invalid_email(self, user):
        data = {'email': 'bla',
                'institution': 'uon',
                'full_name': 'testuser'}
        form = MyAccountForm(instance=user, data=data)
        assert not form.is_valid()

    def test_institution_optional(self, user):
        data = {'email': 'test@test.com',
                'full_name': 'testuser'}
        form = MyAccountForm(instance=user, data=data)
        assert form.is_valid()

    def test_no_name(self, user):
        data = {'email': 'test@test.com',
                'institution': 'uon'}
        form = MyAccountForm(instance=user, data=data)
        assert not form.is_valid()
