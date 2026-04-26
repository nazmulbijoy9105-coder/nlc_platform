"""
Root Vercel serverless entry point for NLC Platform.
Re-exports the Mangum handler from app/api/index.py.

Vercel Python builder expects this file at api/index.py (per vercel.json).
"""
from app.api.index import handler  # noqa: F401 — re-exported for Vercel
