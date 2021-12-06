#!/bin/sh -e
/opt/django/venv/bin/python /opt/django/ap-nimbus-client/docker/create_database.py
/opt/django/venv/bin/python /opt/django/ap-nimbus-client/client/manage.py migrate --noinput
/opt/django/venv/bin/python /opt/django/ap-nimbus-client/client/manage.py collectstatic --noinput
export DJANGO_SUPERUSER_USERNAME="${DJANGO_SUPERUSER_USERNAME:=$DJANGO_SUPERUSER_EMAIL}"
export DJANGO_SUPERUSER_INSTITUTION="${DJANGO_SUPERUSER_INSTITUTION:=unknown}"
/opt/django/venv/bin/python /opt/django/ap-nimbus-client/client/manage.py createsuperuser --noinput --full_name $DJANGO_SUPERUSER_USERNAME --institution $DJANGO_SUPERUSER_INSTITUTION || true
/etc/init.d/nginx restart
/opt/django/venv/bin/uwsgi --ini /opt/django/ap-nimbus-client/docker/client_uwsgi.ini --logto2 /var/log/uwsgi.log
