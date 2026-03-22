"""
NEUM LEX COUNSEL — Commercial Service
app/services/commercial_service.py

Implements _get_revenue_pipeline, _get_conversion_funnel stubs.
Admin-only revenue intelligence layer.

AI Constitution Article 2.2:
  Revenue fields are NEVER returned to client role users.
  Enforced in dependencies.py (require_revenue_access).
  Additionally: Engagements RLS policy in DB is admin-only.
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import Dict, List, Optional

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commercial import Engagement, Quotation, Task
from app.models.enums import (
    ComplexityLevel, EngagementStatus, RevenueTier,
    TaskPriority, TaskStatus,
)
from app.services.base import BaseService


# ═══════════════════════════════════════════════════════════════════════
# ENGAGEMENT SERVICE
# ═══════════════════════════════════════════════════════════════════════

class EngagementService(BaseService[Engagement]):
    model = Engagement

    async def get_pipeline(self) -> Dict:
        """
        Revenue pipeline from vw_revenue_pipeline view.
        _get_revenue_pipeline stub implementation.
        """
        result = await self.db.execute(text("SELECT * FROM vw_revenue_pipeline"))
        rows = [dict(r) for r in result.mappings().all()]

        # Structure by revenue tier
        pipeline = {
            "COMPLIANCE_PACKAGE":        {"stages": {}, "total_estimated": 0, "total_confirmed": 0, "total_collected": 0},
            "STRUCTURED_REGULARIZATION": {"stages": {}, "total_estimated": 0, "total_confirmed": 0, "total_collected": 0},
            "CORPORATE_RESCUE":          {"stages": {}, "total_estimated": 0, "total_confirmed": 0, "total_collected": 0},
        }
        for row in rows:
            tier = row.get("revenue_tier", "")
            if tier in pipeline:
                stage = row.get("engagement_status", "")
                pipeline[tier]["stages"][stage] = {
                    "count":          row.get("engagement_count", 0),
                    "estimated_bdt":  float(row.get("total_estimated_bdt") or 0),
                    "quoted_bdt":     float(row.get("total_quoted_bdt") or 0),
                    "confirmed_bdt":  float(row.get("total_confirmed_bdt") or 0),
                    "invoiced_bdt":   float(row.get("total_invoiced_bdt") or 0),
                    "collected_bdt":  float(row.get("total_collected_bdt") or 0),
                }
                pipeline[tier]["total_estimated"] += float(row.get("total_estimated_bdt") or 0)
                pipeline[tier]["total_confirmed"]  += float(row.get("total_confirmed_bdt") or 0)
                pipeline[tier]["total_collected"]  += float(row.get("total_collected_bdt") or 0)

        # Grand totals
        grand_total_estimated  = sum(v["total_estimated"]  for v in pipeline.values())
        grand_total_confirmed  = sum(v["total_confirmed"]  for v in pipeline.values())
        grand_total_collected  = sum(v["total_collected"]  for v in pipeline.values())

        return {
            "by_tier":              pipeline,
            "grand_total_estimated_bdt":  grand_total_estimated,
            "grand_total_confirmed_bdt":  grand_total_confirmed,
            "grand_total_collected_bdt":  grand_total_collected,
            "collection_rate":      (
                round(grand_total_collected / grand_total_confirmed * 100, 1)
                if grand_total_confirmed > 0 else 0
            ),
        }

    async def get_conversion_funnel(self) -> Dict:
        """
        Engagement conversion funnel metrics.
        _get_conversion_funnel stub implementation.
        """
        result = await self.db.execute(
            select(
                Engagement.engagement_status,
                func.count().label("count"),
                func.sum(Engagement.estimated_fee_bdt).label("value"),
            )
            .where(Engagement.is_active == True)
            .group_by(Engagement.engagement_status)
        )
        stages = {row.engagement_status: {"count": row.count, "value": float(row.value or 0)}
                  for row in result.all()}

        total_identified = stages.get("IDENTIFIED", {}).get("count", 0)
        total_confirmed  = stages.get("CONFIRMED", {}).get("count", 0)
        total_completed  = stages.get("COMPLETED", {}).get("count", 0)

        return {
            "stages": stages,
            "conversion_identified_to_confirmed": (
                round(total_confirmed / total_identified * 100, 1)
                if total_identified > 0 else 0
            ),
            "conversion_confirmed_to_completed": (
                round(total_completed / total_confirmed * 100, 1)
                if total_confirmed > 0 else 0
            ),
        }

    async def advance_status(
        self,
        engagement_id: uuid.UUID,
        new_status: EngagementStatus,
        *,
        fee_bdt: Optional[float] = None,
    ) -> Optional[Engagement]:
        """Advance engagement through the pipeline stages."""
        eng = await self.get_by_id(engagement_id)
        if not eng:
            return None
        updates: Dict = {"engagement_status": new_status}
        status_date_map = {
            EngagementStatus.QUOTED:      "quoted_date",
            EngagementStatus.CONFIRMED:   "confirmed_date",
            EngagementStatus.IN_PROGRESS: "started_date",
            EngagementStatus.COMPLETED:   "completed_date",
        }
        if new_status in status_date_map:
            updates[status_date_map[new_status]] = date.today()
        if fee_bdt:
            if new_status == EngagementStatus.QUOTED:
                updates["quoted_fee_bdt"] = fee_bdt
            elif new_status == EngagementStatus.CONFIRMED:
                updates["confirmed_fee_bdt"] = fee_bdt
        return await self.update_instance(eng, **updates)

    async def get_for_company(self, company_id: uuid.UUID) -> List[Engagement]:
        """Get all engagements for a company."""
        result = await self.db.execute(
            select(Engagement)
            .where(
                Engagement.company_id == company_id,
                Engagement.is_active == True,
            )
            .order_by(Engagement.identified_date.desc())
        )
        return list(result.scalars().all())


# ═══════════════════════════════════════════════════════════════════════
# QUOTATION SERVICE
# ═══════════════════════════════════════════════════════════════════════

class QuotationService(BaseService[Quotation]):
    model = Quotation

    _last_quotation_number: int = 0

    async def create_quotation(
        self,
        engagement_id: uuid.UUID,
        company_id: uuid.UUID,
        *,
        professional_fee_bdt: float,
        government_fee_bdt: float = 0,
        vat_rate: float = 0.15,
        line_items: Optional[List[Dict]] = None,
        valid_days: int = 30,
        notes: Optional[str] = None,
    ) -> Quotation:
        """Create a quotation for an engagement."""
        vat_bdt = round(professional_fee_bdt * vat_rate, 2)
        total_bdt = professional_fee_bdt + government_fee_bdt + vat_bdt
        quotation_number = await self._next_quotation_number()

        return await self.create(
            engagement_id=engagement_id,
            company_id=company_id,
            quotation_number=quotation_number,
            quotation_date=date.today(),
            valid_until=date.today().replace(day=date.today().day) if valid_days else None,
            professional_fee_bdt=professional_fee_bdt,
            government_fee_bdt=government_fee_bdt,
            vat_bdt=vat_bdt,
            total_bdt=total_bdt,
            status="DRAFT",
            line_items=line_items,
            notes=notes,
        )

    async def _next_quotation_number(self) -> str:
        """Generate next sequential quotation number NLC-YYYY-NNNN."""
        from sqlalchemy import text
        year = date.today().year
        result = await self.db.execute(
            text(
                "SELECT COUNT(*) FROM quotations "
                "WHERE quotation_number LIKE :prefix"
            ),
            {"prefix": f"NLC-{year}-%"},
        )
        count = result.scalar_one() + 1
        return f"NLC-{year}-{count:04d}"

    async def accept(
        self,
        quotation_id: uuid.UUID,
    ) -> Optional[Quotation]:
        """Mark quotation as accepted."""
        q = await self.get_by_id(quotation_id)
        if not q:
            return None
        return await self.update_instance(q, status="ACCEPTED", accepted_date=date.today())

    async def reject(
        self,
        quotation_id: uuid.UUID,
        reason: str,
    ) -> Optional[Quotation]:
        """Mark quotation as rejected."""
        q = await self.get_by_id(quotation_id)
        if not q:
            return None
        return await self.update_instance(q, status="REJECTED", rejection_reason=reason)


# ═══════════════════════════════════════════════════════════════════════
# TASK SERVICE
# ═══════════════════════════════════════════════════════════════════════

class TaskService(BaseService[Task]):
    model = Task

    async def create_task(
        self,
        company_id: uuid.UUID,
        title: str,
        *,
        description: Optional[str] = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        due_date: Optional[date] = None,
        assigned_to: Optional[uuid.UUID] = None,
        created_by: Optional[uuid.UUID] = None,
        source_flag_id: Optional[uuid.UUID] = None,
        source_rescue_step_id: Optional[uuid.UUID] = None,
    ) -> Task:
        """Create a task for a company."""
        return await self.create(
            company_id=company_id,
            title=title,
            description=description,
            task_status=TaskStatus.PENDING,
            priority=priority,
            due_date=due_date,
            assigned_to=assigned_to,
            created_by=created_by,
            source_flag_id=source_flag_id,
            source_rescue_step_id=source_rescue_step_id,
        )

    async def get_for_company(
        self,
        company_id: uuid.UUID,
        *,
        status: Optional[TaskStatus] = None,
        assigned_to: Optional[uuid.UUID] = None,
    ) -> List[Task]:
        """Get tasks for a company with optional filters."""
        filters = [Task.company_id == company_id, Task.is_active == True]
        if status:
            filters.append(Task.task_status == status)
        if assigned_to:
            filters.append(Task.assigned_to == assigned_to)
        result = await self.db.execute(
            select(Task)
            .where(*filters)
            .order_by(Task.priority.desc(), Task.due_date)
        )
        return list(result.scalars().all())

    async def complete_task(
        self,
        task_id: uuid.UUID,
    ) -> Optional[Task]:
        """Mark a task as completed."""
        from datetime import datetime, timezone
        task = await self.get_by_id(task_id)
        if not task:
            return None
        return await self.update_instance(
            task,
            task_status=TaskStatus.COMPLETED,
            completed_at=datetime.now(timezone.utc),
        )
