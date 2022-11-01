#!/bin/sh -e
python /opt/django/ap-nimbus-client/docker/create_database.py
python /opt/django/ap-nimbus-client/client/manage.py migrate --noinput
python /opt/django/ap-nimbus-client/client/manage.py collectstatic --noinput
/etc/init.d/nginx restart
uwsgi --ini /opt/django/ap-nimbus-client/docker/client_uwsgi.ini --daemonize /opt/django/media/uwsgi.log
tial -f /opt/django/media/uwsgi.log

