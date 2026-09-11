"""
app/api/v1/health.py

Health check endpoint — no auth required.
Used by load balancers, monitoring systems, and Docker healthchecks.
"""
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings
from app.db.chroma_client import get_chroma_client

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    services: dict


@router.get("/health", response_model=HealthResponse, summary="Service health check")
async def health_check():
    """
    Returns the health status of the API and its dependent services.
    
    Checks:
    - API server: always OK if this endpoint responds
    - ChromaDB: verifies the persistent client is reachable
    """
    settings = get_settings()
    services = {}

    # Check ChromaDB
    try:
        chroma = get_chroma_client()
        collection_count = len(chroma.list_collections())
        services["chromadb"] = {"status": "ok", "collections": collection_count}
    except Exception as e:
        services["chromadb"] = {"status": "error", "error": str(e)}

    overall_status = "ok" if all(s.get("status") == "ok" for s in services.values()) else "degraded"

    return HealthResponse(
        status=overall_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="0.1.0",
        services=services,
    )
