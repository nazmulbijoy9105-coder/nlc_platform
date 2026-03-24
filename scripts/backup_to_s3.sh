#!/bin/bash
# =============================================================================
# Backup to S3 Script
# Automatically exports PostgreSQL data to S3 for long-term archival
# =============================================================================

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TIMESTAMP=$(date -u +%Y-%m-%d_%H-%M-%S)
BACKUP_DIR="/tmp/nlc_backups"
BACKUP_FILE="$BACKUP_DIR/nlc_backup_$TIMESTAMP.sql"
BACKUP_TARBALL="$BACKUP_DIR/nlc_backup_$TIMESTAMP.tar.gz"

echo "🔄 Starting NLC Platform Backup to S3..."
echo "⏰ Timestamp: $TIMESTAMP"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Export PostgreSQL database
echo "📦 Exporting PostgreSQL database..."
flyctl ssh console --app nlc-api --command "pg_dump -U nlc_user nlc_db" > "$BACKUP_FILE"

if [ ! -f "$BACKUP_FILE" ]; then
  echo "❌ Failed to create backup file"
  exit 1
fi

FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "✅ PostgreSQL backup created: $FILE_SIZE"

# Compress backup
echo "🗜️  Compressing backup..."
tar -czf "$BACKUP_TARBALL" -C "$BACKUP_DIR" "nlc_backup_$TIMESTAMP.sql"
COMPRESSED_SIZE=$(du -h "$BACKUP_TARBALL" | cut -f1)
echo "✅ Backup compressed: $COMPRESSED_SIZE"

# Upload to S3
echo "📤 Uploading to S3..."
aws s3 cp "$BACKUP_TARBALL" "s3://nlc-backups/database/nlc_backup_$TIMESTAMP.tar.gz" \
  --storage-class STANDARD_IA \
  --metadata "created=$TIMESTAMP,type=postgresql_database" \
  --region ap-south-1

if [ $? -eq 0 ]; then
  echo "✅ Successfully uploaded to S3"
else
  echo "❌ Failed to upload to S3"
  exit 1
fi

# List recent backups
echo ""
echo "📋 Recent backups in S3:"
aws s3 ls s3://nlc-backups/database/ --region ap-south-1 --recursive | tail -5

# Cleanup local backup
echo ""
echo "🧹 Cleaning up local files..."
rm -f "$BACKUP_FILE" "$BACKUP_TARBALL"

# Verification
echo ""
echo "✅ Backup Complete!"
echo "📊 Summary:"
echo "  - Backup timestamp: $TIMESTAMP"
echo "  - Compressed size: $COMPRESSED_SIZE"
echo "  - Location: s3://nlc-backups/database/nlc_backup_$TIMESTAMP.tar.gz"
echo "  - Retention: STANDARD_IA (30+ days cheap storage)"

exit 0
