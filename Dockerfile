# ==============================
FROM python:3.11-slim-bookworm as appbase
# ==============================

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY tools /tools
ENV PATH="/tools:${PATH}"

RUN groupadd -g 1000 appuser \
    && useradd -u 1000 -g appuser -ms /bin/bash appuser \
    && chown -R appuser:appuser /app

COPY --chown=appuser:appuser requirements*.txt /app/

RUN apt-install.sh \
    git \
    curl \
    build-essential \
    libpq-dev \
    gdal-bin \
    netcat-openbsd \
    python3-gdal \
    postgresql-client \
    && pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir --no-deps -r /app/requirements.txt \
    && pip install --no-cache-dir -r /app/requirements-prod.txt \
    && apt-cleanup.sh build-essential

COPY --chown=appuser:appuser docker-entrypoint.sh /entrypoint/docker-entrypoint.sh
ENTRYPOINT ["/entrypoint/docker-entrypoint.sh"]

# ==============================
FROM appbase as development
# ==============================

RUN apt-install.sh build-essential \
    && pip install --no-cache-dir -r /app/requirements-dev.txt \
    && apt-cleanup.sh build-essential

ENV DEV_SERVER=1

COPY --chown=appuser:appuser . /app/

USER appuser
EXPOSE 8080/tcp

# ==============================
FROM appbase as staticbuilder
# ==============================

ENV VAR_ROOT /app
COPY --chown=appuser:appuser . /app
RUN python manage.py collectstatic --noinput

# ==============================
FROM appbase as production
# ==============================

COPY --from=staticbuilder --chown=appuser:appuser /app/static /app/static
COPY --chown=appuser:appuser . /app/

USER appuser
EXPOSE 8080/tcp
