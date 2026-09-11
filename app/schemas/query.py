"""
app/schemas/query.py

Pydantic request/response models for the RAG query pipeline.
"""
from typing import List, Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Request body for asking a question to the RAG system."""
    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="The academic question to answer",
        examples=["What is the difference between supervised and unsupervised learning?"],
    )
    subject: str = Field(
        ...,
        description="Subject code to search within (e.g., 'ML', 'DBMS')",
        examples=["ML"],
    )
    top_k: Optional[int] = Field(
        default=None,
        ge=1,
        le=20,
        description="Number of context chunks to retrieve (defaults to server setting)",
    )


class SourceChunk(BaseModel):
    """A retrieved context chunk used to generate the answer."""
    doc_id: str = Field(..., description="Source document ID")
    source_file: str = Field(..., description="Original filename")
    chunk_index: int = Field(..., description="Chunk index within the document")
    content_preview: str = Field(..., description="First 200 chars of the chunk content")
    relevance_score: float = Field(..., description="Cosine similarity score (0-1)")


class QueryResponse(BaseModel):
    """Response from the RAG query pipeline."""
    question: str
    answer: str = Field(..., description="LLM-generated answer grounded in retrieved context")
    sources: List[SourceChunk] = Field(..., description="Context chunks used to generate the answer")
    branch: str = Field(..., description="Branch (tenant) that was queried")
    subject: str = Field(..., description="Subject that was queried")
    chunks_retrieved: int = Field(..., description="Number of context chunks retrieved")
    context_found: bool = Field(..., description="Whether relevant context was found in the notes")
