# STAGE 1: builder
FROM python:3.11-slim-bookworm AS builder
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libffi-dev libssl-dev libpq-dev \
    libmagic1 libmagic-dev libpango-1.0-0 libpangoft2-1.0-0 \
    libharfbuzz0b libharfbuzz-icu0 libharfbuzz-subset0 libfontconfig1 libcairo2 \
    libgdk-pixbuf2.0-0 libxml2-dev libxslt1-dev shared-mime-info \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
# requirements.txt is the complete, exactly pinned set verified by the dependency
# audit; install it as-is so the image never resolves anything the audit did not see.
RUN pip install --upgrade "pip==24.0" setuptools wheel && \
    pip install --no-cache-dir --no-deps -r requirements.txt

# STAGE 2: runtime-base
FROM python:3.11-slim-bookworm AS runtime-base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TZ=UTC \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app" \
    HOME="/tmp" \
    XDG_CACHE_HOME="/tmp/nlc_cache" \
    FONTCONFIG_PATH="/etc/fonts"

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 libmagic1 libpango-1.0-0 libpangoft2-1.0-0 \
    libharfbuzz0b libharfbuzz-icu0 libfontconfig1 fontconfig \
    libcairo2 libgdk-pixbuf2.0-0 libxml2 libxslt1.1 \
    shared-mime-info fonts-liberation fonts-noto curl tzdata \
    && apt-get clean && rm -rf /var/lib/apt/lists/* && fc-cache -fv

COPY --from=builder /opt/venv /opt/venv

# Fail the production image build unless the exact Pillow payload contains the
# fixed bundled Brotli decoder and common library. Load common globally first
# so the decoder's private dependency resolves from pillow.libs.
RUN python - <<'PY'
import ctypes
import re
from pathlib import Path
import PIL

assert PIL.__version__ == "13.0.0", f"Unexpected Pillow version: {PIL.__version__}"
libdir = Path(PIL.__file__).resolve().parent.parent / "pillow.libs"
libraries = sorted(
    path for path in libdir.glob("libbrotli*")
    if "brotlidec" in path.name or "brotlicommon" in path.name
)
decoder = next((path for path in libraries if "brotlidec" in path.name), None)
common = next((path for path in libraries if "brotlicommon" in path.name), None)
assert decoder is not None, "Bundled Brotli decoder library missing"
assert common is not None, "Bundled Brotli common library missing"
for path in (decoder, common):
    match = re.search(r"\.so\.(\d+)\.(\d+)\.(\d+)$", path.name)
    assert match, f"Unversioned or unexpected bundled Brotli library: {path.name}"
    version = tuple(map(int, match.groups()))
    assert version >= (1, 2, 1), f"Vulnerable bundled Brotli library: {path.name}"
    print(f"Verified {path.name}: {version}")

ctypes.CDLL(str(common), mode=ctypes.RTLD_GLOBAL)
decoder_library = ctypes.CDLL(str(decoder))
decoder_library.BrotliDecoderVersion.restype = ctypes.c_uint32
encoded = decoder_library.BrotliDecoderVersion()
runtime_version = (encoded >> 24, (encoded >> 12) & 0xFFF, encoded & 0xFFF)
assert runtime_version >= (1, 2, 1), f"Loaded Brotli decoder is too old: {runtime_version}"
print(f"Verified loaded BrotliDecoderVersion: {runtime_version}")
PY

RUN groupadd --gid 1001 nlc && \
    useradd --uid 1001 --gid 1001 --no-create-home --shell /bin/sh nlc && \
    mkdir -p /tmp/nlc_cache/fontconfig && \
    chown -R nlc:nlc /tmp/nlc_cache && \
    chmod 700 /tmp/nlc_cache /tmp/nlc_cache/fontconfig

WORKDIR /app
RUN mkdir -p /app/static/fonts /app/templates/pdf /tmp/nlc_pdfs && \
    chown -R nlc:nlc /app /tmp/nlc_pdfs

COPY --chown=nlc:nlc . /app/
USER nlc

# STAGE 3: worker
FROM runtime-base AS worker
CMD ["celery", "-A", "app.worker.celery_app", "worker", "--loglevel=info"]

# STAGE 4: beat
FROM runtime-base AS beat
CMD ["celery", "-A", "app.worker.celery_app", "beat", "--loglevel=info", "--scheduler", "redbeat.RedBeatScheduler"]

# STAGE 5: api — MUST BE LAST (Render default target)
FROM runtime-base AS api
# Render injects PORT (default 10000). Keep the local fallback aligned.
ENV PORT=10000
EXPOSE 10000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT:-10000}/api/v1/health/live" || exit 1

# Schema changes are applied by the CI-gated migration step before Render deploy.
# The API container never receives the privileged migration credential.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port \"${PORT:-10000}\""]
