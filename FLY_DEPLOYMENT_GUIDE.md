# 🚀 Complete Fly.io + Vercel Deployment Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Fly.io Backend Setup](#fly-io-backend-setup)
3. [Vercel Frontend Setup](#vercel-frontend-setup)
4. [Integration & CORS](#integration--cors)
5. [Environment Variables](#environment-variables)
6. [Monitoring & Logs](#monitoring--logs)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Accounts
- [ ] GitHub account (push repositories)
- [ ] Fly.io account (https://fly.io - free)
- [ ] Vercel account (https://vercel.com - free)
- [ ] Anthropic API key (for AI features)
- [ ] AWS credentials (for S3 + SES, optional)

### Local Prerequisites
```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Install Vercel CLI
npm install -g vercel

# Verify installations
flyctl version
vercel --version
```

---

## Fly.io Backend Setup

### Step 1: Authenticate with Fly.io

```bash
flyctl auth login
# Opens browser → Sign in with GitHub → Copy auth token → Paste in terminal
```

### Step 2: Launch Fly App

```bash
cd /workspaces/nlc_platform

# Initialize Fly app
flyctl launch

# Follow prompts:
# - App name: nlc-api
# - Region: sin (Singapore)
# - Don't copy production secrets (we'll set them manually)
# - Don't scale to multiple regions yet (free tier = 1 app)
# - Deploy now? NO (we'll configure first)
```

This creates `fly.toml` in your repo (we provided the production config).

### Step 3: Create PostgreSQL Database

```bash
# Create managed PostgreSQL (free tier: 3GB storage)
flyctl postgres create

# When prompted:
# - App name: nlc-db
# - Initial admin username: nlc_user
# - Choose admin password (save it!)
# - Disk size: 10GB (free)
# - Replication: No (free tier)

# Get connection string
flyctl postgres credentials --app nlc-db
# Copy: postgresql+asyncpg://nlc_user:password@...

# Store as secret
flyctl secrets set DATABASE_URL="postgresql+asyncpg://nlc_user:password@..."
```

### Step 4: Create Redis Cache

```bash
# Create managed Redis (free tier: 1GB)
flyctl redis create

# When prompted:
# - App name: nlc-redis
# - Eviction: true (auto cleanup when full)
# - Replication: No (free tier)

# Get connection string
flyctl redis status --app nlc-redis
# Copy: redis://default:password@...

# Store as secret
flyctl secrets set REDIS_URL="redis://default:password@..."
```

### Step 5: Set All Secrets

```bash
# Generate secure keys
JWT_SECRET=$(openssl rand -base64 32)
TOTP_KEY=$(openssl rand -base64 32)

# Set critical secrets
flyctl secrets set \
  JWT_SECRET_KEY="$JWT_SECRET" \
  TOTP_ENCRYPTION_KEY="$TOTP_KEY" \
  ENVIRONMENT="production" \
  LOG_LEVEL="INFO"

# Set API keys (get these from respective services)
flyctl secrets set \
  ANTHROPIC_API_KEY="sk-..." \
  AWS_ACCESS_KEY_ID="..." \
  AWS_SECRET_ACCESS_KEY="..." \
  S3_BUCKET_NAME="your-bucket" \
  S3_BACKUP_BUCKET="your-backup-bucket" \
  EMAIL_FROM="noreply@nlccounsel.io"

# Verify secrets are set
flyctl secrets list
```

### Step 6: Deploy Backend

```bash
# Deploy
flyctl deploy

# Monitor logs
flyctl logs

# Wait for deployment to complete (2-5 min)
# You should see:
# - [info] Starting Uvicorn server
# - [info] Application startup complete
```

### Step 7: Initialize Database

```bash
# SSH into container
flyctl ssh console

# Run migrations
alembic upgrade head

# Seed rules
python scripts/seed_rules.py

# Seed prompt templates
python scripts/seed_prompt_templates.py

# Exit
exit
```

### Step 8: Verify Backend

```bash
# Get app URL
flyctl info

# Shows: Instance ID, Status, Addresses
# Test endpoint
curl https://nlc-api.fly.dev/api/v1/health/live
# Should return: {"status": "ok"}
```

**Backend URL: https://nlc-api.fly.dev**

---

## Vercel Frontend Setup

### Step 1: Authenticate with Vercel

```bash
vercel login
# Opens browser → Sign in with GitHub
```

### Step 2: Clone & Deploy Frontend

```bash
cd ~/
git clone https://github.com/nazmulbijoy9105-coder/nlc_frontend
cd nlc_frontend

# Link to Vercel
vercel link

# When prompted:
# - Set up new project? Yes
# - Project name: nlc-frontend
# - Framework: Next.js (auto-detected)
# - Build command: npm run build (auto-filled)
# - Output directory: .next (auto-filled)
# - Root directory: ./ (auto-filled)
```

### Step 3: Set Environment Variable

```bash
# Set backend API URL
vercel env add NEXT_PUBLIC_API_URL
# Value: https://nlc-api.fly.dev

# Deploy
vercel --prod

# Wait for deployment (2-3 min)
```

**Frontend URL: https://nlc-frontend.vercel.app**

---

## Integration & CORS

### Update Backend CORS

The frontend must be whitelisted in the backend's CORS policy:

```bash
flyctl secrets set \
  ALLOWED_ORIGINS="https://nlc-frontend.vercel.app,http://localhost:3000"

# Redeploy for changes to take effect
flyctl deploy
```

### Test Integration

1. **Open Frontend:**
   ```
   https://nlc-frontend.vercel.app
   ```

2. **Check DevTools (F12):**
   - Network tab
   - Try login
   - Should see requests to `nlc-api.fly.dev`
   - No CORS errors ✅

3. **Verify API Response:**
   ```bash
   curl -H "Authorization: Bearer test_token" \
     https://nlc-api.fly.dev/api/v1/health/live
   ```

---

## Environment Variables

### Backend (Fly.io Secrets)

| Variable | Value | Notes |
|----------|-------|-------|
| `DATABASE_URL` | `postgres://...` | Auto-set from Postgres creation |
| `REDIS_URL` | `redis://...` | Auto-set from Redis creation |
| `ENVIRONMENT` | `production` | |
| `LOG_LEVEL` | `INFO` | Set to `DEBUG` for troubleshooting |
| `JWT_SECRET_KEY` | Generated | 32-char base64 |
| `TOTP_ENCRYPTION_KEY` | Generated | 32-char base64 |
| `ALLOWED_ORIGINS` | `https://nlc-frontend.vercel.app,http://localhost:3000` | CORS whitelist |
| `ANTHROPIC_API_KEY` | `sk-...` | From Anthropic dashboard |
| `AWS_ACCESS_KEY_ID` | `...` | From AWS IAM |
| `AWS_SECRET_ACCESS_KEY` | `...` | From AWS IAM |
| `S3_BUCKET_NAME` | `nlc-bucket` | Your S3 bucket name |
| `EMAIL_FROM` | `noreply@nlccounsel.io` | Sender email |

### Frontend (Vercel Environment Variables)

| Variable | Value | Scope |
|----------|-------|-------|
| `NEXT_PUBLIC_API_URL` | `https://nlc-api.fly.dev` | Production |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Development |

---

## Monitoring & Logs

### Fly.io Logs

```bash
# Real-time logs
flyctl logs

# Filter by level
flyctl logs --level=error

# Last 100 lines
flyctl logs -n 100

# Save to file
flyctl logs > logs.txt
```

### Health Checks

```bash
# Check app status
flyctl status

# Detailed machine info
flyctl machine list

# SSH into app to debug
flyctl ssh console
```

### Vercel Analytics

```
1. Vercel Dashboard
2. Select nlc-frontend
3. Analytics tab
→ View response times, edge requests, errors
```

---

## Troubleshooting

### Backend Won't Deploy

```bash
# Check build logs
flyctl logs

# Common issues:
# 1. Dockerfile not found: Verify Dockerfile in root
# 2. Port binding: Already used by another app
# 3. Resource limits: Reduce memory in fly.toml

# Solution: Check logs and fix, then redeploy
flyctl deploy --remote-only
```

### Database Connection Failed

```bash
# Verify PostgreSQL is running
flyctl postgres status --app nlc-db

# Test connection
flyctl postgres connect --app nlc-db

# Restart if stuck
flyctl machine restart postgres-xxx
```

### CORS Errors on Frontend

```bash
# Verify ALLOWED_ORIGINS
flyctl secrets list | grep ALLOWED_ORIGINS

# Should include: https://nlc-frontend.vercel.app

# Fix and redeploy
flyctl secrets set ALLOWED_ORIGINS="https://nlc-frontend.vercel.app,http://localhost:3000"
flyctl deploy
```

### Frontend Can't Reach Backend

```bash
# Check env variable
vercel env list

# Should show: NEXT_PUBLIC_API_URL=https://nlc-api.fly.dev

# Verify backend is running
curl https://nlc-api.fly.dev/api/v1/health/live
```

### Out of Memory

```bash
# Check current usage
flyctl machine list

# Optimize Uvicorn workers
fly.toml: change --workers from 2 to 1

# Redeploy
flyctl deploy
```

---

## Scaling (When Needed)

### Scale Backend on Fly.io

```bash
# Add second machine
flyctl machine create

# Add multiple replicas
flyctl scale count=2

# Scale specific Machine type
flyctl machine update-metadata cores=2
```

### Scale Frontend on Vercel

```
Automatic → Vercel handles load balancing
No action needed!
```

---

## Cost Summary (Free Tier)

| Service | Cost | Monthly Usage |
|---------|------|----------------|
| **Fly.io (Backend)** | $0 | 160GB bandwidth included |
| **Vercel (Frontend)** | $0 | 100GB bandwidth included |
| **PostgreSQL (Fly)** | $0 | 3GB storage included |
| **Redis (Fly)** | $0 | 1GB storage included |
| **Total** | **$0** | Unlimited (within limits) |

**First paid feature:** Going over 160GB bandwidth (~$0.06/GB after).

---

## Summary Checklist

- [ ] Fly.io backend deployed: https://nlc-api.fly.dev
- [ ] PostgreSQL initialized with migrations
- [ ] Redis cache running
- [ ] All secrets configured
- [ ] Vercel frontend deployed: https://nlc-frontend.vercel.app
- [ ] CORS configured (frontend URL added to backend)
- [ ] Frontend env variable set (API URL)
- [ ] Integration tested (login works)
- [ ] Monitoring set up (logs accessible)
- [ ] GitHub Actions CI/CD enabled

**🎉 Your production platform is live!**

---

## Next Steps

1. **Enable GitHub Actions:**
   - Push to main → Auto-deploys backend
   - Frontend auto-deploys on push to nlc_frontend

2. **Monitor Performance:**
   - Review Fly.io logs daily
   - Check Vercel analytics weekly

3. **Scale When Ready:**
   - Fly.io: Add replicas when traffic increases
   - Vercel: Already auto-scales globally

4. **Backup Strategy:**
   - See backup & disaster recovery plan below

---

**Need help? Check Fly.io docs: https://fly.io/docs/**
