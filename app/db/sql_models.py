"""
app/db/sql_models.py

SQLAlchemy ORM models for tenant/group management and document tracking.
These models power the relational side of the platform (NOT the vector store).

Tables:
  - groups   → Student groups (tenants), e.g., "CSE AIML 2026"
  - subjects → Subjects belonging to a group
  - documents → Uploaded documents with processing status
  - api_keys → Tenant API keys for authentication
"""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


# =============================================================================
# Enums
# =============================================================================

class DocumentStatus(str, enum.Enum):
    """Processing lifecycle of an uploaded document."""
    PENDING = "pending"       # Uploaded, not yet processed
    PROCESSING = "processing" # OCR + embedding in progress
    COMPLETED = "completed"   # Fully indexed in ChromaDB
    FAILED = "failed"         # Processing error occurred


class DocumentType(str, enum.Enum):
    """Type of academic content in the document."""
    CLASS_NOTES = "class_notes"
    PYQ = "pyq"               # Previous Year Questions
    SYLLABUS = "syllabus"
    REFERENCE = "reference"


# =============================================================================
# Models
# =============================================================================

class Group(Base):
    """
    Represents a student group / tenant.
    A group is the top-level isolation boundary in the multi-tenant system.
    
    Example: { name: "CSE AIML 2026", branch_code: "CSE_AIML" }
    """
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="Human-readable name e.g. 'CSE AIML 2026'")
    branch_code = Column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment="Machine-readable tenant key used in ChromaDB filters e.g. 'CSE_AIML'",
    )
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    subjects = relationship("Subject", back_populates="group", cascade="all, delete-orphan")
    api_keys = relationship("ApiKey", back_populates="group", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Group id={self.id} branch_code={self.branch_code!r}>"


class Subject(Base):
    """
    A subject/course belonging to a Group.
    Together with Group.branch_code, uniquely identifies a ChromaDB collection.
    
    Example: { name: "Machine Learning", subject_code: "ML", group_id: 1 }
    """
    __tablename__ = "subjects"
    __table_args__ = (
        UniqueConstraint("group_id", "subject_code", name="uq_group_subject_code"),
    )

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(150), nullable=False, comment="Full subject name e.g. 'Machine Learning'")
    subject_code = Column(
        String(50),
        nullable=False,
        comment="Short code used in ChromaDB filters e.g. 'ML'",
    )
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    group = relationship("Group", back_populates="subjects")
    documents = relationship("Document", back_populates="subject", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Subject id={self.id} code={self.subject_code!r} group_id={self.group_id}>"


class Document(Base):
    """
    Tracks an uploaded document through its OCR and indexing lifecycle.
    
    A Document moves through: PENDING → PROCESSING → COMPLETED | FAILED
    Once COMPLETED, its chunks live in ChromaDB under the subject's collection.
    """
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False, comment="UUID-based filename on disk")
    doc_type = Column(Enum(DocumentType), nullable=False, default=DocumentType.CLASS_NOTES)
    status = Column(
        Enum(DocumentStatus),
        nullable=False,
        default=DocumentStatus.PENDING,
        index=True,
    )
    chunk_count = Column(Integer, nullable=True, comment="Number of chunks indexed in ChromaDB")
    error_message = Column(Text, nullable=True, comment="Error details if status=FAILED")
    ocr_text = Column(Text, nullable=True, comment="Raw OCR output (Markdown) for debugging")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    subject = relationship("Subject", back_populates="documents")

    def __repr__(self) -> str:
        return f"<Document id={self.id} status={self.status} file={self.original_filename!r}>"


class ApiKey(Base):
    """
    API keys for tenant authentication (one key per group/tenant).
    Keys are stored as-is for MVP. In production, store hashed (bcrypt/argon2).
    """
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    key_value = Column(String(128), nullable=False, unique=True, index=True)
    label = Column(String(100), nullable=True, comment="Human-readable label e.g. 'Admin Key'")
    is_active = Column(Integer, nullable=False, default=1, comment="1=active, 0=revoked")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    group = relationship("Group", back_populates="api_keys")

    def __repr__(self) -> str:
        return f"<ApiKey id={self.id} group_id={self.group_id} active={self.is_active}>"
