# Production image for Cloud Run (docs/operations.md). One stateless container.

# --- stage 1: build the 3D bundle (docs/frontend.md → Build) ----------------------
# Node 24 LTS (Node 20 reached end of life in April 2026 — audit 2026-11-13).
FROM node:24-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
COPY static/models/ /app/static/models/
RUN npm run build && npm run budget

# --- stage 2: the Django app --------------------------------------------------------
FROM python:3.15-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=esports.settings.production

WORKDIR /app

# Hash-pinned lock (requirements.in → pip-compile): the image gets exactly what CI tested.
COPY requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

COPY . .
COPY --from=frontend /app/static/dist/ static/dist/

# Collect hashed static files at build time (SECRET_KEY not needed for this,
# but Django imports settings — pass harmless build-time values that satisfy the
# production fail-fast checks; the real values come from Secret Manager at run time).
RUN SECRET_KEY=build-only SIGNALS_SALT=build-only TURNSTILE_SECRET=build-only \
    TURNSTILE_SITE_KEY=build-only INTERNAL_TOKEN=build-only ALLOWED_HOSTS=build \
    SITE_BASE_URL=https://build.invalid CF_ORIGIN_TOKEN=build-only \
    python manage.py collectstatic --noinput

# Run as an unprivileged user, not root (audit 2026-11-13).
RUN useradd --system --uid 10001 --no-create-home app
USER app

# Cloud Run sends $PORT. Concurrency/workers per docs/operations.md sizing.
CMD exec gunicorn esports.wsgi:application \
    --bind 0.0.0.0:${PORT:-8080} --workers 2 --threads 4 --timeout 30
