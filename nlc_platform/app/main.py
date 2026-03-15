from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.v1.auth import router as auth_router
from app.api.v1.companies import router as companies_router
from app.api.v1.filings import router as filings_router
from app.api.v1.documents import router as documents_router
from app.api.v1.rescue import router as rescue_router
from app.api.v1.commercial import router as commercial_router
from app.api.v1.rules import router as rules_router
from app.api.v1.admin import router as admin_router
from app.api.v1.health import router as health_router

settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="RJSC Compliance Intelligence Platform API",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
    app.include_router(companies_router, prefix=settings.API_V1_PREFIX)
    app.include_router(filings_router, prefix=settings.API_V1_PREFIX)
    app.include_router(documents_router, prefix=settings.API_V1_PREFIX)
    app.include_router(rescue_router, prefix=settings.API_V1_PREFIX)
    app.include_router(commercial_router, prefix=settings.API_V1_PREFIX)
    app.include_router(rules_router, prefix=settings.API_V1_PREFIX)
    app.include_router(admin_router, prefix=settings.API_V1_PREFIX)
    app.include_router(health_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()
