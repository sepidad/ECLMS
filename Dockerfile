# ECLMS API image (modular monolith, Python 3.11).
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps (none required at runtime beyond pip/build for bcrypt)
COPY pyproject.toml backend/README.md ./
COPY . .

RUN pip install --no-cache-dir -e . \
    && useradd --create-home --shell /usr/sbin/nologin eclms \
    && mkdir -p /app/var/storage && chown -R eclms:eclms /app/var

USER eclms

EXPOSE 8000

# Run schema migrations, then start uvicorn.  --proxy-headers honours the
# X-Forwarded-* headers set by the TLS-terminating reverse proxy.
CMD ["sh", "-c", "alembic upgrade head && uvicorn backend.main:app --host 0.0.0.0 --port 8000 --proxy-headers --no-server-header"]
