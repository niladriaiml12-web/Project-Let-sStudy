"""
app/services/retrieval_service.py

Tenant-aware vector retrieval from ChromaDB.

CRITICAL SECURITY RULE:
    Every query MUST include `where={"branch": branch, "subject": subject}`.
    This is the only guarantee of multi-tenant data isolation.
    Never query a collection without this filter.
"""
from dataclasses import dataclass
from typing import List, Optional

import structlog

from app.db.chroma_client import get_or_create_collection
from app.services.llm_service import embed_text

logger = structlog.get_logger(__name__)


@dataclass
class RetrievedChunk:
    """A single retrieved context chunk with source metadata."""
    doc_id: str
    source_file: str
    chunk_index: int
    content: str
    relevance_score: float          # Cosine similarity (0.0 to 1.0, higher = more similar)
    branch: str
    subject: str
    doc_type: str


async def retrieve(
    query: str,
    branch: str,
    subject: str,
    top_k: Optional[int] = None,
    min_relevance_score: float = 0.0,
) -> List[RetrievedChunk]:
    """
    Retrieves the most relevant chunks for a query within a specific tenant's collection.
    
    ISOLATION GUARANTEE:
        Only chunks where metadata.branch == branch AND metadata.subject == subject
        are ever returned. Cross-tenant retrieval is structurally impossible.
    
    Args:
        query:               The user's question / search text
        branch:              Tenant branch code (e.g., "CSE_AIML")
        subject:             Subject code (e.g., "ML")
        top_k:               Maximum number of chunks to return (defaults to config)
        min_relevance_score: Minimum cosine similarity to include a chunk (0.0 = all)
    
    Returns:
        List of RetrievedChunk, sorted by relevance (highest first)
        Returns empty list if no relevant chunks found (never raises on empty)
    """
    from app.config import get_settings
    settings = get_settings()
    k = top_k or settings.rag_top_k

    # -------------------------------------------------------------------------
    # Step 1: Embed the query using RETRIEVAL_QUERY task type
    # (different from RETRIEVAL_DOCUMENT — optimized for query-time)
    # -------------------------------------------------------------------------
    logger.info("Embedding query for retrieval", branch=branch, subject=subject, query_len=len(query))
    query_embedding = await embed_text(query, task_type="RETRIEVAL_QUERY")

    # -------------------------------------------------------------------------
    # Step 2: Query ChromaDB with tenant metadata filter
    # NEVER remove the `where` clause — this is the isolation boundary
    # -------------------------------------------------------------------------
    collection = get_or_create_collection(branch=branch, subject=subject)

    # Check if collection has any documents before querying
    collection_count = collection.count()
    if collection_count == 0:
        logger.warning(
            "Collection is empty — no documents indexed yet",
            branch=branch,
            subject=subject,
        )
        return []

    # Clamp top_k to available documents
    effective_k = min(k, collection_count)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=effective_k,
        where={"$and": [{"branch": {"$eq": branch}}, {"subject": {"$eq": subject}}]},
        include=["documents", "metadatas", "distances"],
    )

    # -------------------------------------------------------------------------
    # Step 3: Parse results into typed dataclasses
    # ChromaDB returns distances (lower = more similar for L2, inverted for cosine)
    # -------------------------------------------------------------------------
    chunks: List[RetrievedChunk] = []

    if not results["ids"] or not results["ids"][0]:
        logger.info("No results found", branch=branch, subject=subject, query=query[:100])
        return []

    for i, (doc_id_chunk, document, metadata, distance) in enumerate(
        zip(
            results["ids"][0],
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )
    ):
        # Convert cosine distance to similarity score (distance 0 = perfect match)
        # ChromaDB with cosine space: distance ∈ [0, 2], similarity = 1 - distance/2
        relevance_score = max(0.0, 1.0 - distance / 2.0)

        if relevance_score < min_relevance_score:
            logger.debug(
                "Chunk below relevance threshold, skipping",
                score=relevance_score,
                threshold=min_relevance_score,
            )
            continue

        chunks.append(
            RetrievedChunk(
                doc_id=metadata.get("doc_id", "unknown"),
                source_file=metadata.get("source_file", "unknown"),
                chunk_index=metadata.get("chunk_index", i),
                content=document,
                relevance_score=round(relevance_score, 4),
                branch=metadata.get("branch", branch),
                subject=metadata.get("subject", subject),
                doc_type=metadata.get("doc_type", "unknown"),
            )
        )

    logger.info(
        "Retrieval complete",
        branch=branch,
        subject=subject,
        chunks_found=len(chunks),
        top_score=chunks[0].relevance_score if chunks else 0,
    )

    return chunks
