"""
app/schemas/grade.py

Pydantic request/response models for the answer grading pipeline.
"""
from typing import List, Optional

from pydantic import BaseModel, Field


class GradeRequest(BaseModel):
    """Request body for grading a student's written answer."""
    question: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="The exam question being answered",
        examples=["Explain the working of a Support Vector Machine with a diagram."],
    )
    student_answer: str = Field(
        ...,
        min_length=10,
        max_length=10000,
        description="The student's written answer to evaluate",
    )
    subject: str = Field(
        ...,
        description="Subject code to retrieve reference material from",
        examples=["ML"],
    )
    max_marks: Optional[int] = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum marks for the question (default: 10)",
    )


class MissedPoint(BaseModel):
    """A key concept that was in the reference material but missing from the student's answer."""
    point: str = Field(..., description="The missed concept or fact")
    importance: str = Field(..., description="Why this point matters: 'critical' | 'important' | 'bonus'")


class GradeResponse(BaseModel):
    """Detailed grading result with score, feedback, and missed points."""
    question: str
    score: int = Field(..., description="Score awarded")
    max_score: int = Field(..., description="Maximum possible score")
    percentage: float = Field(..., description="Score as a percentage")
    grade_letter: str = Field(..., description="Letter grade: A, B, C, D, F")
    feedback: str = Field(..., description="Detailed examiner feedback explaining the score")
    missed_points: List[MissedPoint] = Field(
        ...,
        description="Key concepts from the reference material that were absent from the answer",
    )
    correct_points: List[str] = Field(
        ...,
        description="Points the student got right according to reference material",
    )
    context_based: bool = Field(
        ...,
        description="True if grading was based on retrieved context; False if no context was found",
    )
    subject: str
    branch: str
