# ==============================
FROM python:3.7-slim as appbase
# ==============================

ENV PYTHONUNBUFFERED 1

WORKDIR /app
RUN mkdir /entrypoint

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        gdal-bin \
        python3-gdal \
        netcat \
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/cache/apt/archives

COPY --chown=appuser:appuser requirements.txt /app/requirements.txt
RUN pip install -U pip \
    && pip install --no-cache-dir -r /app/requirements.txt

COPY docker-entrypoint.sh /entrypoint/docker-entrypoint.sh
ENTRYPOINT ["/entrypoint/docker-entrypoint.sh"]

# ==============================
FROM appbase as development
# ==============================

COPY --chown=appuser:appuser requirements-dev.txt /app/requirements-dev.txt
RUN pip install --no-cache-dir -r /app/requirements-dev.txt

ENV DEV_SERVER=1

COPY --chown=appuser:appuser . /app/

USER appuser

EXPOSE 8080/tcp

# ==============================
FROM appbase as production
# ==============================

COPY --chown=appuser:appuser . /app/

USER appuser

EXPOSE 8080/tcp
