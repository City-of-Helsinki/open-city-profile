# Open city profile

[![Continuous integration](https://github.com/City-of-Helsinki/open-city-profile/actions/workflows/ci.yml/badge.svg)](https://github.com/City-of-Helsinki/open-city-profile/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/City-of-Helsinki/open-city-profile/branch/develop/graph/badge.svg)](https://codecov.io/gh/City-of-Helsinki/open-city-profile)


## Summary

Open city profile is used to store common information (name, contact
information, ...) about the citizens of the city of Helsinki.

When a citizen is using a service which is connected to the profile, the
service can query for the citizen's information from the profile so that the
citizen doesn't have to enter all of their data every time it is needed. The
services may also provide a better user experience using the profile's data,
for example by returning more relevant search results based on the citizen's
interests.

The same data may also be queried by the employees of the city of Helsinki
while performing their daily duties, for example using the administrative
functions of services.

Open city profile is implemented using Django and it provides a GraphQL API.

## Configuration

See [docs/config.adoc](docs/config.adoc).

## Development with [Docker](https://docs.docker.com/)

Prerequisites:
* Docker engine: 18.06.0+
* Docker compose 1.22.0+

1. Create a `compose.env` file in the project folder:
   * Use `compose.env.example` as a base, it does not need any changes
     for getting the project running.
   * Change `DEBUG` and the rest of the Django settings if needed.
     * `TOKEN_AUTH_*`, settings for authentication service
   * Set entrypoint/startup variables according to taste.
     * `CREATE_SUPERUSER`, creates a superuser with credentials `admin`:`admin` (admin@example.com)
     * `APPLY_MIGRATIONS`, applies migrations on startup
     * `ENABLE_GRAPHIQL`, enables GraphiQL interface for `/graphql/`
     * `ENABLE_GRAPHQL_INTROSPECTION`, enables GraphQL introspection queries
     * `SEED_DEVELOPMENT_DATA`, flush data and recreate the environment with
        fake development data (requires `APPLY_MIGRATIONS`)
     * `KEYCLOAK_BASE_URL`, the base URL of the Keycloak server, including any configured context path.
     * `KEYCLOAK_REALM`, the name of the [Keycloak realm](https://www.keycloak.org/docs/latest/server_admin/#the-master-realm) to use.
     * `KEYCLOAK_CLIENT_ID`, authentication to the Keycloak instance happens [using a service account](https://www.keycloak.org/docs/latest/server_development/#authenticate-with-a-service-account). This is the client id.
     * `KEYCLOAK_CLIENT_SECRET`, ...and this is the client secret.
     * `KEYCLOAK_GDPR_CLIENT_ID`, client id to use in the authorization code flow for GDPR calls.
     * `KEYCLOAK_GDPR_CLIENT_SECRET`, client secret to use in the authorization code flow for GDPR calls.
     * `GDPR_AUTH_CALLBACK_URL`, GDPR auth callback URL should be the same which is used by the UI for
       fetching OAuth/OIDC authorization token for using the GDPR API

2. Run `docker compose up`
    * The project is now running at [localhost:8080](http://localhost:8080)

**Optional steps**

1. Run migrations:
    * Taken care by the example env
    * `docker exec profile-backend python manage.py migrate`

2. Seed development data
    * Taken care by the example env
    * See also _Seed development data_ below
    * `docker exec profile-backend python manage.py seed_development_data`

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
    seed_development_data`
    * See `python manage.py help seed_development_data` for optional arguments
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
* PostgreSQL 17
* Python 3.12


### Installing Python requirements

* Install [`uv`](https://docs.astral.sh/uv/getting-started/installation/) `>=0.9.17`
* Run `uv sync` (installs production and development requirements)
  * Add `--group prod` if you also need `uwsgi`/`uwsgitop` (not required for local development)

`uv >=0.9.17` is required because the project uses the ISO 8601 duration
`exclude-newer = "P3D"` configuration in `pyproject.toml`.


### Database

To setup a database compatible with default database settings:

Create user and database

    sudo -u postgres createuser -P -R -S open_city_profile  # use password `open_city_profile`
    sudo -u postgres createdb -O open_city_profile open_city_profile

Allow user to create test database

    sudo -u postgres psql -c "ALTER USER open_city_profile CREATEDB;"


### Daily running

* Create a `.env` file in the project root with at least the following:

      DEBUG=1
      FIELD_ENCRYPTION_KEYS=<generate-a-local-key>

  * `FIELD_ENCRYPTION_KEYS` is **required**: it is used to encrypt/decrypt data in the
    database, and commands such as `migrate` fail without it. The value above is only
    meant for local development, see
    [docs/config.adoc](docs/config.adoc) for details and
    [`django-searchable-encrypted-fields`](https://gitlab.com/guywillett/django-searchable-encrypted-fields#generating-encryption-keys)
    for how to generate keys.
  * See `compose.env.example` and [docs/config.adoc](docs/config.adoc) for the other
    available settings.
* Run `uv run manage.py migrate`
* Run `uv run manage.py createsuperuser`
* Run `uv run manage.py runserver 0:8000`

The project is now running at [localhost:8000](http://localhost:8000)


## Keeping Python requirements up to date

This repository uses [`uv`](https://docs.astral.sh/uv/) with `pyproject.toml` and `uv.lock` for dependency management.

1. Add new packages:
    * Production dependencies: `uv add <package>`
    * Development dependencies: `uv add --group dev <package>`
    * Production-only dependencies (e.g. `uwsgi`): `uv add --group prod <package>`

2. If you want to update dependencies to their newest versions, run:
    * `uv lock --upgrade`

3. To install Python requirements according to the lockfile, run:
    * `uv sync --locked`

**Note:** when updating dependencies, read the [dependency update checklist](docs/dependency-update.adoc) if there's anything you need to pay attention to.

## Code format

This project uses [Ruff](https://docs.astral.sh/ruff/) for code formatting and quality checking. It is run automatically via [`pre-commit`](https://pre-commit.com/), see below. If you want to use `ruff` outside of the pre-commit hooks, install it separately, for example with `uv tool install ruff` or `pip install ruff`.

Basic `ruff` commands:

* lint: `ruff check`
* apply safe lint fixes: `ruff check --fix`
* check formatting: `ruff format --check`
* format: `ruff format`

[`pre-commit`](https://pre-commit.com/) can be used to install and
run all the formatting tools as git hooks automatically before a
commit.


## Commit message format

New commit messages must adhere to the [Conventional Commits](https://www.conventionalcommits.org/)
specification, and line length is limited to 72 characters.

When [`pre-commit`](https://pre-commit.com/) is in use, [`commitlint`](https://github.com/conventional-changelog/commitlint)
checks new commit messages for the correct format.


## Running tests

The tests require a Postgres database to which to connect to. Here's one way to run the tests:

* Bring the service up with `docker compose up`. This also brings up the required Postgres server.
* Run tests within the Django container: `docker compose exec django pytest`.


## Issue tracking

* [Github issue list](https://github.com/City-of-Helsinki/open-city-profile/issues)


## API documentation

* [Generated GraphiQL documentation](https://profile-api.dev.hel.ninja/graphql/)


## Environments

* Dev: https://profile-api.dev.hel.ninja//graphql/
* Test: https://profile-api.test.hel.ninja//graphql/
* Staging: https://api.hel.fi/profiili-stage/graphql/
* Production: https://api.hel.fi/profiili/graphql/

## Anonymised Database dump

See [docs/database_dump.adoc](docs/database_dump.adoc).

## Dependent services

For a complete service the following additional components are also required:
* [Keycloak](https://www.keycloak.org/) is used as the authentication service
* [open-city-profile-ui](https://github.com/City-of-Helsinki/open-city-profile-ui/) provides UI
