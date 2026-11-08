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
        Revenue pipeline from the finance-ledger-backed vw_revenue_pipeline view.

        Estimated, quoted, and confirmed values are engagement aggregates.
        Invoiced values come from non-draft/non-void invoices; collected values
        come from allocations against settled payments. These are not bank-
        statement reconciled cash receipts.
        """
        result = await self.db.execute(text("SELECT * FROM vw_revenue_pipeline"))
        rows = [dict(r) for r in result.mappings().all()]

        zero = Decimal("0.00")
        pipeline: dict[str, dict[str, Any]] = {
            "COMPLIANCE_PACKAGE": {
                "stages": {},
                "total_estimated": zero,
                "total_confirmed": zero,
                "total_invoiced": zero,
                "total_collected": zero,
            },
            "STRUCTURED_REGULARIZATION": {
                "stages": {},
                "total_estimated": zero,
                "total_confirmed": zero,
                "total_invoiced": zero,
                "total_collected": zero,
            },
            "CORPORATE_RESCUE": {
                "stages": {},
                "total_estimated": zero,
                "total_confirmed": zero,
                "total_invoiced": zero,
                "total_collected": zero,
            },
        }
        for row in rows:
            tier = str(row.get("revenue_tier", ""))
            if tier not in pipeline:
                continue
            stage = str(row.get("engagement_status", ""))
            estimated = Decimal(str(row.get("total_estimated_bdt") or 0))
            quoted = Decimal(str(row.get("total_quoted_bdt") or 0))
            confirmed = Decimal(str(row.get("total_confirmed_bdt") or 0))
            invoiced = Decimal(str(row.get("total_invoiced_bdt") or 0))
            collected = Decimal(str(row.get("total_collected_bdt") or 0))
            pipeline[tier]["stages"][stage] = {
                "count": row.get("engagement_count", 0),
                "estimated_bdt": estimated,
                "quoted_bdt": quoted,
                "confirmed_bdt": confirmed,
                "invoiced_bdt": invoiced,
                "collected_bdt": collected,
            }
            pipeline[tier]["total_estimated"] += estimated
            pipeline[tier]["total_confirmed"] += confirmed
            pipeline[tier]["total_invoiced"] += invoiced
            pipeline[tier]["total_collected"] += collected

        grand_total_estimated = sum(
            (v["total_estimated"] for v in pipeline.values()), zero
        )
        grand_total_confirmed = sum(
            (v["total_confirmed"] for v in pipeline.values()), zero
        )
        grand_total_invoiced = sum(
            (v["total_invoiced"] for v in pipeline.values()), zero
        )
        grand_total_collected = sum(
            (v["total_collected"] for v in pipeline.values()), zero
        )
        return {
            "by_tier": pipeline,
            "grand_total_estimated_bdt": grand_total_estimated,
            "grand_total_confirmed_bdt": grand_total_confirmed,
            "grand_total_invoiced_bdt": grand_total_invoiced,
            "grand_total_collected_bdt": grand_total_collected,
            "collection_rate": (
                round(grand_total_collected / grand_total_confirmed * 100, 1)
                if grand_total_confirmed > zero else 0
            ),
            # Engagement aggregates are not independently verified receipts.
            "revenue_data_basis": "ENGAGEMENT_RECORDED_AGGREGATES",
            "collected_cash_reconciled": False,
            "engagement_amounts_source": "ENGAGEMENT_RECORDS",
            "invoiced_amounts_source": "NON_DRAFT_NON_VOID_FINANCE_INVOICES",
            "collected_amounts_source": "SETTLED_FINANCE_PAYMENT_ALLOCATIONS",
            "bank_reconciliation_verified": False,
        }

    async def get_conversion_funnel(self) -> dict:
        """Return engagement conversion metrics from a single aggregate query."""
        result = await self.db.execute(
            select(
                Engagement.engagement_status,
                func.count().label("count"),
                func.sum(Engagement.estimated_fee_bdt).label("value"),
            )
            .where(Engagement.is_active.is_(True))
            .group_by(Engagement.engagement_status)
        )
        stages: dict[str, dict[str, Any]] = {
            str(row.engagement_status): {
                "count": row.count,
                "value": Decimal(str(row.value or 0)),
            }
            for row in result.all()
        }
        total_identified = stages.get("IDENTIFIED", {}).get("count", 0)
        total_confirmed = stages.get("CONFIRMED", {}).get("count", 0)
        total_completed = stages.get("COMPLETED", {}).get("count", 0)
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
        fee_bdt: Decimal | None = None,
        note: str | None = None,
        locked_engagement: Engagement | None = None,
    ) -> Engagement | None:
        """Advance an engagement only through the canonical lifecycle."""
        engagement: Engagement | None
        if locked_engagement is not None:
            if locked_engagement.id != engagement_id or not locked_engagement.is_active:
                return None
            engagement = locked_engagement
        else:
            result = await self.db.execute(
                select(Engagement)
                .where(
                    Engagement.id == engagement_id,
                    Engagement.is_active.is_(True),
                )
                .execution_options(populate_existing=True)
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
            issued_count = await self.db.execute(
                select(func.count())
                .select_from(Quotation)
                .where(
                    Quotation.engagement_id == engagement_id,
                    Quotation.status.in_({"DRAFT", "SENT", "ACCEPTED"}),
                )
            )
            if issued_count.scalar_one() < 1:
                raise CommercialConflictError(
                    "A quotation record is required before moving an engagement to QUOTED."
                )

        if new_status == EngagementStatus.CONFIRMED:
            accepted_count = await self.db.execute(
                select(func.count())
                .select_from(Quotation)
                .where(
                    Quotation.engagement_id == engagement_id,
                    Quotation.status == "ACCEPTED",
                )
            )
            if accepted_count.scalar_one() < 1:
                raise CommercialConflictError(
                    "An accepted quotation is required before confirming an engagement."
                )

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
        if not 7 <= valid_days <= 90:
            raise ValueError("Quotation validity must be between 7 and 90 days.")

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
        if engagement.engagement_status not in {
            EngagementStatus.IDENTIFIED,
            EngagementStatus.QUOTED,
        }:
            raise CommercialConflictError(
                "A quotation can only be created for an identified or quoted engagement."
            )

        professional_fee = Decimal(str(professional_fee_bdt)).quantize(Decimal("0.01"))
        government_fee = Decimal(str(government_fee_bdt)).quantize(Decimal("0.01"))
        vat_amount = Decimal(str(vat_bdt)).quantize(Decimal("0.01"))
        if professional_fee <= 0 or government_fee < 0 or vat_amount < 0:
            raise ValueError("Quotation fees must be positive or zero as applicable.")
        total_bdt = (professional_fee + government_fee + vat_amount).quantize(Decimal("0.01"))
        quotation_number = await self._next_quotation_number()

        quotation = await self.create(
            engagement_id=engagement_id,
            company_id=company_id,
            quotation_number=quotation_number,
            quotation_date=date.today(),
            valid_until=date.today() + timedelta(days=valid_days),
            professional_fee_bdt=professional_fee,
            government_fee_bdt=government_fee,
            vat_bdt=vat_amount,
            total_bdt=total_bdt,
            status="DRAFT",
            line_items=line_items,
            notes=notes,
        )
        engagement.quoted_fee_bdt = total_bdt
        if engagement.engagement_status == EngagementStatus.IDENTIFIED:
            engagement.engagement_status = EngagementStatus.QUOTED
            engagement.quoted_date = date.today()
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
        pattern = f"{prefix}%"
        result = await self.db.execute(
            text(
                "SELECT COALESCE(MAX("
                "CASE WHEN SPLIT_PART(quotation_number, '-', 3) ~ '^[0-9]+$' "
                "THEN CAST(SPLIT_PART(quotation_number, '-', 3) AS INTEGER) "
                "ELSE NULL END"
                "), 0) + 1 "
                "FROM quotations WHERE quotation_number LIKE :pattern"
            ),
            {"pattern": pattern},
        )
        next_number = int(result.scalar_one())
        return f"{prefix}{next_number:04d}"

    async def accept(
        self,
        quotation_id: uuid.UUID,
    ) -> Quotation | None:
        """Accept a valid quotation while serializing parent lifecycle changes."""
        parent_result = await self.db.execute(
            select(Quotation.engagement_id, Quotation.company_id).where(
                Quotation.id == quotation_id
            )
        )
        parent = parent_result.one_or_none()
        if parent is None:
            return None

        # Lock the parent first: every quotation lifecycle transition uses the
        # same engagement -> quotation lock order to avoid deadlocks.
        engagement_result = await self.db.execute(
            select(Engagement)
            .where(
                Engagement.id == parent.engagement_id,
                Engagement.company_id == parent.company_id,
                Engagement.is_active.is_(True),
            )
            .with_for_update()
        )
        engagement = engagement_result.scalar_one_or_none()
        if engagement is None:
            raise ValueError(
                "Quotation engagement is missing, inactive, or belongs to another company."
            )

        quotation_result = await self.db.execute(
            select(Quotation)
            .where(
                Quotation.id == quotation_id,
                Quotation.company_id == engagement.company_id,
            )
            .with_for_update()
        )
        quotation = quotation_result.scalar_one_or_none()
        if quotation is None:
            return None
        if (
            quotation.engagement_id != engagement.id
            or quotation.company_id != engagement.company_id
        ):
            raise ValueError(
                "Quotation parent changed while acceptance was being processed."
            )
        if quotation.status == "ACCEPTED":
            return quotation
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
        await EngagementService(self.db).advance_status(
            engagement.id,
            EngagementStatus.CONFIRMED,
            fee_bdt=quotation.total_bdt,
            locked_engagement=engagement,
        )
        return accepted

    async def reject(
        self,
        quotation_id: uuid.UUID,
        reason: str | None = None,
        rejected_by: uuid.UUID | None = None,
    ) -> Quotation | None:
        """Reject a draft or sent quotation while locking its engagement first."""
        parent_result = await self.db.execute(
            select(Quotation.engagement_id, Quotation.company_id).where(
                Quotation.id == quotation_id
            )
        )
        parent = parent_result.one_or_none()
        if parent is None:
            return None

        engagement_result = await self.db.execute(
            select(Engagement)
            .where(
                Engagement.id == parent.engagement_id,
                Engagement.company_id == parent.company_id,
                Engagement.is_active.is_(True),
            )
            .with_for_update()
        )
        engagement = engagement_result.scalar_one_or_none()
        if engagement is None:
            raise ValueError(
                "Quotation engagement is missing, inactive, or belongs to another company."
            )

        quotation_result = await self.db.execute(
            select(Quotation)
            .where(
                Quotation.id == quotation_id,
                Quotation.company_id == engagement.company_id,
            )
            .with_for_update()
        )
        quotation = quotation_result.scalar_one_or_none()
        if quotation is None:
            return None
        if (
            quotation.engagement_id != engagement.id
            or quotation.company_id != engagement.company_id
        ):
            raise ValueError(
                "Quotation parent changed while rejection was being processed."
            )
        if quotation.status not in {"DRAFT", "SENT"}:
            raise CommercialConflictError(
                f"Cannot reject a quotation in {quotation.status} state."
            )

        return await self.update_instance(
            quotation,
            status="REJECTED",
            rejection_reason=reason,
            rejected_by=rejected_by,
        )  # COM-002


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
        *,
        completion_note: str | None = None,
    ) -> Task | None:
        """Complete only an active task belonging to the authorized company."""
        from datetime import datetime

        """Complete only a task belonging to the already-authorized company."""
        task_result = await self.db.execute(
            select(Task)
            .where(
                Task.id == task_id,
                Task.company_id == company_id,
                Task.is_active.is_(True),
            )
            .with_for_update()
        )
        task = task_result.scalar_one_or_none()
        if task is None:
            return None
        if task.task_status not in {TaskStatus.PENDING, TaskStatus.IN_PROGRESS}:
            raise CommercialConflictError(
                f"Cannot complete a task in {task.task_status} state."
            )
        normalized_note = completion_note.strip() if completion_note else None
        if normalized_note is not None and len(normalized_note) > 2000:
            raise ValueError("Completion note must not exceed 2,000 characters.")
        return await self.update_instance(
            task,
            task_status=TaskStatus.COMPLETED,
            completed_at=datetime.now(UTC),
            completion_note=normalized_note,
        )
