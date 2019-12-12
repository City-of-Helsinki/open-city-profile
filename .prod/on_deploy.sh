#!/bin/sh

python /app/manage.py migrate --noinput
python /app/manage.py seed_data
