# Open city profile

[![status](https://travis-ci.com/City-of-Helsinki/open-city-profile.svg)](https://github.com/City-of-Helsinki/open-city-profile)
[![codecov](https://codecov.io/gh/City-of-Helsinki/open-city-profile/branch/develop/graph/badge.svg)](https://codecov.io/gh/City-of-Helsinki/open-city-profile)


## Summary

Open city profile is used to store common information (name, contact
information, areas of interests, ...) about the citizens of the city of Helsinki.

When a citizen is using a service which is connected to the profile, the
service can query for the citizen's information from the profile so that the
citizen doesn't have to enter all of their data every time it is needed. The
services may also provide a better user experience using the profile's data,
for example by returning more relevant search results based on the citizen's
interests.

The same data may also be queried by the employees of the city of Helsinki
while performing their daily duties, for example using the administrative
functions of Venepaikka service.

Open city profile is implemented using Django and it provides a GraphQL API.

## Configuration

See [docs/config.adoc](docs/config.adoc).

## Development with [Docker](https://docs.docker.com/)

Prerequisites:
* Docker engine: 18.06.0+
* Docker compose 1.22.0+

1. Create a `docker-compose.env.yaml` file in the project folder:
   * Use `docker-compose.env.yaml.example` as a base, it does not need any changes
     for getting the project running.
   * Change `DEBUG` and the rest of the Django settings if needed.
     * `TOKEN_AUTH_*`, settings for [tunnistamo](https://github.com/City-of-Helsinki/tunnistamo) authentication service
   * Set entrypoint/startup variables according to taste.
     * `CREATE_SUPERUSER`, creates a superuser with credentials `admin`:`admin` (admin@example.com)
     * `APPLY_MIGRATIONS`, applies migrations on startup
     * `ENABLE_GRAPHIQL`, enables GraphiQL interface for `/graphql/`
     * `SEED_DEVELOPMENT_DATA`, flush data and recreate the environment with
        fake development data (requires `APPLY_MIGRATIONS`)
     * `OIDC_CLIENT_ID`, Tunnistamo client id for enabling GDPR API authorization code flows
     * `OIDC_CLIENT_SECRET`, Tunnistamo client secret for enabling GDPR API authorization code flows
     * `GDPR_AUTH_CALLBACK_URL`, GDPR auth callback URL should be the same which is used by the UI for
       fetching OAuth/OIDC authorization token for using the GDPR API
     * `TUNNISTAMO_API_TOKENS_URL`, Tunnistamo URL from which the backend will fetch API tokens for GDPR API use.

2. Run `docker-compose up`
    * The project is now running at [localhost:8080](http://localhost:8080)

**Optional steps**

1. Run migrations:
    * Taken care by the example env
    * `docker exec profile-backend python manage.py migrate`

2. Seed data
    * Taken care by the example env
    * See also _Seed development data_ below
    * `docker exec profile-backend python manage.py seed_data`

3. Create superuser:
    * Taken care by the example env
    * `docker exec -it profile-backend python manage.py createsuperuser`

5. Set permissions for service staff members if needed:
   * Create group(s) (via Django admin) and add user(s) to the group
   * Create service permissions for group manually via Django admin or for example:
     * `docker exec profile-backend python manage.py add_object_permission ServiceName GroupName can_view_profiles`,  where:
       * `ServiceName` is the name of the Service the permission is given for
       * `GroupName` is the name of the group to whom the permission is give
       * `can_view_profiles` is the name of the permission
   * Permissions can be removed as follows:
     * `docker exec profile-backend python manage.py remove_object_permission ServiceName GroupName can_view_profiles`

6. Seed development data
    * **Note!** This command will flush the database.
    * Add all data with defaults: `docker exec profile-backend python manage.py
    seed_data --development`
    * See `python manage.py help seed_data` for optional arguments
    * Command will generate:
      * All available services
      * One group per service (with `can_manage_profiles` permissions)
      * One user per group (with username `{group.name}_user`)
      * Profiles
        * With user
        * With email, phone number and address
        * Connects to one random service


## Development without Docker

Prerequisites:
* PostgreSQL 9.6
* PostGIS 2.5
* Python 3.7


### Installing Python requirements

* Run `pip install -r requirements.txt`
* Run `pip install -r requirements-dev.txt` (development requirements)


### Database

To setup a database compatible with default database settings:

Create user and database

    sudo -u postgres createuser -P -R -S open_city_profile  # use password `open_city_profile`
    sudo -u postgres createdb -O open_city_profile open_city_profile

Create extensions in the database

    sudo -u postgres psql open_city_profile -c "CREATE EXTENSION postgis;"

Allow user to create test database

    sudo -u postgres psql -c "ALTER USER open_city_profile CREATEDB;"


### Daily running

* Create `.env` file: `touch .env`
* Set the `DEBUG` environment variable to `1`.
* Run `python manage.py migrate`
* Run `python manage.py createsuperuser`
* Run `python manage.py runserver 0:8000`

The project is now running at [localhost:8000](http://localhost:8000)


## Keeping Python requirements up to date

This repository contains `requirements*.in` and corresponding `requirements*.txt` files for requirements handling. The `requirements*.txt` files are generated from the `requirements*.in` files with `pip-compile`.

1. Add new packages to `requirements.in` or `requirements-dev.in`

3. Update `.txt` file for the changed requirements file:
    * `pip-compile requirements.in`
    * `pip-compile requirements-dev.in`
    * **Note:** the `requirements*.txt` files added to version control are meant to be used in the containerized environment where the service is run. Because [Python package dependencies are environment dependent](https://github.com/jazzband/pip-tools/#cross-environment-usage-of-requirementsinrequirementstxt-and-pip-compile) they need to be generated within a similar environment. This can be done by running the `pip-compile` command within Docker, for example like this: `docker-compose exec django pip-compile requirements.in` ([the container needs to be running](#development-with-docker) beforehand).

4. If you want to update dependencies to their newest versions, run:
    * `pip-compile --upgrade requirements.in`

5. To install Python requirements run:
    * `pip-sync requirements.txt`

**Note:** when updating dependencies, read the [dependency update checklist](docs/dependency-update.adoc) if there's anything you need to pay attention to.

## Code format

This project uses
[`black`](https://github.com/ambv/black),
[`flake8`](https://gitlab.com/pycqa/flake8) and
[`isort`](https://github.com/timothycrosley/isort)
for code formatting and quality checking. Project follows the basic
black config, without any modifications.

Basic `black` commands:

* To let `black` do its magic: `black .`
* To see which files `black` would change: `black --check .`

[`pre-commit`](https://pre-commit.com/) can be used to install and
run all the formatting tools as git hooks automatically before a
commit.


## Running tests

The tests require a Postgres database to which to connect to. Here's one way to run the tests:

* Bring the service up with `docker-compose up`. This also brings up the required Postgres server.
* Run tests within the Django container: `docker-compose exec django pytest`.


## Issue tracking

* [Github issue list](https://github.com/City-of-Helsinki/open-city-profile/issues)
* [Jira issues](https://helsinkisolutionoffice.atlassian.net/projects/OM/issues/?filter=allissues)


## API documentation

* [Generated GraphiQL documentation](https://profiili-api.test.kuva.hel.ninja/graphql/)


## Environments
Test: https://profiili-api.test.kuva.hel.ninja/graphql/

Production: https://profiili-api.prod.kuva.hel.ninja/graphql/

## CI/CD builds

Project is using [Gitlab](https://gitlab.com/City-of-Helsinki/KuVa/github-mirrors/open-city-profile/pipelines)
for automated builds and deployment into the test environment.
The test environment is built automatically from the `develop` branch.

## Anonymised Database dump

See [docs/database_dump.adoc](docs/database_dump.adoc).

## Dependent services

For a complete service the following additional components are also required:
* [tunnistamo](https://github.com/City-of-Helsinki/tunnistamo) is used as the authentication service
* [open-city-profile-ui](https://github.com/City-of-Helsinki/open-city-profile-ui/) provides UI
