FROM python:3.8-bookworm
ENV PYTHONUNBUFFERED 1

WORKDIR /code

COPY requirements.txt /code

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Celery normally won't allow running with pickle as root, so might as well establish an app:app
# user. This means that "pip install" commands probably should be done with a container started
# with a "-u root" option:
#   docker-compose run --rm -u root app /bin/bash
RUN groupadd -g 1000 app
RUN useradd -u 1000 -g app -s /bin/bash -m app

USER app
