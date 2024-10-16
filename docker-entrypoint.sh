#!/bin/bash

set -e

if [ -z "$SKIP_DATABASE_CHECK" -o "$SKIP_DATABASE_CHECK" = "0" ]; then
    until nc --verbose --wait 30 --send-only "$DATABASE_HOST" 5432
    do
      echo "Waiting for postgres database connection..."
      sleep 1
    done
    echo "Database is up!"
fi


# Apply database migrations
if [[ "$APPLY_MIGRATIONS" = "1" ]]; then
    echo "Applying database migrations..."
    ./manage.py migrate --noinput
fi

if [[ "$APPLY_MIGRATIONS" = "1" ]] && [[ "$SEED_DEVELOPMENT_DATA" = "1" ]]; then
    echo "Seeding initial development data..."
    ./manage.py seed_development_data
fi

if [[ "$SET_ALLOWED_DATA_FIELDS" = "1" ]]; then
    echo "Set allowed data fields..."
    ./manage.py set_allowed_data_fields < open_city_profile/configuration/allowed_data_fields.json
fi

# Create superuser
if [[ "$CREATE_SUPERUSER" = "1" ]]; then
    ./manage.py add_admin_user -u admin -p admin -e admin@example.com
    echo "Admin user created with credentials admin:admin (email: admin@example.com)"
fi

# Start server
if [[ ! -z "$@" ]]; then
    "$@"
elif [[ "$DEV_SERVER" = "1" ]]; then
    python ./manage.py runserver 0.0.0.0:8080
else
    uwsgi --ini .prod/uwsgi.ini
fi
