import pytest
from accounts.models import User
from django.core import mail
from django.urls import reverse


def test_my_account_view_requires_login(client):
    response = client.get('/accounts/myaccount/')
    assert response.status_code == 302
    assert '/login/' in response.url


@pytest.mark.django_db
def test_user_can_delete_own_account(client, logged_in_user):
    response = client.post(f'/accounts/{logged_in_user.pk}/delete/')
    assert response.status_code == 302
    assert not User.objects.filter(pk=logged_in_user.pk).exists()
    assert response.url == reverse('home')


@pytest.mark.django_db
def test_delete_user_requires_login(client, other_user):
    response = client.post(f'/accounts/{other_user.pk}/delete/')
    assert response.status_code == 302
    assert User.objects.filter(pk=other_user.pk).exists()
    assert '/login' in response.url


@pytest.mark.django_db
def test_cannot_delete_other_account(client, logged_in_user, other_user):

    response = client.post(f'/accounts/{other_user.pk}/delete/')
    assert response.status_code == 403
    assert User.objects.filter(pk=other_user.pk).exists()


@pytest.mark.django_db
def test_admin_requires_login(client, admin_user):
    response = client.post('/admin/')
    assert response.status_code == 302


@pytest.mark.django_db
def test_admin_requires_admin_rights(client, logged_in_user):
    response = client.post('/admin/')
    assert response.status_code == 302


@pytest.mark.django_db
def test_logged_in_admin_can_see_admin(client, logged_in_admin):
    response = client.post('/admin/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_can_register(client):
    response = client.post('/accounts/register/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_register(client, settings):
    num_mails = len(mail.outbox)
    data = {'email': 'test@test.com',
            'institution': 'uon',
            'full_name': 'testuser',
            'password1': 'qwertyuiopasdfghjkl',
            'password2': 'qwertyuiopasdfghjkl'}

    assert not User.objects.filter(email=data['email']).exists()

    settings.AP_PREDICT_LDAP = True
    response = client.post('/accounts/register/', data=data)
    assert 'Registration is disabled when using LDAP' in str(response.content)
    assert not User.objects.filter(email=data['email'])

    settings.AP_PREDICT_LDAP = False
    client.post('/accounts/register/', data=data)
    assert User.objects.filter(email=data['email']).exists()
    assert len(mail.outbox) == num_mails + 1
    assert User.objects.get(email=data['email']).is_authenticated


@pytest.mark.django_db
def test_my_account_not_logged_in(client, user):
    response = client.post('/accounts/myaccount/')
    assert response.status_code == 302


@pytest.mark.django_db
def test_my_account_logged_in(client, logged_in_user):
    response = client.post('/accounts/myaccount/')
    assert response.status_code == 200
