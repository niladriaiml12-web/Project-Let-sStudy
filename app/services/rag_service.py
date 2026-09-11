"""
app/services/rag_service.py

RAG (Retrieval-Augmented Generation) orchestration pipeline.
Combines tenant-aware retrieval with Gemini LLM to produce grounded answers.

The LLM is strictly instructed to ONLY use the provided context,
preventing hallucinations from external knowledge.
"""
from typing import List, Optional

import structlog

from app.schemas.query import QueryResponse, SourceChunk
from app.services.llm_service import generate_text
from app.services.retrieval_service import RetrievedChunk, retrieve

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# System Prompt (strict context grounding)
# ---------------------------------------------------------------------------

RAG_SYSTEM_PROMPT = """You are a helpful academic tutor for engineering students.
Your role is to answer questions STRICTLY based on the provided study notes and materials.

CRITICAL RULES:
1. ONLY use information from the "Study Notes Context" provided below.
2. If the answer cannot be found in the context, respond with:
   "I couldn't find this topic in your uploaded study materials. Please check if the relevant notes have been uploaded."
3. Do NOT use any external knowledge, internet information, or your training data to answer.
4. Always cite which part of the notes your answer comes from (e.g., "According to your notes on [topic]...").
5. Be clear, structured, and use bullet points or headings for longer answers.
6. If the context partially answers the question, provide what you can and note what's missing.
"""


def _build_rag_prompt(
    question: str,
    context_chunks: List[RetrievedChunk],
) -> str:
    """
    Builds the full RAG prompt by inserting retrieved chunks as context.
    
    Args:
        question: The student's question
        context_chunks: Retrieved, relevant chunks from ChromaDB
    
    Returns:
        Formatted prompt string to send to Gemini
    """
    if not context_chunks:
        # If no context found, explicitly tell the model
        return f"""Study Notes Context:
[No relevant notes found for this query]

Student Question: {question}

Remember: You MUST only use the provided context. Since no relevant notes were found, 
tell the student you couldn't find this topic in their uploaded materials."""

    # Format context chunks with source attribution
    context_parts = []
    for i, chunk in enumerate(context_chunks, start=1):
        context_parts.append(
            f"--- Note Excerpt {i} (from: {chunk.source_file}, Relevance: {chunk.relevance_score:.0%}) ---\n"
            f"{chunk.content}\n"
        )

    context_text = "\n".join(context_parts)

    return f"""Study Notes Context:
{context_text}

Student Question: {question}

Please answer the question using ONLY the study notes context provided above."""


async def answer_question(
    question: str,
    branch: str,
    subject: str,
    top_k: Optional[int] = None,
) -> QueryResponse:
    """
    Full RAG pipeline: retrieve relevant chunks → build grounded prompt → generate answer.
    
    Args:
        question: The student's academic question
        branch:   Tenant branch code (for ChromaDB isolation)
        subject:  Subject code (for ChromaDB isolation)
        top_k:    Number of chunks to retrieve (uses config default if None)
    
    Returns:
        QueryResponse with answer, sources, and metadata
    """
    logger.info(
        "RAG pipeline started",
        branch=branch,
        subject=subject,
        question_len=len(question),
    )

    # -------------------------------------------------------------------------
    # Step 1: Retrieve relevant chunks (tenant-isolated)
    # -------------------------------------------------------------------------
    chunks = await retrieve(
        query=question,
        branch=branch,
        subject=subject,
        top_k=top_k,
    )

    context_found = len(chunks) > 0

    # -------------------------------------------------------------------------
    # Step 2: Build grounded prompt
    # -------------------------------------------------------------------------
    prompt = _build_rag_prompt(question, chunks)

    # -------------------------------------------------------------------------
    # Step 3: Generate answer with Gemini (low temperature for factual accuracy)
    # -------------------------------------------------------------------------
    logger.info("Calling LLM for answer generation", chunks_in_context=len(chunks))
    answer_text = await generate_text(
        prompt=prompt,
        system_instruction=RAG_SYSTEM_PROMPT,
        temperature=0.1,  # Low temp = more deterministic, less hallucination
        max_output_tokens=1024,
    )

    # -------------------------------------------------------------------------
    # Step 4: Build response with source citations
    # -------------------------------------------------------------------------
    source_chunks = [
        SourceChunk(
            doc_id=chunk.doc_id,
            source_file=chunk.source_file,
            chunk_index=chunk.chunk_index,
            content_preview=chunk.content[:200] + ("..." if len(chunk.content) > 200 else ""),
            relevance_score=chunk.relevance_score,
        )
        for chunk in chunks
    ]

    logger.info(
        "RAG pipeline complete",
        branch=branch,
        subject=subject,
        context_found=context_found,
        answer_len=len(answer_text),
    )

    return QueryResponse(
        question=question,
        answer=answer_text,
        sources=source_chunks,
        branch=branch,
        subject=subject,
        chunks_retrieved=len(chunks),
        context_found=context_found,
    )
