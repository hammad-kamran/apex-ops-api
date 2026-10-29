# syntax=docker/dockerfile:1

# ---- build stage: install dependencies into an isolated prefix ----
FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- runtime stage: minimal image, non-root user ----
FROM python:3.12-slim
ARG APP_VERSION=dev
ARG APEX_FAULT_READY=0
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_VERSION=${APP_VERSION} \
    APEX_FAULT_READY=${APEX_FAULT_READY}

LABEL org.opencontainers.image.title="apex-ops-api" \
      org.opencontainers.image.version="${APP_VERSION}"

RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY --from=builder /install /usr/local
# Source stays root-owned and read-only for the app user.
COPY app ./app
COPY wsgi.py gunicorn.conf.py ./

USER 10001:10001
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=2).status == 200 else 1)"]

CMD ["gunicorn", "-c", "gunicorn.conf.py", "wsgi:app"]
