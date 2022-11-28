FROM python:3.9-slim

USER root
ENV pythonpath /usr/local/lib/python3
RUN useradd -ms /bin/bash appredict

RUN mkdir /opt/django
WORKDIR /opt/django

# install required components
RUN apt-get update
RUN apt-get install -y --no-install-recommends \
    git \
    build-essential \
    nginx \
    libmagic-dev \
    uwsgi \
    uwsgi-plugin-python3 \
    libpcre3-dev \
    sudo && \
    rm -rf /var/lib/apt/lists/*

# get the client from git & install
RUN git clone --recursive --branch master https://github.com/CardiacModelling/ap-nimbus-client.git
RUN python -m pip install -r /opt/django/ap-nimbus-client/requirements/requirements.txt
RUN rm /etc/nginx/sites-enabled/*
RUN ln -s /opt/django/ap-nimbus-client/docker/client_nginx.conf /etc/nginx/sites-enabled/

# allow appredict to control uwsgi and nginx
WORKDIR /opt/django/ap-nimbus-client/client
RUN echo "Defaults!/usr/local/bin/uwsgi setenv" >> /etc/sudoers
RUN echo "appredict ALL=(ALL) NOPASSWD: /etc/init.d/nginx" >> /etc/sudoers
RUN echo "appredict ALL=(ALL) NOPASSWD: /usr/local/bin/uwsgi" >> /etc/sudoers

# make sure appredict owns the django files
RUN chown -R appredict:appredict /opt/django/

# create folder to link data volue
USER appredict
RUN mkdir /opt/django/media

# create database, migrate, deploy static files and (re-)start nginx and uwsgi
CMD python /opt/django/ap-nimbus-client/docker/create_database.py; \
    python /opt/django/ap-nimbus-client/client/manage.py migrate --noinput; \
    python /opt/django/ap-nimbus-client/client/manage.py collectstatic --noinput; \
    sudo /etc/init.d/nginx restart; \
    sudo --preserve-env /usr/local/bin/uwsgi --ini /opt/django/ap-nimbus-client/docker/client_uwsgi.ini --uid appredict
