import os

import pytest
from accounts.models import User
from django.contrib.auth.hashers import check_password
from django.core.management import call_command


@pytest.mark.django_db
def test_create_admin():
    assert not User.objects.filter(email='x@y.com').exists()
    os.environ['DJANGO_SUPERUSER_EMAIL'] = 'x@y.com'
    os.environ['DJANGO_SUPERUSER_PASSWORD'] = 'password'
    os.environ['DJANGO_SUPERUSER_INSTITUTION'] = 'notts'
    call_command('create_admin')
    assert User.objects.filter(email='x@y.com').exists()
    user = User.objects.get(email='x@y.com')
    assert user.institution == 'notts'
    assert check_password('password', user.password)
