#!/bin/sh
# Container entrypoint, run as the non-root app user (appredict).
set -e

# Set up the database.
python /opt/django/ap-nimbus-client/docker/create_database.py
python /opt/django/ap-nimbus-client/client/manage.py migrate --noinput
python /opt/django/ap-nimbus-client/client/manage.py collectstatic --noinput
python /opt/django/ap-nimbus-client/client/manage.py create_admin

# Start nginx (as root, worker processes drop to www-data).
sudo /etc/init.d/nginx restart

# Hand off to uwsgi as the container's main process so it receives SIGTERM for a graceful shutdown.
exec sudo --preserve-env /opt/venv/bin/uwsgi --ini /opt/django/ap-nimbus-client/docker/client_uwsgi.ini
