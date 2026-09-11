"""
app/api/v1/groups.py

Tenant/Group management endpoints.
Allows admins to create student groups (tenants), add subjects,
and manage API keys for authentication.

These endpoints are the foundation of the multi-tenant system.
No X-API-Key required here (admin-only bootstrap operations).
"""
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.db.sql_client import get_db_session
from app.db.sql_models import ApiKey, Group, Subject
from app.dependencies import DbSession

router = APIRouter()


# =============================================================================
# Pydantic Schemas (local to this router for simplicity)
# =============================================================================

class GroupCreate(BaseModel):
    name: str = Field(..., description="Human-readable group name e.g. 'CSE AIML 2026'")
    branch_code: str = Field(..., description="Machine-readable tenant key e.g. 'CSE_AIML'")
    description: Optional[str] = None


class SubjectCreate(BaseModel):
    name: str = Field(..., description="Full subject name e.g. 'Machine Learning'")
    subject_code: str = Field(..., description="Short code e.g. 'ML' — used in API calls")
    description: Optional[str] = None


class ApiKeyCreate(BaseModel):
    key_value: str = Field(..., min_length=16, description="The API key string (min 16 chars)")
    label: Optional[str] = Field(None, description="Human-readable label e.g. 'Admin Key'")


class GroupResponse(BaseModel):
    id: int
    name: str
    branch_code: str
    description: Optional[str]
    model_config = {"from_attributes": True}


class SubjectResponse(BaseModel):
    id: int
    group_id: int
    name: str
    subject_code: str
    description: Optional[str]
    model_config = {"from_attributes": True}


class ApiKeyResponse(BaseModel):
    id: int
    group_id: int
    key_value: str
    label: Optional[str]
    is_active: int
    model_config = {"from_attributes": True}


# =============================================================================
# Group (Tenant) Endpoints
# =============================================================================

@router.post("/", response_model=GroupResponse, status_code=status.HTTP_201_CREATED,
             summary="Create a new student group (tenant)")
async def create_group(payload: GroupCreate, db: DbSession):
    """
    Creates a new student group (tenant boundary).
    The `branch_code` becomes the ChromaDB collection prefix.
    
    Example: { "name": "CSE AIML 2026", "branch_code": "CSE_AIML" }
    """
    # Check for duplicate branch_code
    existing = await db.execute(
        select(Group).where(Group.branch_code == payload.branch_code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A group with branch_code '{payload.branch_code}' already exists.",
        )

    group = Group(
        name=payload.name,
        branch_code=payload.branch_code,
        description=payload.description,
    )
    db.add(group)
    await db.flush()  # Get the generated ID before commit
    await db.refresh(group)
    return group


@router.get("/", response_model=List[GroupResponse], summary="List all student groups")
async def list_groups(db: DbSession):
    """Returns all registered student groups (tenants)."""
    result = await db.execute(select(Group).order_by(Group.id))
    return result.scalars().all()


@router.get("/{group_id}", response_model=GroupResponse, summary="Get a specific group")
async def get_group(group_id: int, db: DbSession):
    """Returns details for a specific group by ID."""
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail=f"Group {group_id} not found.")
    return group


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete a student group")
async def delete_group(group_id: int, db: DbSession):
    """
    Deletes a group and all associated subjects, documents, and API keys.
    WARNING: This does NOT automatically delete ChromaDB collections.
    """
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail=f"Group {group_id} not found.")
    await db.delete(group)


# =============================================================================
# Subject Endpoints
# =============================================================================

@router.post("/{group_id}/subjects", response_model=SubjectResponse,
             status_code=status.HTTP_201_CREATED, summary="Add a subject to a group")
async def add_subject(group_id: int, payload: SubjectCreate, db: DbSession):
    """
    Adds a subject to a group. Each (group, subject) pair gets its own
    isolated ChromaDB collection when documents are ingested.
    """
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail=f"Group {group_id} not found.")

    # Check for duplicate subject code in this group
    existing = await db.execute(
        select(Subject).where(
            Subject.group_id == group_id,
            Subject.subject_code == payload.subject_code,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"Subject '{payload.subject_code}' already exists in group {group_id}.",
        )

    subject = Subject(
        group_id=group_id,
        name=payload.name,
        subject_code=payload.subject_code,
        description=payload.description,
    )
    db.add(subject)
    await db.flush()
    await db.refresh(subject)
    return subject


@router.get("/{group_id}/subjects", response_model=List[SubjectResponse],
            summary="List subjects in a group")
async def list_subjects(group_id: int, db: DbSession):
    """Returns all subjects belonging to a group."""
    result = await db.execute(
        select(Subject).where(Subject.group_id == group_id).order_by(Subject.id)
    )
    return result.scalars().all()


# =============================================================================
# API Key Management
# =============================================================================

@router.post("/{group_id}/api-keys", response_model=ApiKeyResponse,
             status_code=status.HTTP_201_CREATED, summary="Create an API key for a group")
async def create_api_key(group_id: int, payload: ApiKeyCreate, db: DbSession):
    """
    Creates an API key for a tenant group.
    Students use this key in the X-API-Key header to authenticate.
    """
    result = await db.execute(select(Group).where(Group.id == group_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail=f"Group {group_id} not found.")

    api_key = ApiKey(
        group_id=group_id,
        key_value=payload.key_value,
        label=payload.label,
        is_active=1,
    )
    db.add(api_key)
    await db.flush()
    await db.refresh(api_key)
    return api_key


@router.get("/{group_id}/api-keys", response_model=List[ApiKeyResponse],
            summary="List API keys for a group")
async def list_api_keys(group_id: int, db: DbSession):
    """Returns all API keys for a group (for admin management)."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.group_id == group_id).order_by(ApiKey.id)
    )
    return result.scalars().all()


@router.delete("/{group_id}/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Revoke an API key")
async def revoke_api_key(group_id: int, key_id: int, db: DbSession):
    """Deactivates (revokes) an API key without deleting it, for audit trail purposes."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.group_id == group_id)
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail=f"API key {key_id} not found.")

    api_key.is_active = 0  # Revoke without deletion
