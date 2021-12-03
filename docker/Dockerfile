FROM python:3.9-slim

USER root

# environment variables
ENV PYTHONUNBUFFERED=1
ENV POSTGRES_DB=django
ENV POSTGRES_USER=postgres
ENV POSTGRES_HOST=ap_nimbus_postgres
ENV POSTGRES_PORT=5432
ENV DJANGO_PORT=8000

RUN mkdir /opt/django
WORKDIR /opt/django

# install required components
RUN apt-get update
RUN apt-get install git -y
RUN apt-get install build-essential -y
RUN apt-get install nginx -y

# Set up python virtual environment
RUN python3 -m venv venv

# get the client from git & install
RUN git clone --recursive https://github.com/CardiacModelling/ap-nimbus-client.git
RUN /opt/django/venv/bin/python -m pip install -r /opt/django/ap-nimbus-client/requirements/requirements.txt
RUN rm /etc/nginx/sites-enabled/*
RUN ln -s /opt/django/ap-nimbus-client/docker/client_nginx.conf /etc/nginx/sites-enabled/


WORKDIR /opt/django/ap-nimbus-client/client

# start & create database
CMD /opt/django/ap-nimbus-client/docker/kick_off.sh
