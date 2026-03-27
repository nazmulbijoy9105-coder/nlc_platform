# ═══════════════════════════════════════════════════════════════════════
# NEUM LEX COUNSEL — Backend Dockerfile (Venv Optimized)
# ═══════════════════════════════════════════════════════════════════════

# STAGE 1: builder
FROM python:3.11-slim-bookworm AS builder
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libffi-dev libssl-dev libpq-dev \
    libmagic1 libmagic-dev libpango-1.0-0 libpangoft2-1.0-0 \
    libharfbuzz0b libharfbuzz-icu0 libfontconfig1 libcairo2 \
    libgdk-pixbuf2.0-0 libxml2-dev libxslt1-dev shared-mime-info \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --upgrade "pip==24.0" setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# STAGE 2: runtime-base
FROM python:3.11-slim-bookworm AS runtime-base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TZ=UTC \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app"

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 libmagic1 libpango-1.0-0 libpangoft2-1.0-0 \
    libharfbuzz0b libharfbuzz-icu0 libfontconfig1 fontconfig \
    libcairo2 libgdk-pixbuf2.0-0 libxml2 libxslt1.1 \
    shared-mime-info fonts-liberation fonts-noto curl tzdata \
    && apt-get clean && rm -rf /var/lib/apt/lists/* && fc-cache -fv

COPY --from=builder /opt/venv /opt/venv

RUN groupadd --gid 1001 nlc && \
    useradd --uid 1001 --gid 1001 --no-create-home --shell /bin/sh nlc

WORKDIR /app
RUN mkdir -p /app/static/fonts /app/templates/pdf /tmp/nlc_pdfs && \
    chown -R nlc:nlc /app /tmp/nlc_pdfs

COPY --chown=nlc:nlc . /app/
USER nlc

# STAGE 3: api
FROM runtime-base AS api
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
