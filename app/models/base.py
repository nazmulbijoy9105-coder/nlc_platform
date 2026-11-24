"""Credential-independent SQLAlchemy declarative base.

Alembic imports this metadata without initializing the application
database engine or requiring runtime database credentials.
"""
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase


class Base(AsyncAttrs, DeclarativeBase):
    """Declarative base shared by all NLC ORM models."""
    pass
