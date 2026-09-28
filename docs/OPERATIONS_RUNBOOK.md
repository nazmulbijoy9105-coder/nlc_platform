# NLC Platform — Operations Runbook

## Quick Reference

| Resource | URL / Command |
|----------|---------------|
| Frontend | https://nlc-frontend.vercel.app |
| Backend API | https://nlc-platform.onrender.com |
| Health | GET https://nlc-platform.onrender.com/api/v1/health/live |
| Readiness | GET https://nlc-platform.onrender.com/api/v1/health/ready |
| Metrics | GET https://nlc-platform.onrender.com/metrics |
| Admin Login | admin@neumlexcounsel.com / NLC@Admin2026! |
| Database | Neon PostgreSQL (ap-southeast-1) |
| Redis | Render Redis (same region) |
| GitHub | https://github.com/nazmulbijoy9105-coder/nlc_platform |

## Incident Response

### API is down (503 / timeout)
1. Check Render dashboard → nlc-platform → Logs
2. Check `GET /api/v1/health/live` — if 503, service is down
3. Check `GET /api/v1/health/ready` — see which dependency failed
4. If DB down → Check Neon dashboard → Check DATABASE_URL env var
5. If Redis down → Check Render Redis service
6. Restart service: Render dashboard → Manual Deploy → Clear build cache
7. Verify: `curl https://nlc-platform.onrender.com/api/v1/health/live`

### Frontend is down (500 / blank page)
1. Check Vercel dashboard → nlc_frontend → Deployments
2. Check if latest build failed (TypeScript errors)
3. If build failed → Fix code → Push to main → Vercel auto-deploys
4. If build OK but page blank → Check API_URL in frontend env vars

### Login not working (401)
1. Test: `curl -X POST https://nlc-platform.onrender.com/api/v1/auth/login -H "Content-Type: application/json" -d '{"email":"admin@neumlexcounsel.com","password":"NLC@Admin2026!"}'`
2. If 401 → Password may have changed → Run `POST /api/v1/auth/setup-admin`
3. If 500 → Database connection issue → Check Neon
4. If CORS error → Check ALLOWED_ORIGINS env var on Render

### Migration failure (Render deploy fails)
1. Check Render logs for the specific migration that failed
2. Common fixes:
   - `IF NOT EXISTS` not supported → Use `DROP IF EXISTS` + `ADD`
   - `column does not exist` → Remove the FK/index, use DO block
   - `enum type` → Convert to VARCHAR
3. Fix the migration file → Push to main → Render auto-deploys

### Database recovery (data loss)
1. Go to Neon dashboard → project → branch
2. Use PITR (Point-in-Time Recovery) to restore to before the incident
3. Create a new branch from the restore point
4. Update DATABASE_URL on Render to point to the new branch
5. Restart Render service

## Monitoring

### Health checks (every 1 min)
- `GET /api/v1/health/live` → 200 = alive
- `GET /api/v1/health/ready` → 200 = ready (DB + Redis + engine)

### Metrics (Prometheus)
- `GET /metrics` → Prometheus format metrics
- Configure Grafana or Datadog to scrape this endpoint

### Uptime monitoring
- Set up UptimeRobot (free) to ping /api/v1/health/live every 5 min
- Alert on: non-200 response, timeout > 30s

### Error monitoring
- Set SENTRY_DSN env var on Render
- Sentry captures all 500 errors and exceptions

## Backup Strategy

### Neon PITR
- Neon provides Point-in-Time Recovery (up to 7 days on free tier)
- Run `python3 scripts/verify_backup.py` weekly to verify

### Activity log archive (7-year retention)
- Celery task `cleanup_old_activity_logs` archives to S3
- Requires S3_BACKUP_BUCKET env var
- Runs weekly (Sunday 02:00 UTC)

## Deployment

### Backend (Render)
- Push to `main` → Render auto-deploys
- Build: Docker multi-stage → Install deps → Run alembic upgrade → Start uvicorn
- Health check: /api/v1/health/live

### Frontend (Vercel)
- Push to `main` → Vercel auto-deploys
- Build: npm install → next build → Static + dynamic pages
- No health check (static hosting)

### Worker (Render — NEW)
- Deploy as Background Worker on Render
- Command: `celery -A app.worker.celery_app worker --loglevel=info`
- Enables: daily evaluation, deadline notifications, score snapshots, cleanup

### Beat scheduler (Render — NEW)
- Deploy as Background Worker on Render
- Command: `celery -A app.worker.celery_app beat --loglevel=info`
- Enables: cron schedules (daily eval, monthly snapshot, weekly cleanup)

## Celery Tasks Schedule

| Schedule | Task | Description |
|----------|------|-------------|
| Daily 00:00 UTC | evaluate_all_companies | Evaluate all active companies |
| Daily 06:00 UTC | check_deadlines | Send deadline warnings (30/15/7/3/1 days) |
| 1st of month | monthly_score_snapshot | Snapshot all company scores |
| Sunday 02:00 | cleanup_old_activity_logs | Archive 7-year-old logs to S3 |
| Daily 08:00 | check_sro_registry | Check for new RJSC SROs |
| Hourly | stale_document_alert | Alert on documents in review >2hrs |
