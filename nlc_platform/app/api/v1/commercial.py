from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.core.schemas import create_data_response
from app.models import Engagement, EngagementStatus, Pipeline, PipelineStage, Invoice, InvoiceStatus

import uuid


def generate_uuid() -> str:
    return str(uuid.uuid4())


router = APIRouter(prefix="/commercial", tags=["Commercial"])


class EngagementCreate(BaseModel):
    company_id: str
    service_type: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    monthly_fee: float | None = None
    notes: str | None = None


class EngagementResponse(BaseModel):
    id: str
    company_id: str
    status: str
    service_type: str | None
    start_date: datetime | None
    end_date: datetime | None
    monthly_fee: float | None


class PipelineCreate(BaseModel):
    engagement_id: str
    stage: PipelineStage = PipelineStage.LEAD
    value: float | None = None
    expected_close_date: datetime | None = None
    probability: int = 0
    notes: str | None = None


class PipelineUpdate(BaseModel):
    stage: PipelineStage | None = None
    value: float | None = None
    expected_close_date: datetime | None = None
    probability: int | None = None
    notes: str | None = None


class PipelineResponse(BaseModel):
    id: str
    engagement_id: str
    stage: str
    value: float | None
    probability: int


@router.post("/engagements", status_code=status.HTTP_201_CREATED)
async def create_engagement(
    request: EngagementCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    engagement = Engagement(
        id=generate_uuid(),
        company_id=request.company_id,
        service_type=request.service_type,
        start_date=request.start_date,
        end_date=request.end_date,
        monthly_fee=request.monthly_fee,
        notes=request.notes,
        created_by_id=current_user.id,
    )
    db.add(engagement)
    await db.commit()
    await db.refresh(engagement)
    return create_data_response(
        data=EngagementResponse.model_validate(engagement),
        message="Engagement created successfully",
    )


@router.get("/engagements")
async def list_engagements(
    status: EngagementStatus | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Engagement)
    if status:
        query = query.where(Engagement.status == status)
    result = await db.execute(query)
    engagements = result.scalars().all()
    return create_data_response(data=[EngagementResponse.model_validate(e) for e in engagements])


@router.get("/engagements/{engagement_id}")
async def get_engagement(engagement_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Engagement).where(Engagement.id == engagement_id))
    engagement = result.scalar_one_or_none()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    return create_data_response(data=EngagementResponse.model_validate(engagement))


@router.put("/engagements/{engagement_id}")
async def update_engagement(
    engagement_id: str,
    request: EngagementCreate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Engagement).where(Engagement.id == engagement_id))
    engagement = result.scalar_one_or_none()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(engagement, field, value)

    engagement.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(engagement)
    return create_data_response(
        data=EngagementResponse.model_validate(engagement),
        message="Engagement updated successfully",
    )


@router.post("/pipeline", status_code=status.HTTP_201_CREATED)
async def create_pipeline(
    request: PipelineCreate,
    db: AsyncSession = Depends(get_db),
):
    pipeline = Pipeline(
        id=generate_uuid(),
        engagement_id=request.engagement_id,
        stage=request.stage,
        value=request.value,
        expected_close_date=request.expected_close_date,
        probability=request.probability,
        notes=request.notes,
    )
    db.add(pipeline)
    await db.commit()
    await db.refresh(pipeline)
    return create_data_response(
        data=PipelineResponse.model_validate(pipeline),
        message="Pipeline created successfully",
    )


@router.get("/pipeline")
async def list_pipelines(
    stage: PipelineStage | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Pipeline)
    if stage:
        query = query.where(Pipeline.stage == stage)
    result = await db.execute(query)
    pipelines = result.scalars().all()
    return create_data_response(data=[PipelineResponse.model_validate(p) for p in pipelines])


@router.put("/pipeline/{pipeline_id}")
async def update_pipeline(
    pipeline_id: str,
    request: PipelineUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(pipeline, field, value)

    pipeline.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(pipeline)
    return create_data_response(
        data=PipelineResponse.model_validate(pipeline),
        message="Pipeline updated successfully",
    )


@router.get("/dashboard")
async def get_commercial_dashboard(db: AsyncSession = Depends(get_db)):
    total_engagements = await db.execute(select(Engagement))
    total_engagements_count = len(total_engagements.scalars().all())

    total_pipeline = await db.execute(select(Pipeline))
    pipeline_items = total_pipeline.scalars().all()
    total_value = sum(p.value or 0 for p in pipeline_items)

    won_pipeline = [p for p in pipeline_items if p.stage == PipelineStage.WON]
    won_value = sum(p.value or 0 for p in won_pipeline)

    return create_data_response(
        data={
            "total_engagements": total_engagements_count,
            "total_pipeline_value": total_value,
            "won_value": won_value,
            "pipeline_by_stage": {
                stage.value: len([p for p in pipeline_items if p.stage == stage])
                for stage in PipelineStage
            },
        }
    )
