import os

from accounts.models import User
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = ('Create superuser or set the username and password if superuser with the given email already exists. '
            'The command uses DJANGO_SUPERUSER_EMAIL DJANGO_SUPERUSER_USERNAME DJANGO_SUPERUSER_INSTITUTION and '
            'DJANGO_SUPERUSER_PASSWORD environment variables')

    def handle(self, *args, **kwargs):
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
        full_name = os.environ.get('DJANGO_SUPERUSER_USERNAME', email)
        institution = os.environ.get('DJANGO_SUPERUSER_INSTITUTION', 'unknown')
        password = make_password(os.environ.get('DJANGO_SUPERUSER_PASSWORD'))
        if not User.objects.filter(email=email).exists():
            User.objects.create(email=email,
                                full_name=full_name,
                                institution=institution,
                                password=password,
                                is_superuser=True,
                                is_staff=True,
                                is_active=True)
        else:
            user = User.objects.get(email=email)
            user.institution=institution
            user.password = password
            user.is_superuser = True
            user.is_staff = True
            user.is_active = True
            user.save()
