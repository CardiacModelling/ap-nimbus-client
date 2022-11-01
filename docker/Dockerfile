FROM python:3.9-slim

USER root
ENV pythonpath /usr/local/lib/python3


RUN mkdir /opt/django
WORKDIR /opt/django

# install required components
RUN apt-get update
RUN apt-get install git -y
RUN apt-get install build-essential -y
RUN apt-get install nginx -y
RUN apt-get install libmagic-dev -y
RUN apt-get install uwsgi
RUN apt-get install uwsgi-plugin-python3 -y
RUN apt-get install libpcre3-dev -y

# get the client from git & install
RUN git clone --recursive --branch UI_Improvements https://github.com/CardiacModelling/ap-nimbus-client.git
RUN python -m pip install -r /opt/django/ap-nimbus-client/requirements/requirements.txt
RUN rm /etc/nginx/sites-enabled/*
RUN ln -s /opt/django/ap-nimbus-client/docker/client_nginx.conf /etc/nginx/sites-enabled/
RUN chmod +x /opt/django/ap-nimbus-client/docker/kick_off.sh


WORKDIR /opt/django/ap-nimbus-client/client

# start & create database

CMD /opt/django/ap-nimbus-client/docker/kick_off.sh
