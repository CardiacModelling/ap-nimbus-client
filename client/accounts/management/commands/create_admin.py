import os

from accounts.models import User
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = ('Create Django superuser by: (1) new user on application initialisation; or (2) new user if '
            'not currently in the system; or (3) elevation of privileges of existing user. '
            'Users are identified by their email address. '
            'See https://ap-nimbus.readthedocs.io/en/latest/running/client-direct/index.html#environment-variables')

    def handle(self, *args, **kwargs):
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
        full_name = os.environ.get('DJANGO_SUPERUSER_FULLNAME', email)
        institution = os.environ.get('DJANGO_SUPERUSER_INSTITUTION', 'unknown')
        password = make_password(os.environ.get('DJANGO_SUPERUSER_PASSWORD'))
        if not User.objects.filter(email=email).exists():
            # User with specified email does not exist. Create new user from env var values.
            User.objects.create(email=email,
                                full_name=full_name,
                                institution=institution,
                                password=password,
                                is_superuser=True,
                                is_staff=True,
                                is_active=True)
        else:
            # User with specified email exists. Overwrite retrieved values with env var values.
            user = User.objects.get(email=email)
            user.full_name = full_name
            user.institution = institution
            user.password = password
            user.is_superuser = True
            user.is_staff = True
            user.is_active = True
            user.save()
