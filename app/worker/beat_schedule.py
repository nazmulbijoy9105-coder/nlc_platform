"""
NEUM LEX COUNSEL — Celery Beat Schedule
app/worker/beat_schedule.py

All scheduled (cron) tasks for the NLC compliance engine.
Imported by celery_app.py and applied to celery_app.conf.beat_schedule.

SCHEDULE OVERVIEW:
┌─────────────────────────────────────────────┬──────────────────────┬──────────────┐
│ Task                                        │ Schedule (UTC)       │ Queue        │
├─────────────────────────────────────────────┼──────────────────────┼──────────────┤
│ Daily compliance evaluation (all companies) │ 00:00 UTC daily      │ compliance   │
│ Deadline warning notifications              │ 08:00 UTC daily      │ notifications│
│ AI review queue alert                       │ 09:00, 14:00, 17:00  │ documents    │
│ Monthly score snapshot                      │ 1st of month 01:00   │ maintenance  │
│ Expired notification cleanup                │ 03:00 UTC daily      │ maintenance  │
│ Old activity log cleanup (7yr retention)    │ Sunday 02:00 UTC     │ maintenance  │
│ Database health check                       │ Every 5 minutes      │ maintenance  │
│ SRO registry sync check                     │ 06:00 UTC daily      │ maintenance  │
│ Pending notification sender                 │ Every 10 minutes     │ notifications│
└─────────────────────────────────────────────┴──────────────────────┴──────────────┘

TIMEZONE NOTE:
All schedules are defined in UTC. Bangladesh time (BST) is UTC+6.
So "00:00 UTC" = 06:00 BST — tasks run at 6am Bangladesh time.
"08:00 UTC" = 14:00 BST — deadline warnings at 2pm Bangladesh time.

AI Constitution Article 1:
The daily evaluation cron is the backbone of the compliance engine.
It must run every day. Missing a daily run is a system alert-level event.

Release Governance Protocol:
Changing cron schedules requires Super Admin approval.
Document the business reason for any schedule change.
"""
from __future__ import annotations

from celery.schedules import crontab

# ═══════════════════════════════════════════════════════════════════════
# BEAT SCHEDULE DEFINITION
# ═══════════════════════════════════════════════════════════════════════

BEAT_SCHEDULE = {

    # ── DAILY COMPLIANCE EVALUATION ───────────────────────────────────
    # The most critical scheduled task.
    # Evaluates ALL active companies in the portfolio every night.
    # At 00:00 UTC (06:00 BST) — after business hours, minimal DB load.
    # AI Constitution Article 1: deterministic rule engine, no AI involvement.
    "daily-compliance-evaluation": {
        "task":     "app.worker.tasks.evaluate_all_companies",
        "schedule": crontab(hour=0, minute=0),   # 00:00 UTC = 06:00 BST
        "options": {
            "queue":   "compliance",
            "expires": 3600,         # Expire if not started within 1 hour
            "priority": 9,           # Highest priority
        },
        "kwargs": {
            "trigger_source": "CRON_DAILY",
        },
        "description": "Daily compliance evaluation — all active companies",
    },

    # ── DEADLINE WARNING NOTIFICATIONS ────────────────────────────────
    # Sends email/WhatsApp/dashboard notifications for upcoming deadlines.
    # At 08:00 UTC (14:00 BST) — during Bangladesh business hours.
    # Checks for AGM, Annual Return, Audit deadlines in 30, 15, 7, 3, 1 days.
    "daily-deadline-warnings": {
        "task":     "app.worker.tasks.queue_deadline_warning_notifications",
        "schedule": crontab(hour=8, minute=0),   # 08:00 UTC = 14:00 BST
        "options": {
            "queue":   "notifications",
            "expires": 3600,
        },
        "kwargs": {
            "warning_days": [30, 15, 7, 3, 1],
        },
        "description": "Daily deadline warning notifications (AGM, returns, audits)",
    },

    # ── PENDING NOTIFICATION SENDER ───────────────────────────────────
    # Processes notifications in PENDING status and attempts delivery.
    # Runs every 10 minutes — short enough for timely delivery,
    # long enough to batch and not hammer email APIs.
    "process-pending-notifications": {
        "task":     "app.worker.tasks.send_pending_notifications",
        "schedule": crontab(minute="*/10"),      # Every 10 minutes
        "options": {
            "queue":   "notifications",
            "expires": 600,          # Expire if not started within 10 minutes
        },
        "kwargs": {
            "batch_size": 50,        # Max 50 notifications per run
        },
        "description": "Process pending notifications queue (email, WhatsApp, dashboard)",
    },

    # ── AI REVIEW QUEUE ALERTS ────────────────────────────────────────
    # Checks for AI-generated documents waiting for human review.
    # Sends an alert to NLC legal staff if documents have been waiting
    # more than 2 hours. AI Constitution Article 3 enforcement.
    # Runs 3x per day during business hours (BST: 15:00, 20:00, 23:00).
    "ai-review-queue-morning": {
        "task":     "app.worker.tasks.process_ai_review_queue",
        "schedule": crontab(hour=9, minute=0),   # 09:00 UTC = 15:00 BST
        "options": {
            "queue":   "documents",
            "expires": 3600,
        },
        "kwargs": {
            "alert_threshold_hours": 2,
        },
        "description": "AI review queue check — alert staff of pending approvals (morning)",
    },
    "ai-review-queue-afternoon": {
        "task":     "app.worker.tasks.process_ai_review_queue",
        "schedule": crontab(hour=14, minute=0),  # 14:00 UTC = 20:00 BST
        "options": {
            "queue":   "documents",
            "expires": 3600,
        },
        "kwargs": {
            "alert_threshold_hours": 2,
        },
        "description": "AI review queue check — alert staff of pending approvals (afternoon)",
    },
    "ai-review-queue-evening": {
        "task":     "app.worker.tasks.process_ai_review_queue",
        "schedule": crontab(hour=17, minute=0),  # 17:00 UTC = 23:00 BST
        "options": {
            "queue":   "documents",
            "expires": 3600,
        },
        "kwargs": {
            "alert_threshold_hours": 2,
        },
        "description": "AI review queue check — alert staff of pending approvals (evening)",
    },

    # ── MONTHLY SCORE SNAPSHOT ────────────────────────────────────────
    # On the 1st of every month at 01:00 UTC, takes a formal compliance
    # score snapshot for all companies. This creates the immutable monthly
    # record used for trend reporting and client reporting.
    # AI Constitution Article 4: score snapshots are append-only and tamper-evident.
    "monthly-score-snapshot": {
        "task":     "app.worker.tasks.monthly_score_snapshot_all",
        "schedule": crontab(day_of_month=1, hour=1, minute=0),  # 1st of month
        "options": {
            "queue":   "maintenance",
            "expires": 7200,         # Expire if not started within 2 hours
        },
        "description": "Monthly compliance score snapshot — all active companies",
    },

    # ── SRO REGISTRY SYNC CHECK ───────────────────────────────────────
    # Checks if any SRO (Statutory Regulatory Order) entries in the registry
    # have rule_update_required=True and alerts Super Admin.
    # At 06:00 UTC (12:00 BST) daily — midday Bangladesh.
    "sro-registry-check": {
        "task":     "app.worker.tasks.sync_sro_registry",
        "schedule": crontab(hour=6, minute=0),   # 06:00 UTC = 12:00 BST
        "options": {
            "queue":   "maintenance",
            "expires": 3600,
        },
        "description": "SRO registry check — alert Super Admin of pending rule updates",
    },

    # ── EXPIRED NOTIFICATION CLEANUP ─────────────────────────────────
    # Mark old PENDING notifications as FAILED if they haven't been sent
    # within 48 hours. Prevents the notification queue from growing unboundedly.
    "cleanup-expired-notifications": {
        "task":     "app.worker.tasks.cleanup_expired_notifications",
        "schedule": crontab(hour=3, minute=0),   # 03:00 UTC = 09:00 BST
        "options": {
            "queue":   "maintenance",
            "expires": 3600,
        },
        "kwargs": {
            "expire_after_hours": 48,
        },
        "description": "Mark expired pending notifications as FAILED",
    },

    # ── ACTIVITY LOG RETENTION (7-year rule) ─────────────────────────
    # Compliance regulation: activity logs and compliance events must be
    # retained for 7 years. Logs older than 7 years are archived to S3
    # and removed from the database. This keeps the DB size manageable.
    # Runs every Sunday at 02:00 UTC (08:00 BST).
    "weekly-log-cleanup": {
        "task":     "app.worker.tasks.cleanup_old_activity_logs",
        "schedule": crontab(day_of_week=0, hour=2, minute=0),  # Sunday 02:00 UTC
        "options": {
            "queue":   "maintenance",
            "expires": 7200,
        },
        "kwargs": {
            "retain_years": 7,
        },
        "description": "7-year retention enforcement — archive old activity logs to S3",
    },

    # ── DATABASE HEALTH CHECK ─────────────────────────────────────────
    # Lightweight DB connectivity check every 5 minutes.
    # If this fails, it means DB is unreachable — triggers an alert.
    # Very fast — just runs SELECT 1.
    "db-health-check": {
        "task":     "app.worker.tasks.database_health_check",
        "schedule": crontab(minute="*/5"),       # Every 5 minutes
        "options": {
            "queue":   "maintenance",
            "expires": 60,           # Expire very quickly if not started
        },
        "description": "Database connectivity health check",
    },

}
