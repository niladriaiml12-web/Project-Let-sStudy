"""
app/schemas/ingest.py

Pydantic request/response models for the document ingestion pipeline.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.db.sql_models import DocumentStatus, DocumentType


class IngestResponse(BaseModel):
    """Response returned after a successful document upload."""
    doc_id: str = Field(..., description="Unique document ID (UUID) for status tracking")
    filename: str = Field(..., description="Original filename of the uploaded document")
    subject: str = Field(..., description="Subject the document was ingested into")
    branch: str = Field(..., description="Branch (tenant) the document belongs to")
    status: DocumentStatus = Field(..., description="Initial processing status")
    message: str = Field(..., description="Human-readable status message")

    model_config = {"from_attributes": True}


class DocumentStatusResponse(BaseModel):
    """Detailed status of a document's processing lifecycle."""
    doc_id: str
    original_filename: str
    doc_type: DocumentType
    status: DocumentStatus
    chunk_count: Optional[int] = Field(None, description="Number of chunks indexed (available after COMPLETED)")
    error_message: Optional[str] = Field(None, description="Error details if status=FAILED")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DeleteDocumentResponse(BaseModel):
    """Response after deleting a document's chunks from ChromaDB."""
    doc_id: str
    message: str
    chunks_removed: int
