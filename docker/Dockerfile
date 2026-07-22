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

FROM debian:trixie-slim

LABEL version="2.0.0"

USER root
RUN useradd -ms /bin/bash appredict

RUN mkdir /opt/django && chown appredict:appredict /opt/django
WORKDIR /opt/django

# Install required components
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-dev \
    python3-venv \
    ca-certificates \
    build-essential \
    nginx \
    libmagic-dev \
    libpcre2-dev \
    libldap2-dev \
    libsasl2-dev \
    sudo && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies into a dedicated virtualenv
RUN python3 -m venv /opt/venv

# Put the venv first on PATH so bare python/pip/uwsgi resolve to it
ENV PATH="/opt/venv/bin:$PATH"

COPY --chown=appredict:appredict . /opt/django/ap-nimbus-client
RUN python -m pip install --no-cache-dir --upgrade pip && \
    python -m pip install --no-cache-dir -r /opt/django/ap-nimbus-client/requirements/requirements.txt
RUN rm /etc/nginx/sites-enabled/*
RUN ln -s /opt/django/ap-nimbus-client/docker/client_nginx.conf /etc/nginx/sites-enabled/

# Allow appredict to control uwsgi and nginx
WORKDIR /opt/django/ap-nimbus-client/client
RUN echo '\nDefaults!/opt/venv/bin/uwsgi setenv\n\
appredict ALL=(ALL) NOPASSWD: /etc/init.d/nginx\n\
appredict ALL=(ALL) NOPASSWD: /opt/venv/bin/uwsgi\n\
appredict ALL=(ALL) NOPASSWD: /bin/cat /opt/django/media/uwsgi.log, /usr/bin/tail -f /opt/django/media/uwsgi.log\n' >> /etc/sudoers

# Create folder to link data volume
USER appredict
RUN mkdir /opt/django/media

# Create database, migrate, deploy static files and (re-)start nginx and uwsgi.
# Using the CMD json form means SIGTERM from `docker stop` reaches uwsgi for
# a graceful shutdown instead of being swallowed by the shell.
CMD ["/bin/sh", "-c", \
     "python /opt/django/ap-nimbus-client/docker/create_database.py && \
      python /opt/django/ap-nimbus-client/client/manage.py migrate --noinput && \
      python /opt/django/ap-nimbus-client/client/manage.py collectstatic --noinput && \
      python /opt/django/ap-nimbus-client/client/manage.py create_admin && \
      sudo /etc/init.d/nginx restart && \
      exec sudo --preserve-env /opt/venv/bin/uwsgi \
      --ini /opt/django/ap-nimbus-client/docker/client_uwsgi.ini --uid appredict"]
