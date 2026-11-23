"""HTTP Bearer authentication dependency with RFC-compliant 401 responses.

Use composition rather than subclassing FastAPI's HTTPBearer: FastAPI needs
the public callable parameter annotated as Request, while HTTPBearer's own
callable is typed against HTTPConnection.
"""
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer
from fastapi.security.base import SecurityBase
from fastapi.security.http import HTTPAuthorizationCredentials


class Bearer401(SecurityBase):
    """Missing/malformed Authorization header -> 401 (RFC 7235), not 403."""

    def __init__(
        self,
        *,
        auto_error: bool = True,
        scheme_name: str | None = None,
    ) -> None:
        self._bearer = HTTPBearer(
            auto_error=auto_error,
            scheme_name=scheme_name,
        )
        # Preserve FastAPI's OpenAPI HTTP bearer security scheme metadata.
        self.model = self._bearer.model
        self.scheme_name = self._bearer.scheme_name
        self.auto_error = auto_error

    async def __call__(
        self, request: Request
    ) -> HTTPAuthorizationCredentials | None:
        try:
            return await self._bearer(request)
        except HTTPException as exc:
            if exc.status_code == status.HTTP_403_FORBIDDEN:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                ) from exc
            raise
