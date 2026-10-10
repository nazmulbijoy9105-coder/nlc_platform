# NOTE: do NOT add `from __future__ import annotations` here.
# FastAPI must resolve the `request: Request` annotation of __call__.
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer


class Bearer401(HTTPBearer):
    """Missing/malformed Authorization header -> 401 (RFC 7235), not 403."""

    async def __call__(self, request: Request):
        try:
            return await super().__call__(request)
        except HTTPException as exc:
            if exc.status_code == status.HTTP_403_FORBIDDEN:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                ) from exc
            raise
