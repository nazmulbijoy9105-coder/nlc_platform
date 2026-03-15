from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.core.schemas import create_data_response
from app.models import Document, DocumentStatus, DocumentType

import uuid


def generate_uuid() -> str:
    return str(uuid.uuid4())


router = APIRouter(prefix="/documents", tags=["Documents"])


class DocumentCreate(BaseModel):
    company_id: str
    document_type: DocumentType
    title: str
    content: str | None = None


class DocumentUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    status: DocumentStatus | None = None


class DocumentResponse(BaseModel):
    id: str
    company_id: str
    document_type: str
    title: str
    status: str
    content: str | None
    ai_generated: str
    approved_by_id: str | None
    released_at: datetime | None


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_document(
    request: DocumentCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    document = Document(
        id=generate_uuid(),
        company_id=request.company_id,
        document_type=request.document_type,
        title=request.title,
        content=request.content,
        created_by_id=current_user.id,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)
    return create_data_response(
        data=DocumentResponse.model_validate(document),
        message="Document created successfully",
    )


@router.get("")
async def list_documents(
    company_id: str | None = None,
    status: DocumentStatus | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Document)
    if company_id:
        query = query.where(Document.company_id == company_id)
    if status:
        query = query.where(Document.status == status)

    result = await db.execute(query)
    documents = result.scalars().all()
    return create_data_response(data=[DocumentResponse.model_validate(d) for d in documents])


@router.get("/{document_id}")
async def get_document(document_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return create_data_response(data=DocumentResponse.model_validate(document))


@router.put("/{document_id}")
async def update_document(
    document_id: str,
    request: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(document, field, value)

    document.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(document)
    return create_data_response(
        data=DocumentResponse.model_validate(document),
        message="Document updated successfully",
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    await db.delete(document)
    await db.commit()


@router.post("/{document_id}/approve")
async def approve_document(
    document_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    document.status = DocumentStatus.APPROVED
    document.approved_by_id = current_user.id
    document.approved_at = datetime.now(timezone.utc)
    document.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return create_data_response(
        data=DocumentResponse.model_validate(document),
        message="Document approved successfully",
    )


@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return create_data_response(
        data={
            "document_id": document.id,
            "title": document.title,
            "content": document.content,
            "file_url": document.file_url,
            "status": document.status.value,
        }
    )
