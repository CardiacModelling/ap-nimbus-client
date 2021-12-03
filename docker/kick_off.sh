#!/bin/sh -e
/opt/django/ap-nimbus-client/venv/bin/python /clientdirect/create_database.py
/opt/django/ap-nimbus-client/venv/bin/python /clientdirect/manage.py  migrate
/opt/django/ap-nimbus-client/venv/bin/python /clientdirect/manage.py  collectstatic
export DJANGO_SUPERUSER_USERNAME="${DJANGO_SUPERUSER_USERNAME:=$DJANGO_SUPERUSER_EMAIL}"
/opt/django/ap-nimbus-client/venv/bin/python /clientdirect/manage.py createsuperuser --noinput || true
/etc/init.d/nginx restart
/opt/django/ap-nimbus-client/venv/bin/uwsgi --ini /opt/django/ap-nimbus-client/docker/client_uwsgi.ini --logto2 /var/log/uwsgi.log
