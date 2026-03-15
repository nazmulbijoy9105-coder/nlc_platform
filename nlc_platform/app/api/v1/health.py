from fastapi import APIRouter
from sqlalchemy import text

from app.core.database import get_db
from app.core.schemas import create_data_response

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def health_check():
    return create_data_response(
        data={
            "status": "healthy",
            "service": "NLC Platform API",
        }
    )


@router.get("/db")
async def health_check_db(db=Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return create_data_response(data={"status": "healthy", "database": "connected"})
    except Exception as e:
        return create_data_response(
            data={"status": "unhealthy", "database": "disconnected"},
            message=str(e),
        )


@router.get("/redis")
async def health_check_redis():
    from app.core.config import get_settings

    settings = get_settings()
    try:
        import redis

        r = redis.Redis.from_url(settings.REDIS_URL)
        r.ping()
        return create_data_response(data={"status": "healthy", "redis": "connected"})
    except Exception:
        return create_data_response(data={"status": "unhealthy", "redis": "disconnected"})


from fastapi import Depends
