"""
NEUM LEX COUNSEL — Base Service Layer
app/services/base.py

BaseService provides common async database operations.
All domain services inherit from this class.
Concrete services add domain-specific business logic on top.

Design principles:
  - All DB access is async (asyncpg)
  - RLS context is already set by the dependency layer
  - Services never call AI directly (AI Constitution Article 3)
  - Services never build HTTP responses — they return ORM models
  - All writes produce activity log entries via ActivityService
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Base

logger = logging.getLogger("nlc.services")

# Generic type variable bound to any ORM model
ModelT = TypeVar("ModelT", bound=Base)


class BaseService(Generic[ModelT]):
    """
    Generic base service providing standard async CRUD operations.
    Subclass and set `model` to the ORM model class.

    Example:
        class UserService(BaseService[User]):
            model = User
    """
    model: Type[ModelT]

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── CREATE ────────────────────────────────────────────────────

    async def create(self, **kwargs: Any) -> ModelT:
        """
        Create and persist a new instance.
        Auto-generates UUID if 'id' not in kwargs.
        Returns the fully refreshed ORM instance.
        """
        if "id" not in kwargs:
            kwargs["id"] = uuid.uuid4()
        instance = self.model(**kwargs)
        self.db.add(instance)
        await self.db.flush()   # Get DB-generated values (created_at etc.)
        await self.db.refresh(instance)
        logger.debug(f"[{self.model.__tablename__}] Created {instance.id}")
        return instance

    # ── READ ──────────────────────────────────────────────────────

    async def get_by_id(self, record_id: uuid.UUID) -> Optional[ModelT]:
        """Fetch one record by primary key. Returns None if not found."""
        result = await self.db.execute(
            select(self.model).where(self.model.id == record_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_or_404(self, record_id: uuid.UUID) -> ModelT:
        """Fetch one record by primary key. Raises 404 HTTPException if not found."""
        from fastapi import HTTPException, status
        instance = await self.get_by_id(record_id)
        if instance is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{self.model.__tablename__} with id={record_id} not found.",
            )
        return instance

    async def list_all(
        self,
        *,
        limit: int = 25,
        offset: int = 0,
        order_by=None,
        filters: Optional[List] = None,
    ) -> List[ModelT]:
        """
        List records with optional filters, ordering, and pagination.
        filters: list of SQLAlchemy column expressions e.g. [Model.is_active == True]
        """
        stmt = select(self.model)
        if filters:
            for f in filters:
                stmt = stmt.where(f)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count(self, filters: Optional[List] = None) -> int:
        """Count records matching filters."""
        stmt = select(func.count()).select_from(self.model)
        if filters:
            for f in filters:
                stmt = stmt.where(f)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    # ── UPDATE ────────────────────────────────────────────────────

    async def update_by_id(
        self,
        record_id: uuid.UUID,
        **kwargs: Any,
    ) -> Optional[ModelT]:
        """
        Update specific fields on a record by ID.
        Returns the refreshed instance or None if not found.
        Excludes None values (partial update pattern).
        """
        # Filter out None values — don't overwrite with null
        updates = {k: v for k, v in kwargs.items() if v is not None}
        if not updates:
            return await self.get_by_id(record_id)

        await self.db.execute(
            update(self.model)
            .where(self.model.id == record_id)
            .values(**updates)
        )
        await self.db.flush()
        instance = await self.get_by_id(record_id)
        if instance:
            await self.db.refresh(instance)
        return instance

    async def update_instance(self, instance: ModelT, **kwargs: Any) -> ModelT:
        """
        Update specific fields on an already-loaded ORM instance.
        More efficient when you already have the instance in memory.
        """
        for key, value in kwargs.items():
            if value is not None:
                setattr(instance, key, value)
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    # ── SOFT DELETE ───────────────────────────────────────────────

    async def soft_delete(self, record_id: uuid.UUID) -> bool:
        """
        Mark a record as inactive (is_active = False).
        NEVER hard-delete records — audit trail must be preserved.
        Returns True if found and deactivated, False if not found.
        """
        result = await self.db.execute(
            update(self.model)
            .where(self.model.id == record_id)
            .values(is_active=False)
        )
        await self.db.flush()
        return result.rowcount > 0

    # ── EXISTENCE CHECK ───────────────────────────────────────────

    async def exists(self, **kwargs: Any) -> bool:
        """Check if any record matching the given column=value kwargs exists."""
        conditions = [
            getattr(self.model, k) == v for k, v in kwargs.items()
        ]
        stmt = select(func.count()).select_from(self.model).where(*conditions)
        result = await self.db.execute(stmt)
        return result.scalar_one() > 0

    # ── FLUSH ─────────────────────────────────────────────────────

    async def flush(self) -> None:
        """Flush pending DB operations without committing the transaction."""
        await self.db.flush()
