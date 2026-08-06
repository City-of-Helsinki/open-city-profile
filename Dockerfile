# ==============================
FROM registry.access.redhat.com/ubi9/python-312 AS appbase
# ==============================

# Branch or tag used to pull python-uwsgi-common.
ARG UWSGI_COMMON_REF=main

COPY --from=ghcr.io/astral-sh/uv:0.12.2@sha256:069a51314a7bb6031777a9273205fe1b0b19e914ef418207d1338b268df641dd /uv /uvx /usr/local/bin/

USER root
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_PROJECT_ENVIRONMENT=/opt/app-root \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    UV_PYTHON_DOWNLOADS=never
ENV PATH="/opt/app-root/bin:$PATH"

COPY pyproject.toml uv.lock .

RUN dnf update -y \
    && dnf install -y nmap-ncat \
    && dnf clean all \
    && uv sync --locked --no-dev --group prod

# Build and copy specific python-uwsgi-common files.
ADD https://github.com/City-of-Helsinki/python-uwsgi-common/archive/${UWSGI_COMMON_REF}.tar.gz /usr/src/
RUN mkdir -p /usr/src/python-uwsgi-common && \
    tar --strip-components=1 -xzf /usr/src/${UWSGI_COMMON_REF}.tar.gz -C /usr/src/python-uwsgi-common && \
    mkdir -p /usr/local/etc && \
    cp /usr/src/python-uwsgi-common/uwsgi-base.ini /usr/local/etc/ && \
    uwsgi --build-plugin /usr/src/python-uwsgi-common && \
    rm -rf /usr/src/${UWSGI_COMMON_REF}.tar.gz && \
    rm -rf /usr/src/python-uwsgi-common && \
    uwsgi --build-plugin https://github.com/City-of-Helsinki/uwsgi-sentry && \
    mkdir -p /usr/local/lib/uwsgi/plugins && \
    mv escape_json_plugin.so sentry_plugin.so /usr/local/lib/uwsgi/plugins

COPY docker-entrypoint.sh /entrypoint/docker-entrypoint.sh
ENTRYPOINT ["/entrypoint/docker-entrypoint.sh"]

# ==============================
FROM appbase AS development
# ==============================

RUN groupadd -g 1000 appuser \
    && useradd -u 1000 -g appuser -ms /bin/bash appuser \
    && chown -R appuser:root /app

RUN uv sync --locked --group prod

ENV DEV_SERVER=1

COPY --chown=appuser:root . .

USER appuser
EXPOSE 8080/tcp

# ==============================
FROM appbase AS staticbuilder
# ==============================

ENV VAR_ROOT=/app
COPY . .
RUN python manage.py collectstatic --noinput

# ==============================
FROM appbase AS production
# ==============================

COPY --from=staticbuilder /app/static /app/static
COPY . .

USER default
EXPOSE 8080/tcp
