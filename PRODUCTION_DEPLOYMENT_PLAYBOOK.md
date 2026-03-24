# 🎯 NLC PLATFORM - PRODUCTION DEPLOYMENT PLAYBOOK

## 📋 Table of Contents

1. [Pre-Deployment (5 min)](#pre-deployment)
2. [GitHub Secrets Setup (5 min)](#github-secrets)
3. [Backend Deployment to Fly.io (20 min)](#backend-deployment)
4. [Frontend Deployment to Vercel (10 min)](#frontend-deployment)
5. [Integration & Testing (10 min)](#integration)
6. [Monitoring & Alerts Setup (5 min)](#monitoring)
7. [Verification Checklist](#verification)

---

## Pre-Deployment

### ✅ Files Already Created For You

```
✅ fly.toml                              (Production config)
✅ .github/workflows/deploy-fly.yml      (Auto-deploy on push)
✅ .github/workflows/backup-health-check.yml   (Weekly health check)
✅ .github/workflows/daily-s3-backup.yml       (Daily backups)
✅ FLY_DEPLOYMENT_GUIDE.md              (Complete setup guide)
✅ FLY_MONITORING_SETUP.md              (Monitoring & alerts)
✅ BACKUP_DISASTER_RECOVERY.md          (DR procedures)
✅ QUICK_START_GUIDE.md                 (5-step guide)
✅ scripts/backup_to_s3.sh              (Manual backup tool)
✅ scripts/deployment_checklist.sh      (Pre-flight check)
```

### 🔍 Pre-Flight Check

Run this to verify local setup:

```bash
cd /workspaces/nlc_platform
bash scripts/deployment_checklist.sh
```

Expected output:
```
✅ fly.toml exists
✅ Dockerfile exists
✅ requirements.txt exists
✅ Backend deployment workflow exists
✅ Health check workflow exists
✅ S3 backup workflow exists
✅ Deployment guide exists
✅ Monitoring documentation exists
✅ Disaster recovery plan exists
✅ .env file is gitignored
```

---

## GitHub Secrets

### Step 1: Get Your Fly.io Token

```bash
# From your LOCAL machine (with flyctl installed):
flyctl auth token
```

Copy the token → GitHub repo → Settings → Secrets and variables → Actions

### Step 2: Add These 5 Secrets

| Secret Name | Value | Where to Get |
|------------|-------|-------------|
| `FLY_API_TOKEN_PROD` | Output from `flyctl auth token` | Run locally |
| `AWS_ACCESS_KEY_ID` | Your AWS IAM key | AWS Console |
| `AWS_SECRET_ACCESS_KEY` | Your AWS secret | AWS Console |
| `VERCEL_TOKEN` | Your Vercel API token | Vercel Settings |
| `SLACK_WEBHOOK_DEPLOYMENTS` | Slack webhook URL | Slack API (optional) |

### Instructions to Add Secrets

1. Go to GitHub: https://github.com/nazmulbijoy9105-coder/nlc_platform
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each of the 5 secrets above
5. Verify all secrets appear in the list

---

## Backend Deployment

### Step 1: Install Fly CLI (2 min)

**On your local machine:**

```bash
# macOS
brew install flyctl

# Linux
curl -L https://fly.io/install.sh | sh

# Windows
choco install flyctl
```

Verify:
```bash
flyctl version
# Should output: v0.1.x or similar
```

### Step 2: Log In to Fly.io (2 min)

```bash
flyctl auth login
# Opens browser → Sign in with GitHub
# Generates auth token automatically
```

### Step 3: Create Fly App (2 min)

```bash
cd /workspaces/nlc_platform

flyctl launch

# Follow prompts:
# - App name: nlc-api
# - Region: sin (Singapore)
# - PostgreSQL: I'll add it myself (choose this)
# - Redis: I'll add it myself (choose this)
# - Deploy now?: NO
```

This creates your `fly.toml` (already provided).

### Step 4: Create PostgreSQL (3 min)

```bash
flyctl postgres create

# When prompted:
# - App name: nlc-db
# - Choose region: sin (same as api)
# - Admin username: nlc_user
# - Generate password: (let Fly generate it)
# - Initial database: nlc_db
```

**Save the connection string!** You'll see output like:

```
postgresql+asyncpg://nlc_user:PASSWORD@nlc-db.internal:5432/nlc_db
```

### Step 5: Create Redis (2 min)

```bash
flyctl redis create

# When prompted:
# - App name: nlc-redis
# - Choose region: sin (same as api)
# - Eviction: Enable (auto cleanup)
# - Replication: Disable (free tier)
```

**Save the connection string!** You'll see:

```
redis://default:PASSWORD@nlc-redis.internal:6379
```

### Step 6: Set All Secrets (3 min)

```bash
# Generate secure keys
JWT_SECRET=$(openssl rand -base64 32)
TOTP_KEY=$(openssl rand -base64 32)

# Set runtime secrets
flyctl secrets set \
  DATABASE_URL="postgresql+asyncpg://nlc_user:PASSWORD@nlc-db.internal:5432/nlc_db" \
  REDIS_URL="redis://default:PASSWORD@nlc-redis.internal:6379" \
  JWT_SECRET_KEY="$JWT_SECRET" \
  TOTP_ENCRYPTION_KEY="$TOTP_KEY" \
  ENVIRONMENT="production" \
  LOG_LEVEL="INFO" \
  ANTHROPIC_API_KEY="sk-..." \
  AWS_ACCESS_KEY_ID="..." \
  AWS_SECRET_ACCESS_KEY="..." \
  ALLOWED_ORIGINS="https://localhost:3000,http://localhost:3000"

# Verify
flyctl secrets list
```

### Step 7: Deploy Backend (5 min)

```bash
# Deploy!
flyctl deploy

# Watch logs
flyctl logs -f

# Should see:
# - Building Docker image...
# - Pushing image...
# - Starting application...
# - Application startup complete
```

**Wait for success message** (2-5 minutes)

### Step 8: Initialize Database (3 min)

```bash
# SSH into container
flyctl ssh console

# Run migrations
alembic upgrade head

# Seed rules
python scripts/seed_rules.py

# Seed templates
python scripts/seed_prompt_templates.py

# Exit
exit
```

### Step 9: Verify Backend (1 min)

```bash
# Get app URL
flyctl info

# Show addresses - copy the HTTPS URL

# Test endpoint
curl https://nlc-api.fly.dev/api/v1/health/live

# Expected response:
# {"status":"ok"}
```

✅ **Backend is live at: https://nlc-api.fly.dev**

---

## Frontend Deployment

### Step 1: Install Vercel CLI (2 min)

```bash
npm install -g vercel
```

### Step 2: Clone Frontend (2 min)

```bash
cd ~/
git clone https://github.com/nazmulbijoy9105-coder/nlc_frontend
cd nlc_frontend
```

### Step 3: Link to Vercel (3 min)

```bash
vercel link

# When prompted:
# - Set up new project?: YES
# - Project name: nlc-frontend
# - Framework: Next.js (auto-detected)
# - Build command: npm run build (auto)
# - Install dependencies: NO (already mentioned in package.json)
```

### Step 4: Set Environment Variable (2 min)

```bash
# Add backend API URL
vercel env add NEXT_PUBLIC_API_URL

# When prompted:
# Value: https://nlc-api.fly.dev
# Environment: Production
```

### Step 5: Deploy (3 min)

```bash
vercel --prod

# Wait for:
# - Installing dependencies...
# - Building...
# - Deploying...
# - ✓ Production: https://nlc-frontend.vercel.app
```

✅ **Frontend is live at: https://nlc-frontend.vercel.app**

---

## Integration & Testing

### Step 1: Update CORS

Backend must whitelist frontend:

```bash
flyctl secrets set \
  ALLOWED_ORIGINS="https://nlc-frontend.vercel.app,http://localhost:3000"

# Redeploy for changes to take effect
flyctl deploy
```

### Step 2: Test Integration

1. **Open frontend:**
   ```
   https://nlc-frontend.vercel.app
   ```

2. **Open DevTools:**
   - Press F12
   - Go to Network tab
   - Go to Console tab

3. **Try logging in:**
   - Watch Network tab
   - Should see requests going to `nlc-api.fly.dev`
   - No CORS errors ✅

4. **Check API directly:**
   ```bash
   curl -X POST https://nlc-api.fly.dev/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"user@test.com","password":"password"}'
   ```

### Step 3: Test Database

```bash
curl https://nlc-api.fly.dev/api/v1/companies \
  -H "Authorization: Bearer YOUR_TOKEN"

# Should return list of companies (if already created)
```

✅ **Integration complete!**

---

## Monitoring & Alerts Setup

### Step 1: Connect Slack (1 min)

1. Go to https://api.slack.com/apps
2. Create New App → From scratch
3. Name: "NLC Alerts"
4. Add to workspace
5. Incoming Webhooks → Activate → Add webhook
6. Copy webhook URL
7. Add to GitHub secret: `SLACK_WEBHOOK_DEPLOYMENTS`

### Step 2: Create Uptime Monitor (2 min)

1. Go to https://uptimerobot.com
2. Sign up (free)
3. Add monitor:
   - URL: https://nlc-api.fly.dev/api/v1/health/live
   - Interval: 5 minutes
   - Alerts: Email + Slack

### Step 3: Test GitHub Actions

```bash
# Make a test commit
git add . && git commit -m "Ready for production"
git push origin main

# Watch: GitHub Actions tab
# Should see: Deploy workflow starts → completes successfully
```

---

## Verification Checklist

### ✅ Backend
- [ ] **Fly.io app running** → `flyctl status`
- [ ] **PostgreSQL online** → `flyctl postgres status --app nlc-db`
- [ ] **Redis online** → `flyctl redis status --app nlc-redis`
- [ ] **API responds** → `curl https://nlc-api.fly.dev/api/v1/health/live`
- [ ] **Database initialized** → Migrations run
- [ ] **Secrets stored** → `flyctl secrets list`

### ✅ Frontend
- [ ] **Vercel deployment live** → Open https://nlc-frontend.vercel.app
- [ ] **API URL set** → `vercel env list`
- [ ] **No build errors** → Check Vercel deployment logs

### ✅ Integration
- [ ] **Frontend can reach backend** → Network tab shows requests
- [ ] **No CORS errors** → Console shows no errors
- [ ] **Login works** → Successfully authenticated

### ✅ Deployment Automation
- [ ] **GitHub Actions enabled** → 3 workflows active
- [ ] **GitHub Secrets set** → All 5 secrets present
- [ ] **Auto-deploy works** → Push triggers deployment

### ✅ Monitoring
- [ ] **Slack notifications work** → Test by triggering deployment
- [ ] **Uptime monitor active** → Configured
- [ ] **Weekly health check scheduled** → Monday 10 AM UTC
- [ ] **Daily backups scheduled** → 2 AM UTC daily

---

## Emergency Commands

Save these for when you need them:

### API Down?
```bash
flyctl logs -n 50              # Check error
flyctl machine restart <id>    # Restart
```

### Database Issue?
```bash
flyctl postgres backups list              # See backups
flyctl postgres backups restore backup-1  # Restore
```

### Frontend Broken?
```
Vercel Dashboard → Deployments → Promote Last Good Version
```

### Complete Rollback?
```bash
git revert HEAD
git push origin main
# GitHub Actions auto-redeploys
```

---

## What Now Runs Automatically

From now on, every time you push to main:

```
git push origin main
    ↓
[GitHub Actions Start]
    ↓
✅ Lint code with Ruff
✅ Type check with mypy
✅ Run unit tests
✅ Security scan with Trivy
✅ Build Docker image
✅ Deploy to Fly.io
✅ Run health checks
✅ Send Slack notification (✅ or ❌)
    ↓
🚀 Your changes live in ~5 minutes
```

---

## 🎉 You're Done!

Your production platform is now:
- ✅ Deployed and running
- ✅ Auto-scaling globally
- ✅ Backed up daily
- ✅ Monitored 24/7
- ✅ Zero-cost (free tier)

**Total Setup Time: ~45 minutes**

---

## 📚 Detailed Guides (If You Need Help)

- [FLY_DEPLOYMENT_GUIDE.md](FLY_DEPLOYMENT_GUIDE.md) — Complete setup details
- [FLY_MONITORING_SETUP.md](FLY_MONITORING_SETUP.md) — Monitoring & alerts
- [BACKUP_DISASTER_RECOVERY.md](BACKUP_DISASTER_RECOVERY.md) — Backup & recovery
- [QUICK_START_GUIDE.md](QUICK_START_GUIDE.md) — 5-step quick reference

---

## Support

- **Fly.io Docs:** https://fly.io/docs
- **Vercel Docs:** https://vercel.com/docs
- **Status Pages:**
  - https://status.fly.io
  - https://www.vercelstatus.com

---

**Good luck! Your NEUM LEX COUNSEL platform is production-ready! 🚀**
