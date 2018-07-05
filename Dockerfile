FROM python:3.4

ENV PYTHONUNBUFFERED 0

RUN mkdir /code

COPY requirements-dev.txt requirements.txt /code/

WORKDIR /code

RUN pip install --upgrade pip \
    && pip install -r /code/requirements.txt \
    && pip install -r /code/requirements-dev.txt \
    && pip install pip-tools

COPY . /code
