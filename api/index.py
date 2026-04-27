"""
Vercel serverless entry point for NLC Platform FastAPI backend.
Wraps the FastAPI ASGI app with Mangum for Vercel (AWS Lambda) compatibility.
"""
import os
os.environ.setdefault("CELERY_ENABLED", "false")

from mangum import Mangum  # noqa: E402
from app.main import app   # noqa: E402

# Vercel Python runtime requires a top-level "handler" variable
handler = Mangum(app, lifespan="off")
