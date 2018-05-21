FROM python:3.4

ENV PYTHONUNBUFFERED 0

RUN mkdir /code
WORKDIR /code

COPY . /code

RUN pip install --upgrade pip \
    && pip install -r /code/requirements.txt \
    && pip install -r /code/requirements-dev.txt \
    && pip install pip-tools
