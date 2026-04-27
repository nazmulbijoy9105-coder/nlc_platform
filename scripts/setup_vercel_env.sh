#!/usr/bin/env bash
# =============================================================================
# NLC Platform — Vercel Environment Variable Setup Script
# Run this once after creating the Vercel project to configure all env vars.
#
# Usage:
#   VERCEL_TOKEN=your_token VERCEL_PROJECT_ID=your_project_id bash scripts/setup_vercel_env.sh
#
# Or set these env vars first:
#   export VERCEL_TOKEN=...
#   export VERCEL_ORG_ID=...
#   export VERCEL_PROJECT_ID=...
# =============================================================================
set -euo pipefail

: "${VERCEL_TOKEN:?VERCEL_TOKEN must be set}"
: "${VERCEL_PROJECT_ID:?VERCEL_PROJECT_ID must be set}"

VERCEL_ORG_ID="${VERCEL_ORG_ID:-}"
PROJECT_URL="https://api.vercel.com/v9/projects/${VERCEL_PROJECT_ID}/env"

# Helper: add or update a Vercel env var
set_env() {
  local key="$1" value="$2" target="${3:-production,preview,development}"
  echo "  Setting $key..."
  curl -s -X POST "$PROJECT_URL" \
    -H "Authorization: Bearer $VERCEL_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"key\": \"$key\",
      \"value\": \"$value\",
      \"type\": \"encrypted\",
      \"target\": [\"production\", \"preview\", \"development\"]
    }" > /dev/null
}

echo "=== Configuring Vercel Environment Variables ==="
echo "Project: $VERCEL_PROJECT_ID"

# ── Database ─────────────────────────────────────────────────────────
set_env "DATABASE_URL" \
  "postgresql+asyncpg://neondb_owner:npg_c6sEDg3PXFAS@ep-winter-forest-aozont4u-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb?ssl=require"

# ── JWT / Auth ────────────────────────────────────────────────────────
set_env "JWT_SECRET_KEY" \
  "248a7d73134f6bf0bcd311a948e5bfe0bb1ea39705e6800613b6bea641f7d9ad2a590f1314f06f7c434e74d3f3bd5817d96d3d99a26fecaaee293af70eaf6215"

set_env "TOTP_ENCRYPTION_KEY" \
  "f53c035b2e32e0a57ff9c8c2561d43fca70fe0ae33999a4ea245016a6dcf8e98"

# ── App Config ────────────────────────────────────────────────────────
set_env "ENVIRONMENT"       "production"
set_env "CELERY_ENABLED"    "false"
set_env "PYTHONPATH"        "."
set_env "AI_PROVIDER"       "local_llm"
set_env "LOG_LEVEL"         "INFO"

# ── CORS ─────────────────────────────────────────────────────────────
set_env "ALLOWED_ORIGINS" \
  "https://nlc-frontend.vercel.app,https://nlc-frontend.coonect.vercel.app,http://localhost:3000"

# ── Redis (disabled in serverless) ───────────────────────────────────
set_env "REDIS_URL" "redis://localhost:6379/0"

# ── AWS (optional — document storage) ────────────────────────────────
set_env "AWS_REGION"        "ap-southeast-1"
set_env "S3_BUCKET_NAME"    "nlc-documents"
set_env "S3_BACKUP_BUCKET"  "nlc-backups"

# ── Email ─────────────────────────────────────────────────────────────
set_env "EMAIL_FROM" "compliance@neumlexcounsel.com"

echo ""
echo "=== Done! All environment variables configured. ==="
echo ""
echo "Next: trigger a deployment with:"
echo "  vercel deploy --prod --token=\$VERCEL_TOKEN --yes"
