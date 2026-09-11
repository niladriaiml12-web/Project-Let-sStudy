"""
app/api/v1/query.py

RAG Query endpoint.
Students ask questions and receive grounded answers
sourced exclusively from their group's uploaded study materials.

All endpoints require X-API-Key authentication.
"""
from fastapi import APIRouter

from app.dependencies import AuthenticatedGroup, SettingsDep
from app.schemas.query import QueryRequest, QueryResponse
from app.services.rag_service import answer_question

router = APIRouter()


@router.post(
    "/ask",
    response_model=QueryResponse,
    summary="Ask a question about your study materials",
)
async def ask_question_endpoint(
    payload: QueryRequest,
    group: AuthenticatedGroup,
    settings: SettingsDep,
):
    """
    Ask a question and receive an answer grounded in your uploaded study notes.
    
    **How it works:**
    1. Your question is embedded using Google's `text-embedding-004` model
    2. The top-K most relevant chunks are retrieved from **your group's** ChromaDB collection
    3. Gemini LLM generates an answer using ONLY the retrieved chunks
    4. The answer includes source citations so you can verify against your notes
    
    **Multi-tenant isolation:**
    The system ONLY searches notes uploaded by your group for the specified subject.
    Notes from other groups are completely invisible.
    
    **If no relevant notes are found:**
    The system will tell you the topic isn't in your uploaded materials rather than
    making up an answer.
    """
    response = await answer_question(
        question=payload.question,
        branch=group.branch_code,
        subject=payload.subject,
        top_k=payload.top_k,
    )
    return response
