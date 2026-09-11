"""
app/db/chroma_client.py

ChromaDB client singleton and collection management.

CRITICAL RULE: Every query MUST use metadata filtering to enforce
multi-tenant data isolation. A CSE Core student must never see
CSE AIML documents — ever.
"""
import threading
from typing import Optional

import chromadb
from chromadb import Collection
from chromadb.config import Settings as ChromaSettings

from app.config import get_settings

_chroma_client: Optional[chromadb.PersistentClient] = None
_lock = threading.Lock()


def get_chroma_client() -> chromadb.PersistentClient:
    """
    Returns the ChromaDB client singleton (thread-safe lazy init).
    Uses PersistentClient so embeddings survive server restarts.
    """
    global _chroma_client
    if _chroma_client is None:
        with _lock:
            if _chroma_client is None:  # Double-checked locking
                settings = get_settings()
                _chroma_client = chromadb.PersistentClient(
                    path=settings.chroma_persist_dir,
                    settings=ChromaSettings(anonymized_telemetry=False),
                )
    return _chroma_client


def get_collection_name(branch: str, subject: str) -> str:
    """
    Generates a deterministic ChromaDB collection name for a tenant+subject.
    Collection names must be 3-63 chars, alphanumeric + underscores/hyphens.

    Example: "CSE_AIML" + "Machine Learning" → "CSE_AIML_Machine_Learning"
    """
    # Sanitize: replace spaces and special chars with underscores
    safe_branch = "".join(c if c.isalnum() else "_" for c in branch).strip("_")
    safe_subject = "".join(c if c.isalnum() else "_" for c in subject).strip("_")
    return f"{safe_branch}__{safe_subject}"


def get_or_create_collection(branch: str, subject: str) -> Collection:
    """
    Gets or creates a ChromaDB collection for the given branch+subject tenant.
    
    Each (branch, subject) pair gets its own isolated collection.
    Metadata is stored at the collection level for audit purposes.
    
    Args:
        branch: Tenant branch identifier e.g. "CSE_AIML", "CSE_Core"
        subject: Subject name e.g. "Machine_Learning", "DBMS"
    
    Returns:
        ChromaDB Collection ready for upsert/query
    """
    client = get_chroma_client()
    collection_name = get_collection_name(branch, subject)

    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={
            "branch": branch,
            "subject": subject,
            "hnsw:space": "cosine",  # Use cosine similarity for text embeddings
        },
    )
    return collection


def list_tenant_collections(branch: Optional[str] = None) -> list[str]:
    """
    Lists all ChromaDB collection names, optionally filtered by branch prefix.
    
    Args:
        branch: Optional branch to filter by. If None, returns all collections.
    
    Returns:
        List of collection names
    """
    client = get_chroma_client()
    all_collections = client.list_collections()
    names = [col.name for col in all_collections]

    if branch:
        safe_branch = "".join(c if c.isalnum() else "_" for c in branch)
        names = [n for n in names if n.startswith(safe_branch)]

    return names


def delete_collection(branch: str, subject: str) -> bool:
    """
    Deletes a ChromaDB collection for a tenant+subject pair.
    Used for admin cleanup operations.
    
    Returns:
        True if deleted, False if collection didn't exist
    """
    client = get_chroma_client()
    collection_name = get_collection_name(branch, subject)
    try:
        client.delete_collection(collection_name)
        return True
    except Exception:
        return False
