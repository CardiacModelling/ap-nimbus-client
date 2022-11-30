import os
from datetime import datetime
from shutil import copyfile

import pytest
from accounts.admin import UserForm
from accounts.forms import MyAccountForm, RegistrationForm
from accounts.models import User
from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.core.files.uploadedfile import TemporaryUploadedFile
from django.test.client import RequestFactory


def data_equals_user(data, usr):
    return data['email'] == usr.email and \
        data['full_name'] == usr.full_name and \
        data['institution'] == usr.institution


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
    def test_modify_user(self, user):
        data = {'email': 'new@email.com',
                'full_name': 'new name',
                'institution': 'new institution'}
        assert not data_equals_user(data, user)
        form = MyAccountForm(instance=user, data=data)
        assert form.is_valid()
        form.save()
        assert data_equals_user(data, user)

    def test_same_email_user(self, user, admin_user):
        data = {'email': admin_user.email,
                'full_name': user.full_name,
                'institution': user.institution}
        assert not data_equals_user(data, user)
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


@pytest.mark.django_db
class TestUserForm:
    def upload_accounts(self, tmp_path, file_name):
        test_file = os.path.join(settings.BASE_DIR, 'accounts', 'tests', file_name)
        temp_file = os.path.join(tmp_path, file_name)
        assert os.path.isfile(test_file), str(test_file)
        copyfile(test_file, temp_file)
        assert os.path.isfile(temp_file)

        tempfile = TemporaryUploadedFile(file_name, 'text/plain', os.path.getsize(test_file), 'utf-8')
        tempfile.file = open(temp_file, 'rb')
        return tempfile

    def test_modify_user(self, user):
        data = {'email': 'new@email.com',
                'full_name': 'new name',
                'institution': 'new institution',
                'date_joined': datetime.now()}
        assert not data_equals_user(data, user)
        form = UserForm(instance=user, data=data)
        assert form.is_valid()
        form.save()
        assert data_equals_user(data, user)

    def test_same_email_user(self, user, admin_user):
        data = {'email': admin_user.email,
                'full_name': user.full_name,
                'institution': user.institution,
                'date_joined': datetime.now()}
        assert not data_equals_user(data, user)
        form = UserForm(instance=user, data=data)
        assert not form.is_valid()  # can't change email to one of an existing user

    def test_no_email(self, user):
        user.email = None
        data = {'institution': 'uon',
                'full_name': 'testuser',
                'date_joined': datetime.now()}
        form = UserForm(instance=user, data=data)
        assert not form.is_valid()

    def test_invalid_email(self, user):
        data = {'email': 'bla',
                'institution': 'uon',
                'full_name': 'testuser',
                'date_joined': datetime.now()}
        form = UserForm(instance=user, data=data)
        assert not form.is_valid()

    def test_institution_optional(self, user):
        password = user.password
        data = {'email': 'test@test.com',
                'full_name': 'testuser',
                'date_joined': datetime.now()}
        form = UserForm(instance=user, data=data)
        form.is_valid()
        assert form.is_valid()
        form.save()
        user.refresh_from_db()
        assert password == user.password

    def test_no_name(self, user):
        data = {'email': 'test@test.com',
                'institution': 'uon',
                'date_joined': datetime.now()}
        form = UserForm(instance=user, data=data)
        assert not form.is_valid()

    def test_no_date_joined(self, user):
        data = {'email': 'test@test.com',
                'institution': 'uon',
                'full_name': 'testuser'}
        form = UserForm(instance=user, data=data)
        assert not form.is_valid()

    def test_change_password(self, user):
        assert not check_password('NewPassw0rd', user.password)
        data = {'email': 'test@test.com',
                'institution': 'uon',
                'full_name': 'testuser',
                'date_joined': datetime.now(),
                'password1': 'NewPassw0rd',
                'password2': 'NewPassw0rd'}
        form = UserForm(instance=user, data=data)
        assert form.is_valid()
        form.save()
        user.refresh_from_db()
        assert check_password('NewPassw0rd', user.password)

    def test_passwords_do_not_match(self, user):
        data = {'email': 'test@test.com',
                'institution': 'uon',
                'full_name': 'testuser',
                'date_joined': datetime.now(),
                'password1': 'NewPassw0rd',
                'password2': 'NewPassw0rd2'}
        form = UserForm(instance=user, data=data)
        assert not form.is_valid()

    def test_create_new_user(self):
        assert User.objects.count() == 0
        data = {'email': 'test@test.com',
                'institution': 'uon',
                'full_name': 'testuser',
                'date_joined': datetime.now()}
        form = UserForm(data=data)
        assert not form.is_valid()
        data['password1'] = 'NewPassw0rd'
        data['password2'] = 'NewPassw0rd'
        form = UserForm(data=data)
        assert form.is_valid()
        form.save()
        assert User.objects.count() == 1

    def test_bulk_upload(self, tmp_path):
        assert User.objects.count() == 0
        # the upload skips existing users
        User.objects.create(email='pierre.jordaan@novartis.com',
                            full_name='pierre.jordaan',
                            institution='novartis',
                            password='pwd')
        assert User.objects.filter(email='pierre.jordaan@novartis.com').exists()

        tsv_upload = self.upload_accounts(tmp_path, 'accounts.tsv')
        form = UserForm({}, {'tsv': tsv_upload})
        assert form.is_valid()
        form.save()
        assert User.objects.count() == 3
        assert User.objects.filter(email='pierre.jordaan@novartis.com').exists()
        assert User.objects.filter(email='yawyisrael@gmail.com').exists()
        assert User.objects.filter(email='bernard_christophe@hotmail.com').exists()

    def test_bulk_upload_no_accounts(self, tmp_path):
        tsv_upload = self.upload_accounts(tmp_path, 'accounts2.tsv')
        form = UserForm({}, {'tsv': tsv_upload})
        assert not form.is_valid()
        assert 'TSV file did not contain (new) user accounts.' in str(form.errors)

    def test_wrong_mime_type(self, tmp_path):
        tsv_upload = self.upload_accounts(tmp_path, 'error-mimetype.tsv')
        form = UserForm({}, {'tsv': tsv_upload})
        assert not form.is_valid()
        assert 'Invalid TSV file' in str(form.errors)
