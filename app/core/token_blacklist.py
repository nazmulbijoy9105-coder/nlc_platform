"""Access-token revocation list backed by Redis, keyed by JWT jti."""
from __future__ import annotations

import logging
import os
import time
from functools import lru_cache

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)


def _redis_url() -> str:
    return os.environ.get("REDIS_URL") or settings.redis_url or "redis://localhost:6379/0"


@lru_cache(maxsize=1)
def _client() -> redis.Redis:
    return redis.from_url(
        _redis_url(),
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )


def revoke(jti: str, exp: float | None) -> bool:
    """Blacklist jti until the token's own expiry. Returns False if Redis failed."""
    ttl = max(int(exp - time.time()), 1) if exp else 3600
    try:
        _client().setex(f"blacklist:{jti}", ttl, "revoked")
        return True
    except Exception:
        logger.warning("token_revoke_failed", exc_info=True)
        return False


def is_revoked(jti: str) -> bool:
    """Fail-open on Redis errors (availability), but log them."""
    try:
        return bool(_client().exists(f"blacklist:{jti}"))
    except Exception:
        logger.warning("token_blacklist_check_failed", exc_info=True)
        return False
