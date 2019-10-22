#!/bin/sh

python /app/manage.py geo_import finland --municipalities
python /app/manage.py geo_import helsinki --divisions
python /app/manage.py mark_divisions_of_interest
python /app/manage.py migrate --noinput
