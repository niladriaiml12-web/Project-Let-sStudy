"""
app/dependencies.py

Shared FastAPI dependencies (Depends) for authentication,
database sessions, and service injection.
"""
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.chroma_client import get_chroma_client
from app.db.sql_client import get_db_session
from app.db.sql_models import ApiKey, Group


# =============================================================================
# Config Dependency
# =============================================================================

def settings_dep() -> Settings:
    """Injects the application settings."""
    return get_settings()


SettingsDep = Annotated[Settings, Depends(settings_dep)]


# =============================================================================
# Database Dependencies
# =============================================================================

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


# =============================================================================
# Authentication: API Key per Tenant
# =============================================================================

async def verify_api_key(
    db: DbSession,
    settings: SettingsDep,
    x_api_key: Annotated[str | None, Header(description="Tenant API key for authentication")] = None,
    x_tenant_branch: Annotated[str | None, Header(description="Tenant branch code e.g. CSE_AIML")] = None,
) -> Group:
    """
    Validates the tenant key or tenant branch against the database.
    
    Returns the associated Group (tenant) on success.
    In development mode, gracefully falls back so developers and students
    never get blocked by 401 errors.
    """
    # 1. Look up the key in the database if provided
    if x_api_key:
        result = await db.execute(
            select(Group)
            .join(ApiKey, ApiKey.group_id == Group.id)
            .where(ApiKey.key_value == x_api_key, ApiKey.is_active == 1)
        )
        group = result.scalar_one_or_none()
        if group is not None:
            return group

    # 2. Try resolving by branch code (from header or key hints)
    branch = x_tenant_branch
    if not branch and x_api_key:
        if "core" in x_api_key.lower():
            branch = "CSE_CORE"
        elif "aiml" in x_api_key.lower():
            branch = "CSE_AIML"

    if branch:
        result = await db.execute(select(Group).where(Group.branch_code == branch))
        group = result.scalar_one_or_none()
        if group is not None:
            return group

    # 3. Development fallback: return default group (CSE AIML) instead of throwing 401
    if settings.app_env == "development":
        result = await db.execute(select(Group).order_by(Group.id))
        default_group = result.scalars().first()
        if default_group is not None:
            return default_group

    # 4. Strict check in production
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing tenant API key.",
        headers={"WWW-Authenticate": "ApiKey"},
    )


# Convenience type annotation for authenticated routes
AuthenticatedGroup = Annotated[Group, Depends(verify_api_key)]


# =============================================================================
# ChromaDB Dependency
# =============================================================================

def get_chroma():
    """Injects the ChromaDB client. Used for admin/debug endpoints."""
    return get_chroma_client()
