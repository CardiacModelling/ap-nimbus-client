# Building the image locally (run from the repository root):
# docker build -t cardiacmodelling/ap-nimbus-client-direct:local -f docker/Dockerfile .

# Starting a container:
# 1. Create an env file (see docker/env for a template)
# 2. Create a network
#    docker network create ap-nimbus-network
# 3. Start a postgres container
#    docker run --name name-postgres --network ap-nimbus-network --user postgres --env-file docker/env -p 5432:5432 postgres:14.1-bullseye
# 4. Start the client container
#    docker run --init -it --network ap-nimbus-network -p 4240:80 --env-file docker/env cardiacmodelling/ap-nimbus-client-direct:local

FROM debian:bullseye-slim

LABEL version="2.1.0"

USER root
ENV pythonpath /usr/local/lib/python3
RUN useradd -ms /bin/bash appredict

RUN mkdir /opt/django
WORKDIR /opt/django

# install required components
RUN apt-get update
RUN apt-get install -y --no-install-recommends \
    python3 \
    python3-dev \
    python3-pip \
    ca-certificates \
    git \
    build-essential \
    nginx \
    libmagic-dev \
    uwsgi \
    uwsgi-plugin-python3 \
    libpcre3-dev \
    libldap2-dev libsasl2-dev \
    sudo && \
    rm -rf /var/lib/apt/lists/*

# Update system to use Python3 by default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1
RUN update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

COPY . /opt/django/ap-nimbus-client
RUN python -m pip install -r /opt/django/ap-nimbus-client/requirements/requirements.txt
RUN rm /etc/nginx/sites-enabled/*
RUN ln -s /opt/django/ap-nimbus-client/docker/client_nginx.conf /etc/nginx/sites-enabled/

# allow appredict to control uwsgi and nginx
WORKDIR /opt/django/ap-nimbus-client/client
RUN echo '\nDefaults!/usr/local/bin/uwsgi setenv\n\
appredict ALL=(ALL) NOPASSWD: /etc/init.d/nginx\n\
appredict ALL=(ALL) NOPASSWD: /usr/local/bin/uwsgi\n\
appredict ALL=(ALL) NOPASSWD: /bin/cat /opt/django/media/uwsgi.log, /usr/bin/tail -f /opt/django/media/uwsgi.log\n' >> /etc/sudoers

# make sure appredict owns the django files
RUN chown -R appredict:appredict /opt/django/

#remove git
RUN apt-get remove --purge git -y && \
    rm -rf /var/lib/apt/lists/*

# create folder to link data volue
USER appredict
RUN mkdir /opt/django/media

# create database, migrate, deploy static files and (re-)start nginx and uwsgi
CMD python /opt/django/ap-nimbus-client/docker/create_database.py; \
    python /opt/django/ap-nimbus-client/client/manage.py migrate --noinput; \
    python /opt/django/ap-nimbus-client/client/manage.py collectstatic --noinput; \
    python /opt/django/ap-nimbus-client/client/manage.py  create_admin; \
    sudo /etc/init.d/nginx restart; \
    sudo --preserve-env /usr/local/bin/uwsgi --ini /opt/django/ap-nimbus-client/docker/client_uwsgi.ini --uid appredict
