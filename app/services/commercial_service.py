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

from datetime import UTC, date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select, text

from app.models.commercial import (
    Engagement,
    InvalidEngagementTransitionError,
    Quotation,
    Task,
    validate_engagement_transition,
)
from app.models.enums import (
    EngagementStatus,
    TaskPriority,
    TaskStatus,
)
from app.services.base import BaseService

if TYPE_CHECKING:
    import uuid


class CommercialConflictError(ValueError):
    """Raised when a commercial action conflicts with the current workflow state."""


# ═══════════════════════════════════════════════════════════════════════
# ENGAGEMENT SERVICE
# ═══════════════════════════════════════════════════════════════════════

class EngagementService(BaseService[Engagement]):
    model = Engagement

    async def get_pipeline(self) -> dict:
        """
        Revenue pipeline from vw_revenue_pipeline view.
        _get_revenue_pipeline stub implementation.
        """
        result = await self.db.execute(text("SELECT * FROM vw_revenue_pipeline"))
        rows = [dict(r) for r in result.mappings().all()]

        # Structure by revenue tier
        pipeline = {
            "COMPLIANCE_PACKAGE":        {"stages": {}, "total_estimated": Decimal('0.00'), "total_confirmed": Decimal('0.00'), "total_invoiced": Decimal('0.00'), "total_collected": Decimal('0.00')},
            "STRUCTURED_REGULARIZATION": {"stages": {}, "total_estimated": Decimal('0.00'), "total_confirmed": Decimal('0.00'), "total_invoiced": Decimal('0.00'), "total_collected": Decimal('0.00')},
            "CORPORATE_RESCUE":          {"stages": {}, "total_estimated": Decimal('0.00'), "total_confirmed": Decimal('0.00'), "total_invoiced": Decimal('0.00'), "total_collected": Decimal('0.00')},
        }
        for row in rows:
            tier = row.get("revenue_tier", "")
            if tier in pipeline:
                stage = row.get("engagement_status", "")
                pipeline[tier]["stages"][stage] = {  # type: ignore
                    "count":          row.get("engagement_count", 0),
                    "estimated_bdt":  Decimal(str(row.get("total_estimated_bdt") or 0)),
                    "quoted_bdt":     Decimal(str(row.get("total_quoted_bdt") or 0)),
                    "confirmed_bdt":  Decimal(str(row.get("total_confirmed_bdt") or 0)),
                    "invoiced_bdt":   Decimal(str(row.get("total_invoiced_bdt") or 0)),
                    "collected_bdt":  Decimal(str(row.get("total_collected_bdt") or 0)),
                }
                pipeline[tier]["total_estimated"] += Decimal(str(row.get("total_estimated_bdt") or 0))
                pipeline[tier]["total_confirmed"] += Decimal(str(row.get("total_confirmed_bdt") or 0))
                pipeline[tier]["total_invoiced"] += Decimal(str(row.get("total_invoiced_bdt") or 0))
                pipeline[tier]["total_collected"] += Decimal(str(row.get("total_collected_bdt") or 0))

        # Grand totals
        grand_total_estimated  = sum(v["total_estimated"]  for v in pipeline.values())  # type: ignore
        grand_total_confirmed  = sum(v["total_confirmed"]  for v in pipeline.values())  # type: ignore
        grand_total_invoiced = sum(v["total_invoiced"] for v in pipeline.values())  # type: ignore
        grand_total_collected  = sum(v["total_collected"]  for v in pipeline.values())  # type: ignore

        return {
            "by_tier": pipeline,
            "grand_total_estimated_bdt": grand_total_estimated,
            "grand_total_confirmed_bdt": grand_total_confirmed,
            "grand_total_invoiced_bdt": grand_total_invoiced,
            # Engagement aggregates are not independently verified receipts.
            "grand_total_collected_bdt": grand_total_collected,
            # These are manually recorded engagement aggregates, not receipts
            # reconciled against a payment ledger or bank/gateway settlement.
            "revenue_data_basis": "ENGAGEMENT_RECORDED_AGGREGATES",
            "collected_cash_reconciled": False,
            "collection_rate": (
                round(grand_total_collected / grand_total_confirmed * 100, 1)
                if grand_total_confirmed > 0 else 0
            ),
        }

    async def get_conversion_funnel(self) -> dict:
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
            .where(Engagement.is_active)
            .group_by(Engagement.engagement_status)
        )
        stages = {row.engagement_status: {"count": row.count, "value": Decimal(str(row.value or 0))}
                  for row in result.all()}

        total_identified = stages.get("IDENTIFIED", {}).get("count", 0)
        total_confirmed  = stages.get("CONFIRMED", {}).get("count", 0)
        total_completed  = stages.get("COMPLETED", {}).get("count", 0)

        return {
            "stages": stages,
            "conversion_identified_to_confirmed": (
                round(total_confirmed / total_identified * 100, 1)  # type: ignore
                if total_identified > 0 else 0  # type: ignore
            ),
            "conversion_confirmed_to_completed": (
                round(total_completed / total_confirmed * 100, 1)  # type: ignore
                if total_confirmed > 0 else 0  # type: ignore
            ),
        }

    async def advance_status(
        self,
        engagement_id: uuid.UUID,
        new_status: EngagementStatus,
        *,
        fee_bdt: Decimal | None = None,
        note: str | None = None,
    ) -> Engagement | None:
        """Advance an engagement only through the canonical lifecycle."""
        result = await self.db.execute(
            select(Engagement)
            .where(Engagement.id == engagement_id, Engagement.is_active.is_(True))
            .with_for_update()
        )
        engagement = result.scalar_one_or_none()
        if engagement is None:
            return None

        if not validate_engagement_transition(engagement.engagement_status, new_status):
            raise InvalidEngagementTransitionError(
                str(engagement.engagement_status), str(new_status)
            )

        if new_status == EngagementStatus.QUOTED:
            quotation_count = await self.db.execute(
                select(func.count())
                .select_from(Quotation)
                .where(
                    Quotation.engagement_id == engagement_id,
                    Quotation.status.in_({"DRAFT", "SENT"}),
                )
            )
            if quotation_count.scalar_one() < 1:
                raise CommercialConflictError(
                    "An issued quotation is required before moving an engagement to QUOTED."
                )

        if new_status == EngagementStatus.CONFIRMED:
            accepted_count = await self.db.execute(
                select(func.count())
                .select_from(Quotation)
                .where(
        """Advance engagement through the pipeline stages."""
        engagement_result = await self.db.execute(
            select(Engagement)
            .where(Engagement.id == engagement_id, Engagement.is_active)
            .with_for_update()
        )
        eng = engagement_result.scalar_one_or_none()
        if not eng:
            return None
        from app.models.commercial import validate_engagement_transition
        if not validate_engagement_transition(eng.engagement_status, new_status):
            raise ValueError(
                f"Invalid engagement transition: {eng.engagement_status} -> {new_status}"
            )
        if new_status == EngagementStatus.QUOTED:
            raise CommercialConflictError("Create a quotation to move an engagement into QUOTED")
        if new_status == EngagementStatus.CONFIRMED:
            accepted_result = await self.db.execute(
                select(func.count()).select_from(Quotation).where(
                    Quotation.engagement_id == engagement_id,
                    Quotation.status == "ACCEPTED",
                )
            )
            if accepted_count.scalar_one() < 1:
                raise CommercialConflictError(
                    "An accepted quotation is required before confirming an engagement."
                )

            if accepted_result.scalar_one() < 1:
                raise CommercialConflictError("An accepted quotation is required before confirmation")
        updates: dict = {"engagement_status": new_status}
        status_date_map = {
            EngagementStatus.QUOTED: "quoted_date",
            EngagementStatus.CONFIRMED: "confirmed_date",
            EngagementStatus.IN_PROGRESS: "started_date",
            EngagementStatus.COMPLETED: "completed_date",
        }
        if new_status in status_date_map:
            updates[status_date_map[new_status]] = date.today()
        if note:
            existing_notes = engagement.notes or ""
            updates["notes"] = (
                f"{existing_notes}\n[{date.today().isoformat()}] {note}"
            ).strip()
            existing_notes = eng.notes or ""
            updates["notes"] = f"{existing_notes}\n[{date.today().isoformat()}] {note}".strip()
        if fee_bdt is not None:
            if new_status == EngagementStatus.QUOTED:
                updates["quoted_fee_bdt"] = fee_bdt
            elif new_status == EngagementStatus.CONFIRMED:
                updates["confirmed_fee_bdt"] = fee_bdt

        return await self.update_instance(engagement, **updates)

    async def get_for_company(self, company_id: uuid.UUID) -> list[Engagement]:
        """Get all engagements for a company."""
        result = await self.db.execute(
            select(Engagement)
            .where(
                Engagement.company_id == company_id,
                Engagement.is_active,
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
        professional_fee_bdt: Decimal,
        government_fee_bdt: Decimal = Decimal("0.00"),
        vat_bdt: Decimal = Decimal("0.00"),
        line_items: list[dict] | None = None,
        valid_days: int = 30,
        notes: str | None = None,
    ) -> Quotation:
        """Create a company-bound quotation using exact decimal arithmetic."""
        """Create a quotation for an engagement owned by the specified company."""
        engagement_result = await self.db.execute(
            select(Engagement)
            .where(
                Engagement.id == engagement_id,
                Engagement.company_id == company_id,
                Engagement.is_active.is_(True),
            )
            .with_for_update()
        )
        engagement = engagement_result.scalar_one_or_none()
        if engagement is None:
            raise ValueError(
                "Engagement does not belong to the supplied company or is inactive."
            )
            raise ValueError("Engagement not found for the specified company")
        if engagement.engagement_status not in {
            EngagementStatus.IDENTIFIED,
            EngagementStatus.QUOTED,
        }:
            raise CommercialConflictError(
                "A quotation can only be created for an identified or quoted engagement."
            )
        if not 7 <= valid_days <= 90:
            raise ValueError("Quotation validity must be between 7 and 90 days.")

        professional_fee = Decimal(str(professional_fee_bdt)).quantize(Decimal("0.01"))
        government_fee = Decimal(str(government_fee_bdt)).quantize(Decimal("0.01"))
        vat_amount = Decimal(str(vat_bdt)).quantize(Decimal("0.01"))
        if professional_fee <= 0 or government_fee < 0 or vat_amount < 0:
            raise ValueError("Quotation fees must be positive or zero as applicable.")
        total_bdt = professional_fee + government_fee + vat_amount
                f"Cannot issue a quotation while engagement is {engagement.engagement_status}"
            )
        professional_fee_bdt = professional_fee_bdt.quantize(Decimal("0.01"))
        government_fee_bdt = government_fee_bdt.quantize(Decimal("0.01"))
        vat_bdt = vat_bdt.quantize(Decimal("0.01"))
        total_bdt = (professional_fee_bdt + government_fee_bdt + vat_bdt).quantize(Decimal("0.01"))
        quotation_number = await self._next_quotation_number()

        quotation = await self.create(
            engagement_id=engagement_id,
            company_id=company_id,
            quotation_number=quotation_number,
            quotation_date=date.today(),
            valid_until=date.today() + timedelta(days=valid_days) if valid_days else None,
            professional_fee_bdt=professional_fee_bdt,
            government_fee_bdt=government_fee_bdt,
            vat_bdt=vat_bdt,
            total_bdt=total_bdt,
            status="DRAFT",
            line_items=line_items,
            notes=notes,
        )
        await self.db.flush()

        engagement.quoted_fee_bdt = total_bdt
        if engagement.engagement_status == EngagementStatus.IDENTIFIED:
            engagement.engagement_status = EngagementStatus.QUOTED
            engagement.quoted_date = date.today()
        self.db.add(engagement)
        await self.db.flush()
        return quotation

    async def _next_quotation_number(self) -> str:
        """Generate the next sequential quotation number under a transaction lock."""
        year = date.today().year
        prefix = f"NLC-{year}-"
        await self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
            {"lock_key": prefix},
        )
        result = await self.db.execute(
            text(
                "SELECT COALESCE(MAX(CAST(SPLIT_PART(quotation_number, '-', 3) AS INTEGER)), 0) "
                "FROM quotations WHERE quotation_number LIKE :prefix"
        pattern = f"{prefix}%"
        result = await self.db.execute(
            text(
                "SELECT COALESCE(MAX("
                "CAST(SUBSTRING(quotation_number FROM CAST(:suffix_start AS INTEGER)) AS INTEGER)"
                "), 0) + 1 "
                "FROM quotations "
                "WHERE quotation_number LIKE :pattern "
                "AND SUBSTRING(quotation_number FROM CAST(:suffix_start AS INTEGER)) ~ '^[0-9]+$'"
                "CASE "
                "WHEN SPLIT_PART(quotation_number, '-', 3) ~ '^[0-9]+$' "
                "THEN CAST(SPLIT_PART(quotation_number, '-', 3) AS INTEGER) "
                "ELSE NULL END"
                "), 0) "
                "FROM quotations WHERE quotation_number LIKE :pattern"
            ),
            {"pattern": f"{prefix}%"},
            {"pattern": pattern},
        )
        number = int(result.scalar_one())
        return f"{prefix}{number:04d}"
        next_number = int(result.scalar_one()) + 1
        return f"{prefix}{next_number:04d}"

    async def accept(
        self,
        quotation_id: uuid.UUID,
    ) -> Quotation | None:
        """Mark quotation as accepted."""
        """Accept a valid quotation after locking its company engagement."""
        """Accept a quotation using the shared engagement-first lock order."""
        # Read immutable parent keys first; lifecycle writers then lock the
        # engagement before the quotation to prevent lock-order deadlocks.
        quotation_ref_result = await self.db.execute(
            select(Quotation.engagement_id, Quotation.company_id).where(
                Quotation.id == quotation_id
            )
        )
        quotation_ref = quotation_ref_result.one_or_none()
        if quotation_ref is None:
            return None

        engagement_result = await self.db.execute(
            select(Engagement)
            .where(
                Engagement.id == quotation_ref.engagement_id,
                Engagement.company_id == quotation_ref.company_id,
                Engagement.is_active.is_(True),
            )
            .with_for_update()
        )
        engagement = engagement_result.scalar_one_or_none()
        if engagement is None:
            raise ValueError(
                "Quotation engagement is missing, inactive, or belongs to another company."
            )
            raise ValueError("Quotation engagement is missing, inactive, or belongs to another company.")

        quotation_result = await self.db.execute(
            select(Quotation).where(Quotation.id == quotation_id).with_for_update()
        )
        quotation = quotation_result.scalar_one_or_none()
        if quotation is None:
            return None
        if (
            quotation.engagement_id != engagement.id
            or quotation.company_id != engagement.company_id
        ):
            raise ValueError("Quotation parent changed while acceptance was being processed.")
        if quotation.status not in {"DRAFT", "SENT"}:
            raise CommercialConflictError(
                f"Cannot accept a quotation in {quotation.status} state."
            )
        if quotation.valid_until is None or quotation.valid_until < date.today():
            raise CommercialConflictError(
                "An expired quotation cannot be accepted; issue a renewed quotation."
            )
        if engagement.engagement_status != EngagementStatus.QUOTED:
            raise CommercialConflictError(
                "Only a quotation for a QUOTED engagement can be accepted."
            )

        accepted = await self.update_instance(
            quotation,
            status="ACCEPTED",
            accepted_date=date.today(),
        )
        await self.db.flush()
        q = quotation_result.scalar_one_or_none()
        if not q:
            return None
        if q.status == "ACCEPTED":
            return q
        if q.status not in {"DRAFT", "SENT"}:
            raise CommercialConflictError(f"Cannot accept a quotation in {q.status} state")
        if q.valid_until is not None and q.valid_until < date.today():
            raise CommercialConflictError("Quotation has expired")
        engagement_result = await self.db.execute(
            select(Engagement)
            .where(
                Engagement.id == q.engagement_id,
                Engagement.company_id == q.company_id,
            )
            .with_for_update()
        )
        engagement = engagement_result.scalar_one_or_none()
        if engagement is None:
            raise ValueError("Quotation engagement no longer exists")
        if engagement.engagement_status != EngagementStatus.QUOTED:
            raise CommercialConflictError(
                f"Cannot accept a quotation while engagement is {engagement.engagement_status}"
            )
        accepted = await self.update_instance(q, status="ACCEPTED", accepted_date=date.today())
        await EngagementService(self.db).update_instance(
            engagement,
            engagement_status=EngagementStatus.CONFIRMED,
            confirmed_date=date.today(),
            confirmed_fee_bdt=q.total_bdt,
        if q is None:
            return None
        if q.engagement_id != engagement.id or q.company_id != engagement.company_id:
            raise ValueError("Quotation parent changed while the acceptance was being processed.")
        if q.status not in {"DRAFT", "SENT"}:
            raise CommercialConflictError(f"Cannot accept a quotation in {q.status} state.")
        if q.valid_until is None or q.valid_until < date.today():
            raise CommercialConflictError("An expired quotation cannot be accepted; issue a renewed quotation.")
        if engagement.engagement_status != EngagementStatus.QUOTED:
            raise CommercialConflictError("Only a quotation for a QUOTED engagement can be accepted.")

        accepted = await self.update_instance(q, status="ACCEPTED", accepted_date=date.today())
        await EngagementService(self.db).advance_status(
            engagement.id,
            EngagementStatus.CONFIRMED,
            fee_bdt=quotation.total_bdt,
        )
        return accepted

    async def reject(
        self,
        quotation_id: uuid.UUID,
        reason: str | None = None,
        rejected_by: uuid.UUID | None = None,
    ) -> Quotation | None:
        """Mark quotation as rejected."""
        """Reject a quotation while serializing against engagement lifecycle writes."""
        """Reject a quotation while serializing against parent lifecycle writes."""
        quotation_ref_result = await self.db.execute(
            select(Quotation.engagement_id, Quotation.company_id).where(
                Quotation.id == quotation_id
            )
        )
        quotation_ref = quotation_ref_result.one_or_none()
        if quotation_ref is None:
            return None

        engagement_result = await self.db.execute(
            select(Engagement)
            .where(
                Engagement.id == quotation_ref.engagement_id,
                Engagement.company_id == quotation_ref.company_id,
                Engagement.is_active.is_(True),
            )
            .with_for_update()
        )
        engagement = engagement_result.scalar_one_or_none()
        if engagement is None:
            raise ValueError(
                "Quotation engagement is missing, inactive, or belongs to another company."
            )
            raise ValueError("Quotation engagement is missing, inactive, or belongs to another company.")

        quotation_result = await self.db.execute(
            select(Quotation).where(Quotation.id == quotation_id).with_for_update()
        )
        quotation = quotation_result.scalar_one_or_none()
        if quotation is None:
            return None
        if (
            quotation.engagement_id != engagement.id
            or quotation.company_id != engagement.company_id
        ):
            raise ValueError("Quotation parent changed while rejection was being processed.")
        if quotation.status not in {"DRAFT", "SENT"}:
            raise CommercialConflictError(
                f"Cannot reject a quotation in {quotation.status} state."
            )
        q = quotation_result.scalar_one_or_none()
        if not q:
            return None
        if q.status not in {"DRAFT", "SENT"}:
            raise CommercialConflictError(f"Cannot reject a quotation in {q.status} state")
        return await self.update_instance(q, status="REJECTED", rejection_reason=reason, rejected_by=rejected_by)  # COM-002
        if q is None:
            return None
        if q.engagement_id != engagement.id or q.company_id != engagement.company_id:
            raise ValueError("Quotation parent changed while the rejection was being processed.")
        if q.status not in {"DRAFT", "SENT"}:
            raise CommercialConflictError(f"Cannot reject a quotation in {q.status} state.")

        return await self.update_instance(
            quotation,
            status="REJECTED",
            rejection_reason=reason,
            rejected_by=rejected_by,
        )


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
        description: str | None = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        due_date: date | None = None,
        assigned_to: uuid.UUID | None = None,
        created_by: uuid.UUID | None = None,
        source_flag_id: uuid.UUID | None = None,
        source_rescue_step_id: uuid.UUID | None = None,
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
        status: TaskStatus | None = None,
        assigned_to: uuid.UUID | None = None,
    ) -> list[Task]:
        """Get tasks for a company with optional filters."""
        filters = [Task.company_id == company_id, Task.is_active]
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
        company_id: uuid.UUID,
    ) -> Task | None:
        """Complete only a task belonging to the already-authorized company."""
        from datetime import datetime
        task_result = await self.db.execute(
            select(Task).where(Task.id == task_id, Task.is_active).with_for_update()
            select(Task)
            .where(
                Task.id == task_id,
                Task.company_id == company_id,
                Task.is_active.is_(True),
            )
            .where(Task.id == task_id)
            .with_for_update()
        )
        task = task_result.scalar_one_or_none()
        if not task:
            return None
        if task.task_status not in {TaskStatus.PENDING, TaskStatus.IN_PROGRESS}:
            raise CommercialConflictError(
                f"Cannot complete a task in {task.task_status} state"
            )
        return await self.update_instance(
            task,
            task_status=TaskStatus.COMPLETED,
            completed_at=datetime.now(UTC),
        )