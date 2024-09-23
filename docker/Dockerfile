FROM debian:bullseye-slim

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

# get the client from git & install
RUN git clone --recursive --branch master --depth 1 https://github.com/CardiacModelling/ap-nimbus-client.git
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
