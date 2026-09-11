"""
app/db/sql_client.py

Async SQLAlchemy session factory and database initialization.
Supports SQLite (dev) and PostgreSQL (prod) via the DATABASE_URL env var.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings
from app.db.sql_models import Base

# ---------------------------------------------------------------------------
# Engine & Session Factory (module-level singletons)
# ---------------------------------------------------------------------------

_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker | None = None


def get_engine() -> AsyncEngine:
    """Lazily creates and returns the async SQLAlchemy engine singleton."""
    global _engine
    if _engine is None:
        settings = get_settings()
        connect_args = {}

        # SQLite requires check_same_thread=False for async usage
        if "sqlite" in settings.database_url:
            connect_args["check_same_thread"] = False

        _engine = create_async_engine(
            settings.database_url,
            echo=(settings.app_env == "development"),  # Log SQL in dev
            connect_args=connect_args,
            pool_pre_ping=True,  # Verify connections before use
        )
    return _engine


def get_session_factory() -> async_sessionmaker:
    """Returns the async session factory singleton."""
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,  # Keep objects usable after commit
            autocommit=False,
            autoflush=False,
        )
    return _async_session_factory


# ---------------------------------------------------------------------------
# Database Initialization
# ---------------------------------------------------------------------------

async def init_db() -> None:
    """
    Creates all database tables if they don't exist.
    Called once at application startup via the lifespan event.
    """
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def seed_default_data() -> None:
    """
    Seeds default groups (tenants), API keys, and subjects if the database is empty.
    Ensures the frontend can connect immediately without manual SQL/API bootstrap.
    """
    from sqlalchemy import select
    from app.db.sql_models import Group, Subject, ApiKey

    session_factory = get_session_factory()
    async with session_factory() as db:
        result = await db.execute(select(Group))
        if result.scalars().first() is not None:
            return  # Already seeded

        # 1. CSE AIML Group
        aiml = Group(
            name="CSE AIML 2026",
            branch_code="CSE_AIML",
            description="Department of Computer Science & Engineering (Artificial Intelligence & Machine Learning)",
        )
        db.add(aiml)
        await db.flush()

        # 2. CSE Core Group
        core = Group(
            name="CSE Core 2026",
            branch_code="CSE_CORE",
            description="Department of Computer Science & Engineering (Core)",
        )
        db.add(core)
        await db.flush()

        # 3. API Keys
        aiml_key = ApiKey(
            group_id=aiml.id,
            key_value="dev-key-cse-aiml-2026",
            label="CSE AIML Student Access Key",
            is_active=1,
        )
        core_key = ApiKey(
            group_id=core.id,
            key_value="dev-key-cse-core-2026",
            label="CSE Core Student Access Key",
            is_active=1,
        )
        db.add_all([aiml_key, core_key])

        # 4. Subjects for CSE AIML
        db.add_all([
            Subject(group_id=aiml.id, name="Machine Learning", subject_code="ML", description="Supervised, Unsupervised & Reinforcement Learning"),
            Subject(group_id=aiml.id, name="Deep Learning", subject_code="DL", description="Neural Networks, CNNs, Transformers"),
            Subject(group_id=aiml.id, name="Natural Language Processing", subject_code="NLP", description="Language Models, RAG, Information Retrieval"),
        ])

        # 5. Subjects for CSE Core
        db.add_all([
            Subject(group_id=core.id, name="Operating Systems", subject_code="OS", description="Processes, Threads, Virtual Memory, File Systems"),
            Subject(group_id=core.id, name="Database Management Systems", subject_code="DBMS", description="SQL, Normalization, ACID, Indexing"),
            Subject(group_id=core.id, name="Computer Networks", subject_code="CN", description="TCP/IP, Routing Algorithms, Socket Programming"),
        ])

        await db.commit()


async def close_db() -> None:
    """Disposes the database engine. Called at application shutdown."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None


# ---------------------------------------------------------------------------
# Dependency: Async Session per Request
# ---------------------------------------------------------------------------

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a database session per request.
    Automatically commits on success or rolls back on exception.
    
    Usage:
        @router.get("/")
        async def endpoint(db: AsyncSession = Depends(get_db_session)):
            ...
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager version of get_db_session for use outside FastAPI
    (e.g., background tasks, tests, CLI scripts).
    
    Usage:
        async with get_db_context() as db:
            result = await db.execute(select(Group))
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
