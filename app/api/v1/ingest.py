"""
app/api/v1/ingest.py

Document ingestion endpoints.
Handles upload of images/PDFs, triggers OCR + embedding pipeline,
and tracks processing status per document.

All endpoints require X-API-Key authentication.
The authenticated group's branch_code is used for ChromaDB isolation.
"""
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select

from app.db.sql_models import Document, DocumentStatus, DocumentType, Subject
from app.dependencies import AuthenticatedGroup, DbSession, SettingsDep
from app.schemas.ingest import DeleteDocumentResponse, DocumentStatusResponse, IngestResponse
from app.services.ingest_service import delete_document_chunks, ingest_document
from app.services.ocr_service import extract_text_from_file

router = APIRouter()

# Allowed file extensions for upload
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}


# =============================================================================
# Background Task: OCR + Embedding Pipeline
# =============================================================================

async def _process_document(
    doc_id: str,
    file_path: str,
    filename: str,
    branch: str,
    subject_code: str,
    doc_type: str,
) -> None:
    """
    Background task that runs the full OCR + ingestion pipeline.
    Updates the Document record status throughout the lifecycle:
    PENDING → PROCESSING → COMPLETED | FAILED
    """
    from app.db.sql_client import get_db_context

    async with get_db_context() as db:
        # Fetch document record
        result = await db.execute(select(Document).where(Document.id == doc_id))
        document = result.scalar_one_or_none()
        if not document:
            return

        try:
            # --- PROCESSING ---
            document.status = DocumentStatus.PROCESSING
            await db.commit()

            # Step 1: OCR
            with open(file_path, "rb") as f:
                file_bytes = f.read()

            markdown_text = await extract_text_from_file(
                file_bytes=file_bytes,
                filename=filename,
            )

            # Store OCR text for debugging (truncated to 10k chars for DB)
            document.ocr_text = markdown_text[:10000] if markdown_text else ""

            # Step 2: Chunk + Embed + Upsert to ChromaDB
            chunk_count = await ingest_document(
                text=markdown_text,
                branch=branch,
                subject=subject_code,
                doc_id=doc_id,
                source_file=filename,
                doc_type=doc_type,
            )

            # --- COMPLETED ---
            document.status = DocumentStatus.COMPLETED
            document.chunk_count = chunk_count
            await db.commit()

        except Exception as e:
            # --- FAILED ---
            document.status = DocumentStatus.FAILED
            document.error_message = str(e)[:1000]  # Truncate long errors
            await db.commit()
            raise


# =============================================================================
# Endpoints
# =============================================================================

@router.post(
    "/upload",
    response_model=IngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a document (image/PDF) for OCR and indexing",
)
async def upload_document(
    background_tasks: BackgroundTasks,
    db: DbSession,
    settings: SettingsDep,
    group: AuthenticatedGroup,
    subject_code: str = Form(..., description="Subject code (must exist in your group)"),
    doc_type: DocumentType = Form(default=DocumentType.CLASS_NOTES),
    file: UploadFile = File(..., description="Image (JPEG/PNG/WebP) or PDF to ingest"),
):
    """
    Uploads a document for OCR and vector indexing.
    
    Processing is asynchronous — the endpoint returns immediately with a `doc_id`.
    Poll `/ingest/status/{doc_id}` to check when processing is complete.
    
    **Multi-tenant isolation:** Documents are stored in the ChromaDB collection
    for your group's `branch_code` + the provided `subject_code`.
    """
    # -------------------------------------------------------------------------
    # Validate file extension
    # -------------------------------------------------------------------------
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{suffix}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # -------------------------------------------------------------------------
    # Validate file size
    # -------------------------------------------------------------------------
    file_bytes = await file.read()
    if len(file_bytes) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB",
        )

    # -------------------------------------------------------------------------
    # Validate subject belongs to this group
    # -------------------------------------------------------------------------
    subject_result = await db.execute(
        select(Subject).where(
            Subject.group_id == group.id,
            Subject.subject_code == subject_code,
        )
    )
    subject = subject_result.scalar_one_or_none()
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Subject '{subject_code}' not found in group '{group.name}'. "
                f"Create it first via POST /api/v1/groups/{group.id}/subjects"
            ),
        )

    # -------------------------------------------------------------------------
    # Save uploaded file to disk (UUID-based name to avoid collisions)
    # -------------------------------------------------------------------------
    doc_id = str(uuid.uuid4())
    stored_filename = f"{doc_id}{suffix}"
    file_path = Path(settings.upload_dir) / stored_filename

    with open(file_path, "wb") as f:
        f.write(file_bytes)

    # -------------------------------------------------------------------------
    # Create Document record in SQL (status: PENDING)
    # -------------------------------------------------------------------------
    document = Document(
        id=doc_id,
        subject_id=subject.id,
        original_filename=file.filename or stored_filename,
        stored_filename=stored_filename,
        doc_type=doc_type,
        status=DocumentStatus.PENDING,
    )
    db.add(document)
    await db.commit()

    # -------------------------------------------------------------------------
    # Schedule background OCR + embedding task
    # -------------------------------------------------------------------------
    background_tasks.add_task(
        _process_document,
        doc_id=doc_id,
        file_path=str(file_path),
        filename=file.filename or stored_filename,
        branch=group.branch_code,
        subject_code=subject_code,
        doc_type=doc_type.value,
    )

    return IngestResponse(
        doc_id=doc_id,
        filename=file.filename or stored_filename,
        subject=subject_code,
        branch=group.branch_code,
        status=DocumentStatus.PENDING,
        message="Document uploaded successfully. OCR and indexing started in background.",
    )


@router.get(
    "/status/{doc_id}",
    response_model=DocumentStatusResponse,
    summary="Check document processing status",
)
async def get_document_status(doc_id: str, db: DbSession, group: AuthenticatedGroup):
    """
    Polls the processing status of an uploaded document.
    
    Status lifecycle: PENDING → PROCESSING → COMPLETED | FAILED
    
    Once COMPLETED, `chunk_count` shows how many chunks were indexed in ChromaDB.
    """
    result = await db.execute(
        select(Document)
        .join(Document.subject)
        .where(Document.id == doc_id, Subject.group_id == group.id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=404,
            detail=f"Document '{doc_id}' not found or does not belong to your group.",
        )

    return DocumentStatusResponse(
        doc_id=document.id,
        original_filename=document.original_filename,
        doc_type=document.doc_type,
        status=document.status,
        chunk_count=document.chunk_count,
        error_message=document.error_message,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


@router.delete(
    "/{doc_id}",
    response_model=DeleteDocumentResponse,
    summary="Delete a document and its indexed chunks",
)
async def delete_document(doc_id: str, db: DbSession, group: AuthenticatedGroup):
    """
    Deletes a document's SQL record AND removes all its chunks from ChromaDB.
    
    Use this to re-ingest a corrected version of a document.
    """
    # Fetch document and verify ownership
    result = await db.execute(
        select(Document)
        .join(Document.subject)
        .where(Document.id == doc_id, Subject.group_id == group.id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=404,
            detail=f"Document '{doc_id}' not found or does not belong to your group.",
        )

    subject_code = document.subject.subject_code

    # Remove chunks from ChromaDB
    chunks_removed = await delete_document_chunks(
        doc_id=doc_id,
        branch=group.branch_code,
        subject=subject_code,
    )

    # Remove SQL record
    await db.delete(document)

    return DeleteDocumentResponse(
        doc_id=doc_id,
        message=f"Document deleted successfully.",
        chunks_removed=chunks_removed,
    )
