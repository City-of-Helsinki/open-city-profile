# ==============================
FROM registry.access.redhat.com/ubi9/python-312 AS appbase
# ==============================

USER root
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN dnf update -y \
    && dnf install -y nmap-ncat \
    && dnf clean all \
    && pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r /app/requirements.txt

COPY docker-entrypoint.sh /entrypoint/docker-entrypoint.sh
ENTRYPOINT ["/entrypoint/docker-entrypoint.sh"]

# ==============================
FROM appbase AS development
# ==============================

RUN groupadd -g 1000 appuser \
    && useradd -u 1000 -g appuser -ms /bin/bash appuser \
    && chown -R appuser:root /app

COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r /app/requirements-dev.txt

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
