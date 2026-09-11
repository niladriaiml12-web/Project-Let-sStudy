"""
app/services/ingest_service.py

Document ingestion pipeline:
  Raw text (Markdown) → LangChain chunking → Google embeddings → ChromaDB upsert

This is the write side of the RAG system. Every chunk is stored with
rich metadata to enable strict multi-tenant filtering on retrieval.
"""
import uuid
from datetime import datetime, timezone
from typing import List

import structlog
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_settings
from app.db.chroma_client import get_or_create_collection
from app.services.llm_service import embed_batch

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Chunk Metadata Schema
# ---------------------------------------------------------------------------
# Each ChromaDB document stores this metadata for filtering and attribution:
# {
#   "branch":       str  — tenant branch code (e.g., "CSE_AIML")
#   "subject":      str  — subject code (e.g., "ML")
#   "doc_id":       str  — UUID of the parent Document record
#   "source_file":  str  — original filename
#   "doc_type":     str  — "class_notes" | "pyq" | etc.
#   "chunk_index":  int  — chunk position within document
#   "ingested_at":  str  — ISO timestamp of ingestion
# }


async def ingest_document(
    text: str,
    branch: str,
    subject: str,
    doc_id: str,
    source_file: str,
    doc_type: str = "class_notes",
) -> int:
    """
    Main ingestion pipeline: chunks Markdown text, embeds with Google API,
    and upserts all chunks into the appropriate ChromaDB collection.
    
    Args:
        text:        Full Markdown text from OCR
        branch:      Tenant branch code (e.g., "CSE_AIML") — used for isolation
        subject:     Subject code (e.g., "ML") — defines the collection
        doc_id:      UUID string linking chunks back to the SQL Document record
        source_file: Original filename for citation in answers
        doc_type:    Type of document ("class_notes", "pyq", etc.)
    
    Returns:
        Number of chunks successfully indexed in ChromaDB
    
    Raises:
        RuntimeError: If embedding or ChromaDB upsert fails
    """
    settings = get_settings()

    # -------------------------------------------------------------------------
    # Step 1: Chunk the text
    # -------------------------------------------------------------------------
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],  # Prefer paragraph boundaries
        length_function=len,
    )

    chunks = splitter.split_text(text)

    if not chunks:
        logger.warning("No chunks produced from text", doc_id=doc_id, text_len=len(text))
        return 0

    logger.info(
        "Text chunked",
        doc_id=doc_id,
        source_file=source_file,
        chunk_count=len(chunks),
        chunk_size=settings.rag_chunk_size,
    )

    # -------------------------------------------------------------------------
    # Step 2: Embed all chunks (batched)
    # -------------------------------------------------------------------------
    logger.info("Embedding chunks", doc_id=doc_id, count=len(chunks))
    embeddings = await embed_batch(chunks, task_type="RETRIEVAL_DOCUMENT")
    logger.info("Embeddings generated", doc_id=doc_id, count=len(embeddings))

    # -------------------------------------------------------------------------
    # Step 3: Prepare ChromaDB documents
    # -------------------------------------------------------------------------
    ingested_at = datetime.now(timezone.utc).isoformat()
    chunk_ids = []
    chunk_metadatas = []

    for i, chunk in enumerate(chunks):
        chunk_id = f"{doc_id}__chunk_{i}"
        chunk_ids.append(chunk_id)
        chunk_metadatas.append({
            # CRITICAL: These fields are used for multi-tenant filtering
            "branch": branch,
            "subject": subject,
            # Source attribution
            "doc_id": doc_id,
            "source_file": source_file,
            "doc_type": doc_type,
            "chunk_index": i,
            "ingested_at": ingested_at,
        })

    # -------------------------------------------------------------------------
    # Step 4: Upsert into ChromaDB
    # The collection is isolated to (branch, subject) — no cross-tenant leakage
    # -------------------------------------------------------------------------
    collection = get_or_create_collection(branch=branch, subject=subject)

    collection.upsert(
        ids=chunk_ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=chunk_metadatas,
    )

    logger.info(
        "ChromaDB upsert complete",
        collection=f"{branch}__{subject}",
        doc_id=doc_id,
        chunks_indexed=len(chunks),
    )

    return len(chunks)


async def delete_document_chunks(
    doc_id: str,
    branch: str,
    subject: str,
) -> int:
    """
    Removes all ChromaDB chunks belonging to a specific document.
    Used when re-ingesting or deleting a document.
    
    Args:
        doc_id: UUID of the document whose chunks should be removed
        branch: Tenant branch code
        subject: Subject code
    
    Returns:
        Number of chunks removed
    """
    collection = get_or_create_collection(branch=branch, subject=subject)

    # Get all chunk IDs for this document
    results = collection.get(where={"doc_id": doc_id})
    chunk_ids = results.get("ids", [])

    if not chunk_ids:
        logger.info("No chunks to delete", doc_id=doc_id)
        return 0

    collection.delete(ids=chunk_ids)
    logger.info("Chunks deleted", doc_id=doc_id, count=len(chunk_ids))

    return len(chunk_ids)
