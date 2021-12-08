import pytest
from django.urls import reverse

from accounts.models import User


def test_my_account_view_requires_login(client):
    response = client.get('/accounts/myaccount/')
    assert response.status_code == 302
    assert '/login/' in response.url


@pytest.mark.django_db
def test_user_can_delete_own_account(client, logged_in_user):
    response = client.post(
        '/accounts/%d/delete/' % logged_in_user.pk,
    )

    assert response.status_code == 302
    assert not User.objects.filter(pk=logged_in_user.pk).exists()
    assert response.url == reverse('home')


@pytest.mark.django_db
def test_delete_user_requires_login(client, other_user):
    response = client.post(
        '/accounts/%d/delete/' % other_user.pk,
    )
    assert response.status_code == 302
    assert User.objects.filter(pk=other_user.pk).exists()
    assert '/login' in response.url


@pytest.mark.django_db
def test_cannot_delete_other_account(client, logged_in_user, other_user):

    response = client.post(
        '/accounts/%d/delete/' % other_user.pk,
    )

    assert response.status_code == 403
    assert User.objects.filter(pk=other_user.pk).exists()



@pytest.mark.django_db
def test_admin_requires_login(client, admin_user):

    response = client.post(
        '/admin/',
    )

    assert response.status_code == 302


@pytest.mark.django_db
def test_admin_requires_admin_rights(client, logged_in_user):

    response = client.post(
        '/admin/',
    )

    assert response.status_code == 302


@pytest.mark.django_db
def test_logged_in_admin_can_see_admin(client, logged_in_admin):

    response = client.post(
        '/admin/',
    )

    assert response.status_code == 200

@pytest.mark.django_db
def test_register(client):

    response = client.post(
        'accounts/register/',
    )
