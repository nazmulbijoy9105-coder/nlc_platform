from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from app.core.config import get_settings

settings = get_settings()


class TimestampMixin(BaseModel):
    created_at: datetime = datetime.now(timezone.utc)
    updated_at: datetime = datetime.now(timezone.utc)


class ResponseBase(BaseModel):
    success: bool = True
    message: str | None = None


T = TypeVar("T")


class DataResponse(ResponseBase, Generic[T]):
    data: T | None = None


class PaginatedResponse(ResponseBase, Generic[T]):
    data: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class ErrorResponse(ResponseBase):
    success: bool = False
    error_code: str | None = None
    details: dict[str, Any] | None = None


def create_error_response(
    message: str,
    error_code: str | None = None,
    details: dict[str, Any] | None = None,
) -> ErrorResponse:
    return ErrorResponse(
        success=False,
        message=message,
        error_code=error_code,
        details=details,
    )


def create_data_response(data: Any, message: str | None = None) -> DataResponse:
    return DataResponse(success=True, data=data, message=message)


def create_paginated_response(
    data: list[Any],
    total: int,
    page: int,
    page_size: int,
) -> PaginatedResponse:
    total_pages = (total + page_size - 1) // page_size
    return PaginatedResponse(
        success=True,
        data=data,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
