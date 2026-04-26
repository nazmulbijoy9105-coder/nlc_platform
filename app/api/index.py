"""
Vercel serverless entry point for NLC Platform FastAPI backend.
Wraps the FastAPI ASGI app with Mangum for AWS Lambda / Vercel compatibility.
Celery workers are disabled — background tasks run inline on free tier.
"""
import os

os.environ.setdefault("CELERY_ENABLED", "false")

from mangum import Mangum

from app.main import app

# Mangum wraps FastAPI ASGI app for serverless
handler = Mangum(app, lifespan="off")
