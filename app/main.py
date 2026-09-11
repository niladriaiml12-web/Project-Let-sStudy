"""
app/main.py

FastAPI application factory with lifespan management.
This is the entry point for the Multi-Tenant Study RAG Platform backend.
"""
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.db.sql_client import close_db, init_db

logger = structlog.get_logger(__name__)


# =============================================================================
# Lifespan (startup / shutdown)
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages application startup and shutdown:
    - Startup: Initialize DB tables, verify ChromaDB, log config summary
    - Shutdown: Close DB engine connections cleanly
    """
    settings = get_settings()

    # --- Startup ---
    logger.info(
        "Starting Let'sStudy RAG Platform",
        env=settings.app_env,
        llm_provider=settings.llm_provider,
        llm_model=settings.llm_model,
        embedding_model=settings.embedding_model,
    )

    # Initialize relational DB (creates tables if not exist)
    from app.db.sql_client import close_db, init_db, seed_default_data
    await init_db()
    await seed_default_data()
    logger.info("Database initialized and default tenant data seeded", url=settings.database_url)

    # Verify ChromaDB is accessible
    from app.db.chroma_client import get_chroma_client
    chroma = get_chroma_client()
    collections = chroma.list_collections()
    logger.info("ChromaDB connected", collection_count=len(collections))

    yield  # ← Application runs here

    # --- Shutdown ---
    logger.info("Shutting down Let'sStudy RAG Platform")
    await close_db()
    logger.info("Database connections closed")


# =============================================================================
# App Factory
# =============================================================================

def create_app() -> FastAPI:
    """Creates and configures the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Let'sStudy — Multi-Tenant Study RAG Platform",
        description=(
            "AI-powered academic platform for engineering students. "
            "Supports OCR ingestion of handwritten notes, RAG-based Q&A, "
            "and LLM-graded answer evaluation with strict multi-tenant data isolation."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # -------------------------------------------------------------------------
    # CORS Middleware
    # -------------------------------------------------------------------------
    # In development, allow all origins. Tighten in production.
    allow_origins = ["*"] if settings.app_env == "development" else []

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -------------------------------------------------------------------------
    # Routers
    # -------------------------------------------------------------------------
    from app.api.v1 import health, groups, ingest, query, grade

    app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    app.include_router(groups.router, prefix="/api/v1/groups", tags=["Groups & Tenants"])
    app.include_router(ingest.router, prefix="/api/v1/ingest", tags=["Document Ingestion"])
    app.include_router(query.router, prefix="/api/v1/query", tags=["RAG Query"])
    app.include_router(grade.router, prefix="/api/v1/grade", tags=["Answer Grading"])

    # -------------------------------------------------------------------------
    # Root endpoint
    # -------------------------------------------------------------------------
    @app.get("/", include_in_schema=False)
    async def root():
        return JSONResponse({
            "service": "Let'sStudy RAG Platform",
            "version": "0.1.0",
            "docs": "/docs",
            "status": "running",
        })

    return app


# =============================================================================
# Application Instance (used by uvicorn)
# =============================================================================
app = create_app()
