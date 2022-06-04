FROM python:3.7-buster
ENV PYTHONUNBUFFERED 1

WORKDIR /code
COPY Pipfile Pipfile.lock /code/

RUN pip install pipenv
RUN pipenv install

