# Production image for Cloud Run (docs/operations.md). One stateless container.

# --- stage 1: build the 3D bundle (docs/frontend.md → Build) ----------------------
FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build && npm run budget

# --- stage 2: the Django app --------------------------------------------------------
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=esports.settings.production

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=frontend /app/static/dist/ static/dist/

# Collect hashed static files at build time (SECRET_KEY not needed for this,
# but Django imports settings — pass harmless build-time values).
RUN SECRET_KEY=build-only SIGNALS_SALT=build-only TURNSTILE_SECRET=build-only \
    INTERNAL_TOKEN=build-only ALLOWED_HOSTS=build \
    python manage.py collectstatic --noinput

# Cloud Run sends $PORT. Concurrency/workers per docs/operations.md sizing.
CMD exec gunicorn esports.wsgi:application \
    --bind 0.0.0.0:${PORT:-8080} --workers 2 --threads 4 --timeout 30
