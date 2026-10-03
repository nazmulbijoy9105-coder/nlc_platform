"""
NLC — GATE E5: Document & Evidence Integrity Tests
Proves that unapproved AI documents cannot be downloaded or released.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.document_service import DocumentService
from app.models.documents import Document
from app.models.enums import DocumentType

@pytest.fixture
def mock_db():
    return AsyncMock()

@pytest.fixture
def doc_service(mock_db):
    return DocumentService(mock_db)

@pytest.fixture
def unapproved_ai_doc():
    return Document(
        id="doc-1",
        s3_key="s3/path/doc.txt",
        ai_generated=True,
        human_approved=False,
        document_type=DocumentType.AGM_MINUTES
    )

@pytest.fixture
def approved_ai_doc():
    return Document(
        id="doc-2",
        s3_key="s3/path/doc.txt",
        ai_generated=True,
        human_approved=True,
        document_type=DocumentType.AGM_MINUTES
    )

@pytest.mark.asyncio
async def test_unapproved_ai_doc_cannot_get_presigned_url(doc_service, unapproved_ai_doc):
    doc_service.get_by_id_or_404 = AsyncMock(return_value=unapproved_ai_doc)
    with pytest.raises(ValueError, match="AI Constitution violation"):
        await doc_service.get_presigned_url("doc-1")

@pytest.mark.asyncio
async def test_unapproved_ai_doc_cannot_generate_pdf(doc_service, unapproved_ai_doc):
    doc_service.get_by_id_or_404 = AsyncMock(return_value=unapproved_ai_doc)
    with pytest.raises(ValueError, match="AI Constitution violation"):
        await doc_service.generate_pdf_and_presign("doc-1")

@pytest.mark.asyncio
async def test_unapproved_ai_doc_cannot_release_to_client(doc_service, unapproved_ai_doc):
    doc_service.get_by_id = AsyncMock(return_value=unapproved_ai_doc)
    with pytest.raises(ValueError, match="AI Constitution violation"):
        await doc_service.release_to_client("doc-1", "user-1")
