FROM python:3.8-bookworm
ENV PYTHONUNBUFFERED 1

WORKDIR /code

COPY requirements.txt /code

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
