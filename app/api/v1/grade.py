"""
app/api/v1/grade.py

Answer grading endpoint.
Students submit their written answers and receive structured
feedback graded strictly against their uploaded study materials.

All endpoints require X-API-Key authentication.
"""
from fastapi import APIRouter

from app.dependencies import AuthenticatedGroup
from app.schemas.grade import GradeRequest, GradeResponse
from app.services.grading_service import grade_answer

router = APIRouter()


@router.post(
    "/answer",
    response_model=GradeResponse,
    summary="Grade a student's written answer",
)
async def grade_answer_endpoint(
    payload: GradeRequest,
    group: AuthenticatedGroup,
):
    """
    Grades a student's answer against their uploaded study materials.
    
    **How it works:**
    1. The question is used to retrieve the most relevant reference material from
       **your group's** ChromaDB collection for the specified subject
    2. Gemini LLM acts as a strict examiner, evaluating the student's answer
       ONLY against the retrieved reference material
    3. Returns a structured grade with score, feedback, and specific missed points
    
    **Anti-hallucination guarantee:**
    The LLM is strictly instructed to ONLY award marks for content present in
    your uploaded study notes. It cannot use external knowledge for grading.
    
    **If reference material is not found:**
    The grade will indicate that grading cannot proceed until the relevant
    notes are uploaded.
    
    **Score explanation:**
    - `score` / `max_marks` based on how many key concepts from reference notes were covered
    - `missed_points` lists specific concepts from your notes that were absent from the answer
    - `correct_points` confirms what the student got right
    """
    result = await grade_answer(
        question=payload.question,
        student_answer=payload.student_answer,
        branch=group.branch_code,
        subject=payload.subject,
        max_marks=payload.max_marks or 10,
    )
    return result
