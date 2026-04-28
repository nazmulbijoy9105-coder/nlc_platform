"""
api/index.py — Main FastAPI app
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import time

from app.core.config import settings
from app.core.security import create_admin_user_if_missing


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_admin_user_if_missing()
    yield


app = FastAPI(
    title="NLC Platform",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)

# CORS — Vercel ONLY
origins = [settings.FRONTEND_URL]
if "vercel.app" in settings.FRONTEND_URL:
    base = settings.FRONTEND_URL.split(".vercel.app")[0]
    origins.append(f"{base}-*.vercel.app")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Authorization", "X-Total-Count"],
)

@app.middleware("http")
async def timing(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    response.headers["X-Process-Time"] = str(round(time.time() - start, 4))
    return response

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "NLC Platform"}

# Auth + Admin
from app.api.auth import router as auth_router
from app.api.admin import router as admin_router

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(admin_router, prefix="/api/admin", tags=["admin"])

# Existing routers safe load
try:
    from app.api import (rules, cases, documents, analytics, templates, 
                         notifications, reports, search, exports)
    app.include_router(rules.router, prefix="/api/rules", tags=["rules"])
    app.include_router(cases.router, prefix="/api/cases", tags=["cases"])
    app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
    app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
    app.include_router(templates.router, prefix="/api/templates", tags=["templates"])
    app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
    app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
    app.include_router(search.router, prefix="/api/search", tags=["search"])
    app.include_router(exports.router, prefix="/api/exports", tags=["exports"])
except ImportError as e:
    print(f"[WARN] Router import skipped: {e}")
