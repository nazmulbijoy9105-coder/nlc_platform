#!/usr/bin/env bash
# Full PostgreSQL logical backup from Neon to S3.
# Requires a direct PostgreSQL connection string (not a transaction-pooler URL).
set -Eeuo pipefail

: "${NLC_BACKUP_DATABASE_URL:?Set NLC_BACKUP_DATABASE_URL to a direct Neon PostgreSQL URL}"
: "${S3_BACKUP_BUCKET:?Set S3_BACKUP_BUCKET to the bucket name}"
: "${AWS_REGION:?Set AWS_REGION explicitly}"

for command in pg_dump pg_restore aws sha256sum; do
  command -v "$command" >/dev/null 2>&1 || {
    echo "ERROR: required command not found: $command" >&2
    exit 1
  }
done

case "$NLC_BACKUP_DATABASE_URL" in
  postgresql://*|postgres://*) ;;
  *)
    echo "ERROR: NLC_BACKUP_DATABASE_URL must use postgresql:// or postgres:// (direct Neon endpoint)." >&2
    exit 1
    ;;
esac

BACKUP_DIR="${BACKUP_DIR:-${RUNNER_TEMP:-/tmp}/nlc-backups}"
S3_BACKUP_PREFIX="${S3_BACKUP_PREFIX:-database}"
S3_BACKUP_PREFIX="${S3_BACKUP_PREFIX#/}"
S3_BACKUP_PREFIX="${S3_BACKUP_PREFIX%/}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_NAME="nlc-postgres-${TIMESTAMP}.dump"
BACKUP_FILE="$BACKUP_DIR/$BACKUP_NAME"
CHECKSUM_FILE="${BACKUP_FILE}.sha256"
S3_KEY="${S3_BACKUP_PREFIX}/${BACKUP_NAME}"
S3_URI="s3://${S3_BACKUP_BUCKET}/${S3_KEY}"
CHECKSUM_URI="${S3_URI}.sha256"
UPLOAD_VERIFIED=0

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

cleanup() {
  if [[ "$UPLOAD_VERIFIED" == "1" ]]; then
    rm -f "$BACKUP_FILE" "$CHECKSUM_FILE"
  else
    echo "Backup/upload did not complete; local artifacts retained in $BACKUP_DIR" >&2
  fi
}
trap cleanup EXIT

echo "Creating PostgreSQL custom-format backup: $BACKUP_NAME"
pg_dump \
  --format=custom \
  --no-owner \
  --no-acl \
  --verbose \
  --file="$BACKUP_FILE" \
  --dbname="$NLC_BACKUP_DATABASE_URL"

[[ -s "$BACKUP_FILE" ]] || {
  echo "ERROR: pg_dump produced an empty archive" >&2
  exit 1
}

echo "Checking archive TOC before upload"
pg_restore --list "$BACKUP_FILE" >/dev/null

sha256sum "$BACKUP_FILE" > "$CHECKSUM_FILE"
LOCAL_BYTES="$(wc -c < "$BACKUP_FILE" | tr -d '[:space:]')"
LOCAL_SHA256="$(awk '{print $1}' "$CHECKSUM_FILE")"

echo "Uploading archive to $S3_URI"
aws s3 cp "$BACKUP_FILE" "$S3_URI" \
  --region "$AWS_REGION" \
  --storage-class STANDARD_IA \
  --sse AES256 \
  --metadata "sha256=$LOCAL_SHA256,created_utc=$TIMESTAMP,format=pg_custom"

echo "Uploading checksum to $CHECKSUM_URI"
aws s3 cp "$CHECKSUM_FILE" "$CHECKSUM_URI" \
  --region "$AWS_REGION" \
  --storage-class STANDARD_IA \
  --sse AES256

REMOTE_BYTES="$(aws s3api head-object \
  --bucket "$S3_BACKUP_BUCKET" \
  --key "$S3_KEY" \
  --region "$AWS_REGION" \
  --query ContentLength \
  --output text)"
REMOTE_SHA256="$(aws s3api head-object \
  --bucket "$S3_BACKUP_BUCKET" \
  --key "$S3_KEY" \
  --region "$AWS_REGION" \
  --query 'Metadata.sha256' \
  --output text)"

[[ "$REMOTE_BYTES" == "$LOCAL_BYTES" ]] || {
  echo "ERROR: S3 object size mismatch (local=$LOCAL_BYTES remote=$REMOTE_BYTES)" >&2
  exit 1
}
[[ "$REMOTE_SHA256" == "$LOCAL_SHA256" ]] || {
  echo "ERROR: S3 object metadata checksum mismatch" >&2
  exit 1
}

UPLOAD_VERIFIED=1
echo "SUCCESS: archive uploaded and S3 size/metadata verified."
echo "Archive: $S3_URI"
echo "SHA256:  $LOCAL_SHA256"
echo "NOTE: This verifies upload integrity and archive readability, not a database restore."
