# Open city profile

## Development with Docker

1. Create `.env` environment file

2. Set the `DEBUG` environment variable to `1`

3. Run `docker-compose up`

4. Run migrations if needed: 
    * `docker exec profile-backend python manage.py migrate`

5. Create superuser if needed: 
    * `docker exec -it profile-backend python manage.py createsuperuser`
    
6. Import relevant Helsinki regions if needed:

    * `docker exec profile-backend python manage.py geo_import finland --municipalities`
    * `docker exec profile-backend python manage.py geo_import helsinki --divisions`
    * `docker exec profile-backend python manage.py mark_divisions_of_interest`
  
7. Run the server:
    * `docker exec -it profile-backend python manage.py runserver 0:8000`


## Development without Docker

### Install pip-tools

* Run `pip install pip-tools`

### Creating Python requirements files

* Run `pip-compile requirements.in`
* Run `pip-compile requirements-dev.in`

### Updating Python requirements files

* Run `pip-compile --upgrade requirements.in`
* Run `pip-compile --upgrade requirements-dev.in`

### Installing Python requirements

* Run `pip-sync requirements.txt requirements-dev.in`

### Database

To setup a database compatible with default database settings:

Create user and database

    sudo -u postgres createuser -P -R -S open_city_profile  # use password `open_city_profile`
    sudo -u postgres createdb -O open_city_profile open_city_profile

Allow user to create test database

    sudo -u postgres psql -c "ALTER USER open_city_profile CREATEDB;"

### Import administrative divisions

In order to have the relevant Helsinki regions run the following commands:

* `python manage.py geo_import finland --municipalities`
* `python manage.py geo_import helsinki --divisions`
* `python manage.py mark_divisions_of_interest`


### Daily running

* Set the `DEBUG` environment variable to `1`.
* Run `python manage.py migrate`
* Run `python manage.py runserver 0:8000`

## Running tests

* Set the `DEBUG` environment variable to `1`.
* Run `pytest`.
