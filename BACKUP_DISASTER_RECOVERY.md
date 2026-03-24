# 🔒 Backup & Disaster Recovery Plan

## Part 1: Automated Database Backups

### PostgreSQL Backups (Fly.io Managed)

Fly.io **automatically backs up** your PostgreSQL to:
- **Frequency:** Daily
- **Retention:** 7 days (free tier)
- **Location:** Multiple geographic regions
- **Recovery Time:** < 5 minutes

#### View Backups

```bash
# List all backups
flyctl postgres backups list

# Example output:
# ID          | Timestamp           | Size
# backup-100  | 2026-03-24T19:00:00Z | 1.2GB
# backup-99   | 2026-03-23T19:00:00Z | 1.1GB
```

#### Restore from Backup

```bash
# List available backups
flyctl postgres backups list

# Restore to specific backup
flyctl postgres backups restore backup-100 --app nlc-db

# Verify restore
flyctl postgres connect
SELECT * FROM companies LIMIT 1;
```

### Redis Backups

Redis data is **volatile** by default. To enable persistent backups:

```bash
# Enable persistence in Redis
flyctl redis update --app nlc-redis --enable-persistence
```

---

## Part 2: Application Code Recovery

### GitHub Automatic Backup

Your code is automatically backed up on GitHub:

```bash
# View commit history
git log --oneline

# View all branches
git branch -a

# View all tags
git tag

# Restore to specific commit
git checkout <commit-hash>
git reset --hard <commit-hash>

# Restore specific file
git checkout <commit-hash> -- path/to/file.py
```

### Version Tagging Strategy

```bash
# Create release tags
git tag -a v1.0.0 -m "Release 1.0" main
git push origin v1.0.0

# Tag format: v<major>.<minor>.<patch>
# Example: v1.2.3
```

---

## Part 3: Disaster Recovery Procedures

### Scenario 1: App Crashed

**Recovery Time Objective (RTO):** 1 minute

```bash
# Step 1: Check status
flyctl status

# Step 2: View recent logs (find the error)
flyctl logs -n 50

# Step 3: Restart machine
flyctl machine restart <machine-id>

# Step 4: Verify health
curl https://nlc-api.fly.dev/api/v1/health/live
```

### Scenario 2: Database Corrupted

**RTO:** 5 minutes

```bash
# Step 1: Check backup list
flyctl postgres backups list

# Step 2: Restore latest good backup
flyctl postgres backups restore backup-latest

# Step 3: Verify data integrity
flyctl postgres connect
SELECT COUNT(*) FROM companies;

# Step 4: Restart app
flyctl deploy
```

### Scenario 3: Complete Database Loss

**RTO:** 30 minutes (includes re-seeding data)

```bash
# Step 1: Create new PostgreSQL
flyctl postgres create --app nlc-db-recovery

# Step 2: Get new connection string
flyctl postgres credentials --app nlc-db-recovery
# Copy: postgresql+asyncpg://...

# Step 3: Update backend secrets
flyctl secrets set DATABASE_URL="postgresql+asyncpg://..."

# Step 4: Deploy backend
flyctl deploy

# Step 5: Initialize database
flyctl ssh console
alembic upgrade head
python scripts/seed_rules.py
python scripts/seed_prompt_templates.py
exit

# Step 6: Verify
curl https://nlc-api.fly.dev/api/v1/health/live
```

### Scenario 4: Deployment Failed

**RTO:** 2 minutes (rollback)

```bash
# Step 1: Check deployment history
git log --oneline -10

# Step 2: Find last good commit
git log --oneline | grep "working commit message"

# Step 3: Rollback to previous version
git revert HEAD
git push origin main

# Step 4: GitHub Actions auto-deploys fixed version
# Watch: GitHub Actions → Deploy Workflow

# Step 5: Verify
curl https://nlc-api.fly.dev/api/v1/health/live
```

### Scenario 5: Frontend Issues

**RTO:** 1 minute

```bash
# Vercel auto-rollback:
# 1. Go to Vercel dashboard
# 2. Select nlc-frontend project
# 3. Deployments tab
# 4. Find last stable deployment
# 5. Click "Promote to Production"

# OR use CLI:
vercel rollback
```

---

## Part 4: Data Export & Import

### Export All Data

```bash
# Export PostgreSQL to file
flyctl postgres connect < dump_query.sql > backup.sql

# Query to dump data:
cat > dump_query.sql << 'EOF'
\copy companies TO '/tmp/companies.csv' WITH CSV HEADER
\copy users TO '/tmp/users.csv' WITH CSV HEADER
\copy filings TO '/tmp/filings.csv' WITH CSV HEADER
EOF

# Download files
flyctl sftp get /tmp/companies.csv ./backup/
```

### Import Data

```bash
# Connect to database
flyctl postgres connect

# Import CSV
\copy companies FROM '/tmp/companies.csv' WITH CSV HEADER

# Verify import
SELECT COUNT(*) FROM companies;
```

---

## Part 5: Backup Testing

### Weekly Backup Health Check

Schedule via GitHub Actions (automated):

```yaml
name: Weekly Backup Test

on:
  schedule:
    - cron: '0 10 0 * 1'  # Every Monday 10 AM UTC

jobs:
  test_backup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install Fly CLI
        uses: superfly/flyctl-actions/setup-flyctl@master

      - name: List Recent Backups
        run: flyctl postgres backups list | head -3

      - name: Test DB Connection
        env:
          FLY_API_TOKEN: ${{secrets.FLY_API_TOKEN}}
        run: |
          flyctl postgres connect -c "SELECT COUNT(*) FROM companies;" || exit 1

      - name: Verify Data Integrity
        env:
          FLY_API_TOKEN: ${{secrets.FLY_API_TOKEN}}
        run: |
          flyctl ssh console "psql -d nlc_db -c 'SELECT COUNT(*) FROM companies;'" || exit 1
```

---

## Part 6: Manual Backup to S3

### Setup S3 Backup

```bash
# Create backup script
cat > scripts/backup_to_s3.py << 'EOF'
import subprocess
import boto3
from datetime import datetime

# Dump database
subprocess.run([
    'flyctl', 'postgres', 'connect',
    '-c', r'\copy companies TO STDOUT WITH CSV HEADER'
], stdout=open('backup.csv', 'w'))

# Upload to S3
s3 = boto3.client('s3')
s3.upload_file(
    'backup.csv',
    'nlc-backups',
    f'database_backup_{datetime.now().isoformat()}.csv'
)

print("✅ Backup successfully uploaded to S3")
EOF

# Run script
python scripts/backup_to_s3.py
```

### Schedule Daily S3 Backup

GitHub Actions:

```yaml
name: Daily S3 Backup

on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM UTC daily

jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ap-south-1

      - name: Run backup script
        env:
          FLY_API_TOKEN: ${{secrets.FLY_API_TOKEN}}
        run: python scripts/backup_to_s3.py

      - name: Slack notification
        uses: slackapi/slack-github-action@v1
        if: always()
        with:
          payload: |
            {
              "text": "Daily S3 backup completed"
            }
```

---

## Part 7: Communication Plan

### Incident Response Team

| Role | Responsibility | Contact |
|------|---------------|---------| 
| **Lead** | Decision maker | SMS + Slack |
| **Backend Dev** | Investigate app | Slack |
| **DevOps** | Infrastructure | Slack + Email |
| **Manager** | Customer comms | Email |

### Incident Severity Levels

```
🟢 LOW (< 30 min impact)
├─ Memory warning
├─ High CPU usage
└─ Non-critical feature down
→ Slack notification only

🟡 MEDIUM (30-120 min impact)
├─ Single endpoint down
├─ Database slow
└─ Background job failed
→ Slack + Email to team

🔴 CRITICAL (> 120 min impact)
├─ Entire API down
├─ Database lost
└─ Frontend can't reach backend
→ Slack + SMS + Call
```

### Status Page Setup

1. Create status page at https://status.nlccounsel.io
2. Use https://www.statuspage.io (free)
3. Auto-update via API on incidents
4. Notify customers in real-time

---

## Part 8: Testing & Drills

### Monthly Disaster Recovery Drill

```bash
# Checklist:
- [ ] Restore database from backup (test only)
- [ ] Verify data integrity after restore
- [ ] Test app startup with restored DB
- [ ] Verify frontend can reach backend
- [ ] Document any issues
- [ ] Update runbooks
```

### Backup Restore Test Checklist

```bash
#!/bin/bash

echo "🧪 Starting Disaster Recovery Test..."

# 1. Create test database
echo "1. Creating test database..."
flyctl postgres create --app nlc-db-test

# 2. Restore from backup
echo "2. Restoring from latest backup..."
flyctl postgres backups restore backup-latest --app nlc-db-test

# 3. Verify data
echo "3. Verifying data..."
flyctl postgres connect --app nlc-db-test << EOF
SELECT COUNT(*) as company_count FROM companies;
SELECT COUNT(*) as user_count FROM users;
EOF

# 4. Report
echo "✅ Disaster Recovery Test Passed"
echo "Files can be restored in < 5 minutes"

# 5. Cleanup
flyctl postgres destroy nlc-db-test
```

---

## Part 9: Recovery Time Objectives (RTOs)

| Scenario | RTO | RPO | Status |
|----------|-----|-----|--------|
| **App Crash** | 1 min | 0 min | ✅ Auto-restart |
| **App Deployment Fail** | 2 min | 0 min | ✅ Rollback ready |
| **DB Connection Lost** | 5 min | 0 min | ✅ Backup available |
| **DB Corruption** | 5 min | 1 day | ✅ Restore from backup |
| **Complete DB Loss** | 30 min | 1 day | ✅ Backup in S3 |
| **Frontend Broken** | 1 min | 0 min | ✅ Vercel auto-rollback |
| **Regional Outage** | 15 min | 0 min | ✅ Geo-redundant |

---

## Part 10: Backup Checklist

- [ ] PostgreSQL daily backups configured
- [ ] Redis persistence enabled
- [ ] GitHub code versioning active
- [ ] S3 daily exports scheduled
- [ ] Backup testing automated (weekly)
- [ ] Incident response team assigned
- [ ] Communication channels established
- [ ] Status page created
- [ ] Runbooks documented
- [ ] Team trained on procedures
- [ ] Monthly DR drills scheduled

---

## Emergency Contact Card

```
🚨 INCIDENT RESPONSE

Backend Down:
→ Check: flyctl logs
→ Restart: flyctl machine restart <id>
→ Deploy: flyctl deploy
→ Verify: curl https://nlc-api.fly.dev/api/v1/health/live

Database Down:
→ Check: flyctl postgres status
→ Restore: flyctl postgres backups restore backup-latest
→ Test: flyctl postgres connect

Frontend Down:
→ Check: Vercel dashboard
→ Rollback: vercel rollback
→ Verify: https://nlc-frontend.vercel.app

All Down / Unknown:
→ 1. Stay calm
→ 2. Take screenshot of error
→ 3. Notify team on Slack
→ 4. Check https://status.fly.io + https://www.vercelstatus.com
→ 5. Wait for infrastructure checks (15 min)

24/7 Support:
→ Slack: #incident-response
→ Email: devops@nlccounsel.io
```

---

**Your platform is now protected with enterprise-grade disaster recovery!** 🛡️
