# 📊 Fly.io Monitoring & Alerts Setup

## Part 1: Built-in Monitoring

### Fly.io Dashboard Metrics

```bash
# View in browser
flyctl dashboard

# Includes:
# - CPU usage ✅
# - Memory consumption ✅
# - Network I/O ✅
# - Request count ✅
# - Error rate ✅
```

### Health Checks (Auto-Configured)

The `fly.toml` includes health checks that automatically:

```yaml
[services.http_checks]
  enabled = true
  grace_period = "10s"        # Wait 10s before first check
  interval = "30s"            # Check every 30s
  method = "GET"
  path = "/api/v1/health/live"
  protocol = "http"
  restart_limit = 3           # Restart after 3 failures
  timeout = "5s"
```

**What it does:**
- If app doesn't respond to 3 consecutive health checks
- Fly.io automatically restarts the machine
- Keeps your API available 24/7 ✅

---

## Part 2: Application Logging

### View Application Logs

```bash
# Last 25 lines
flyctl logs

# Real-time stream
flyctl logs -f

# Stream specific level
flyctl logs -f --level=error

# Search logs
flyctl logs | grep "database"

# Export logs
flyctl logs > backup_logs.txt
```

### Log Levels in Your App

Set via `LOG_LEVEL` environment variable:

```bash
flyctl secrets set LOG_LEVEL="DEBUG"
flyctl deploy
```

Levels (in order):
- `DEBUG` - Most verbose (for development)
- `INFO` - General info (production default)
- `WARNING` - Important warnings
- `ERROR` - Error events only
- `CRITICAL` - Only critical failures

---

## Part 3: SMS/Email Alerts (Slack)

### Setup Slack Notifications

#### Step 1: Create Slack Webhook

1. Go to https://api.slack.com/apps
2. Click "Create New App"
3. Choose "From scratch"
4. Name: "Fly.io Alerts"
5. Select workspace
6. Go to "Incoming Webhooks"
7. Toggle "Activate Incoming Webhooks" ON
8. Click "Add New Webhook to Workspace"
9. Select channel: #deployments (or create new)
10. Copy webhook URL

#### Step 2: Store Webhook in GitHub Secrets

```bash
# In GitHub repo settings:
# Settings → Secrets and variables → Actions
# Create new secret:
#   Name: SLACK_WEBHOOK_DEPLOYMENTS
#   Value: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

#### Step 3: Alert on Deployment

GitHub Actions already configured to send Slack messages on:
- ✅ Successful deployment
- ❌ Failed deployment

Messages include:
- Commit hash
- Branch name
- Deployment time
- Link to logs

### Manual Slack Alert Example

```bash
#!/bin/bash
# Alert on errors
flyctl logs -f | while read line; do
  if [[ $line == *"ERROR"* ]]; then
    curl -X POST -H 'Content-type: application/json' \
      --data "{\"text\":\"🚨 NLC Platform Error: $line\"}" \
      YOUR_SLACK_WEBHOOK_URL
  fi
done
```

---

## Part 4: Uptime Monitoring

### Use Uptimerobot (Free Tier)

1. Go to https://uptimerobot.com
2. Sign up (free)
3. Add new monitor:
   - Type: HTTP(S)
   - URL: https://nlc-api.fly.dev/api/v1/health/live
   - Interval: Every 5 minutes
   - Add notification: Slack/Email

### What it monitors:
- ✅ API endpoint reachability
- ✅ Response time (SLA tracking)
- ✅ SSL certificate validity
- ✅ Status page updates

---

## Part 5: Database Monitoring

### PostgreSQL Health

```bash
# Connect to database
flyctl postgres connect

# Check connection status
SELECT NOW();

# Check disk usage
SELECT pg_size_pretty(pg_total_relation_size('public'));

# Check active connections
SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;

# Exit
\q
```

### Redis Health

```bash
# Connect to Redis
flyctl redis connect

# Check status
info

# Check memory usage
info memory

# Exit
quit
```

### Automated Database Backup Check

```bash
# View backup status
flyctl postgres backups list

# Last backup timestamp
flyctl postgres backups list | head -1

# Verify restore capability
flyctl postgres backup --help
```

---

## Part 6: Performance Metrics

### Monitor Key Metrics

```bash
# CPU usage over time
flyctl logs | grep "memory\|cpu"

# Request latency
flyctl logs | grep "response_time"

# Error rate
flyctl logs | grep "ERROR" | wc -l
```

### Create Custom Alerts

Create script at `.github/scripts/check_health.sh`:

```bash
#!/bin/bash

# Check API health
if ! curl -f https://nlc-api.fly.dev/api/v1/health/live; then
  echo "❌ API is down!"
  # Send alert
  # Send to Slack, email, etc.
  exit 1
fi

# Check database
if flyctl postgres connect -c "SELECT 1" > /dev/null; then
  echo "✅ Database is healthy"
else
  echo "❌ Database is down!"
  exit 1
fi

# Check Redis
if flyctl redis connect -c "PING" > /dev/null; then
  echo "✅ Redis is healthy"
else
  echo "❌ Redis is down!"
  exit 1
fi

echo "✅ All systems operational"
```

Run weekly via GitHub Actions:

```yaml
name: Weekly Health Check

on:
  schedule:
    - cron: '0 9 * * 1'  # Every Monday 9 AM UTC

jobs:
  health_check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: bash .github/scripts/check_health.sh
```

---

## Part 7: Alerts & Notifications

### Configure Alert Thresholds

Add to `fly.toml`:

```toml
[alerts]
  threshold_cpu_usage = 80          # Alert if CPU > 80%
  threshold_memory_usage = 75        # Alert if memory > 75%
  threshold_error_rate = 5           # Alert if error rate > 5%
  threshold_response_time = 1000     # Alert if avg response > 1s
```

### Notification Channels

| Channel | Setup Time | Cost | Reliability |
|---------|-----------|------|-------------|
| **Slack** | 5 min | Free | 99.9% |
| **Email** | 2 min | Free | 95% |
| **SMS** | 15 min | ~$0.01/msg | 99.5% |
| **PagerDuty** | 10 min | $10-15/mo | 99.99% |

### Slack Alert Messages Example

```json
{
  "text": "🚨 Critical Alert: NLC API Memory Usage High",
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*NLC Platform Alert*\n*Severity:* 🔴 Critical\n*Issue:* Memory usage at 89%\n*Action:* Consider scaling up\n*Time:* 2026-03-24 19:30 UTC"
      }
    },
    {
      "type": "actions",
      "elements": [
        {
          "type": "button",
          "text": {"type": "plain_text", "text": "View Logs"},
          "url": "https://fly.io/dashboard/logs"
        }
      ]
    }
  ]
}
```

---

## Part 8: Dashboard Setup

### Create Monitoring Dashboard

Access via:
```
https://fly.io/dashboard
→ Select nlc-api app
→ Monitor tab
```

Shows real-time:
- ✅ Request count
- ✅ Error rate
- ✅ Response times
- ✅ CPU/Memory usage
- ✅ Network traffic

### Export Metrics to External Service

```bash
# Prometheus (free)
flyctl metrics summary

# Datadog integration (9/month)
# Configure in fly.toml

# New Relic integration (100/month)
# Configure in fly.toml
```

---

## Part 9: Runbooks

### Emergency Response Flowchart

```
API Down?
├─ Check Fly.io Status
│  └─ https://status.fly.io
├─ View Recent Logs
│  └─ flyctl logs -n 100
├─ Check Health Status
│  └─ flyctl status
└─ Resolve
   ├─ Restart machine: flyctl machine restart <machine-id>
   ├─ Redeploy: flyctl deploy
   └─ Rollback: git revert & flyctl deploy

Database Connection Error?
├─ Check PostgreSQL Status
│  └─ flyctl postgres status
├─ Verify Connection String
│  └─ flyctl secrets list | grep DATABASE_URL
├─ Test Connection
│  └─ flyctl postgres connect
└─ Resolve
   ├─ Restart: flyctl machine restart postgres-xxx
   ├─ Restore: flyctl postgres backups restore

High Memory Usage?
├─ Check Memory Limits
│  └─ flyctl machine list
├─ Identify Memory Leak
│  └─ flyctl logs | grep "memory"
└─ Resolve
   ├─ Reduce workers: Change --workers 2 → 1
   ├─ Increase memory: fly.toml memory = 1024mb
   └─ Redeploy
```

---

## Summary Monitoring Checklist

- [ ] Health checks enabled (auto-restart if down)
- [ ] Slack webhook configured (deployment alerts)
- [ ] Uptime monitor enabled (5 min checks)
- [ ] Database backups scheduled
- [ ] Redis monitoring active
- [ ] GitHub Actions alerts configured
- [ ] Weekly health check script enabled
- [ ] Team knows escalation procedure
- [ ] Runbook documented
- [ ] Contact list created

**🎯 Your platform is now monitored 24/7!**
