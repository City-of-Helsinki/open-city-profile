#!/bin/bash

python /app/manage.py migrate --noinput

if [[ "$SEED_DEVELOPMENT_DATA" = "1" ]]; then
    python /app/manage.py seed_development_data --superuser
fi
