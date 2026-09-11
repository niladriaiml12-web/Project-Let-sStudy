"""
app/services/grading_service.py

LLM-powered answer grading service.

ANTI-HALLUCINATION RULES (strictly enforced in the grading prompt):
1. The LLM may ONLY award marks based on content present in the retrieved reference context.
2. If the student writes something correct but NOT in the reference material, it cannot be credited.
3. The score must be justified point-by-point against the reference material.
4. If no reference material is found, grading is declined with a clear explanation.
"""
import json
import re
from typing import List, Optional

import structlog

from app.schemas.grade import GradeResponse, MissedPoint
from app.services.llm_service import generate_text
from app.services.retrieval_service import RetrievedChunk, retrieve

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Grading System Prompt
# ---------------------------------------------------------------------------

GRADING_SYSTEM_PROMPT = """You are a strict, fair, and impartial academic examiner for engineering students.
Your ONLY job is to evaluate a student's answer against the provided reference study material.

ABSOLUTE RULES (violation is not permitted):
1. You MUST grade the student's answer ONLY based on the "Reference Study Material" provided.
2. You CANNOT use any knowledge from your training data, external sources, or the internet.
3. If a student writes something that is factually correct in general but NOT found in the reference material, 
   you CANNOT award marks for it. The reference material is the ground truth.
4. If no reference material is provided or it is insufficient, set score to -1 and explain why.
5. Be specific: for every point deducted, cite what was missing from the student's answer compared to the reference.

SCORING RUBRIC:
- Award marks proportionally based on how many key concepts from the reference material the student covered.
- Full marks: Student covered all key points from the reference material with reasonable accuracy.
- Partial marks: Student covered some key points, missed others.
- Zero marks: Student's answer has no overlap with the reference material.

OUTPUT FORMAT (respond ONLY with valid JSON, no markdown, no extra text):
{
  "score": <integer, 0 to max_marks, or -1 if cannot grade>,
  "max_score": <max_marks>,
  "feedback": "<detailed examiner feedback explaining the score>",
  "missed_points": [
    {"point": "<missed concept>", "importance": "critical|important|bonus"}
  ],
  "correct_points": ["<point student got right according to reference>"]
}
"""


def _build_grading_prompt(
    question: str,
    student_answer: str,
    context_chunks: List[RetrievedChunk],
    max_marks: int,
) -> str:
    """Builds the grading prompt with reference material and student answer."""

    if not context_chunks:
        return f"""Reference Study Material:
[NO REFERENCE MATERIAL FOUND — Cannot grade without reference context]

Question: {question}

Student's Answer: {student_answer}

Max Marks: {max_marks}

Since no reference material was found, set score to -1 and explain that grading 
requires the relevant notes to be uploaded first."""

    # Format reference context
    reference_parts = []
    for i, chunk in enumerate(context_chunks, start=1):
        reference_parts.append(
            f"--- Reference {i} (from: {chunk.source_file}) ---\n{chunk.content}"
        )

    reference_text = "\n\n".join(reference_parts)

    return f"""Reference Study Material (THIS IS THE ONLY SOURCE FOR GRADING):
{reference_text}

---

Question: {question}

Student's Answer:
{student_answer}

Max Marks: {max_marks}

Grade the student's answer STRICTLY based only on the reference material above.
Respond with ONLY a valid JSON object matching the specified format."""


def _compute_grade_letter(score: int, max_score: int) -> str:
    """Converts a numeric score to a letter grade."""
    if max_score <= 0:
        return "N/A"
    percentage = (score / max_score) * 100
    if percentage >= 90:
        return "A+"
    elif percentage >= 80:
        return "A"
    elif percentage >= 70:
        return "B"
    elif percentage >= 60:
        return "C"
    elif percentage >= 50:
        return "D"
    else:
        return "F"


def _parse_grading_response(
    raw_response: str,
    max_marks: int,
    question: str,
    branch: str,
    subject: str,
    context_found: bool,
) -> GradeResponse:
    """
    Parses the LLM's JSON grading response into a GradeResponse object.
    Falls back gracefully if JSON parsing fails.
    """
    # Strip markdown code fences if present (LLMs sometimes add them)
    cleaned = raw_response.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse grading JSON", error=str(e), raw=raw_response[:500])
        # Return a fail-safe response indicating parsing error
        return GradeResponse(
            question=question,
            score=0,
            max_score=max_marks,
            percentage=0.0,
            grade_letter="F",
            feedback=(
                f"Grading system error: Could not parse the evaluation response. "
                f"Raw response: {raw_response[:300]}"
            ),
            missed_points=[],
            correct_points=[],
            context_based=context_found,
            subject=subject,
            branch=branch,
        )

    score = int(data.get("score", 0))
    missed_raw = data.get("missed_points", [])
    correct_raw = data.get("correct_points", [])

    # Handle -1 score (cannot grade — no context)
    if score == -1:
        return GradeResponse(
            question=question,
            score=0,
            max_score=max_marks,
            percentage=0.0,
            grade_letter="N/A",
            feedback=data.get("feedback", "Cannot grade: no reference material found."),
            missed_points=[],
            correct_points=[],
            context_based=False,
            subject=subject,
            branch=branch,
        )

    # Clamp score to valid range
    score = max(0, min(score, max_marks))
    percentage = round((score / max_marks) * 100, 1) if max_marks > 0 else 0.0

    missed_points = [
        MissedPoint(
            point=mp.get("point", str(mp)) if isinstance(mp, dict) else str(mp),
            importance=mp.get("importance", "important") if isinstance(mp, dict) else "important",
        )
        for mp in missed_raw
    ]

    correct_points = [str(cp) for cp in correct_raw]

    return GradeResponse(
        question=question,
        score=score,
        max_score=max_marks,
        percentage=percentage,
        grade_letter=_compute_grade_letter(score, max_marks),
        feedback=data.get("feedback", "No feedback provided."),
        missed_points=missed_points,
        correct_points=correct_points,
        context_based=context_found,
        subject=subject,
        branch=branch,
    )


async def grade_answer(
    question: str,
    student_answer: str,
    branch: str,
    subject: str,
    max_marks: int = 10,
    top_k: Optional[int] = None,
) -> GradeResponse:
    """
    Full answer grading pipeline:
      1. Retrieve reference material from ChromaDB (tenant-isolated)
      2. Build strict anti-hallucination grading prompt
      3. Call Gemini LLM for structured JSON evaluation
      4. Parse and return a typed GradeResponse
    
    Args:
        question:       The exam question
        student_answer: The student's written answer
        branch:         Tenant branch code (for ChromaDB isolation)
        subject:        Subject code (for ChromaDB isolation)
        max_marks:      Maximum marks for the question
        top_k:          Number of reference chunks to retrieve
    
    Returns:
        GradeResponse with score, feedback, missed points, and correct points
    """
    logger.info(
        "Grading pipeline started",
        branch=branch,
        subject=subject,
        question_len=len(question),
        answer_len=len(student_answer),
    )

    # -------------------------------------------------------------------------
    # Step 1: Retrieve reference material (tenant-isolated)
    # Use the question as the retrieval query to find relevant reference chunks
    # -------------------------------------------------------------------------
    context_chunks = await retrieve(
        query=question,
        branch=branch,
        subject=subject,
        top_k=top_k,
        min_relevance_score=0.1,  # Filter very low relevance chunks
    )

    context_found = len(context_chunks) > 0
    logger.info(
        "Reference material retrieved for grading",
        chunks_found=len(context_chunks),
        context_found=context_found,
    )

    # -------------------------------------------------------------------------
    # Step 2: Build grading prompt
    # -------------------------------------------------------------------------
    prompt = _build_grading_prompt(
        question=question,
        student_answer=student_answer,
        context_chunks=context_chunks,
        max_marks=max_marks,
    )

    # -------------------------------------------------------------------------
    # Step 3: Call LLM for structured grading (JSON output mode)
    # temperature=0 for deterministic, consistent grading
    # -------------------------------------------------------------------------
    logger.info("Calling LLM for grading", context_chunks=len(context_chunks))
    raw_response = await generate_text(
        prompt=prompt,
        system_instruction=GRADING_SYSTEM_PROMPT,
        temperature=0.0,     # Deterministic grading — no randomness
        max_output_tokens=1024,
    )

    # -------------------------------------------------------------------------
    # Step 4: Parse JSON response into GradeResponse
    # -------------------------------------------------------------------------
    result = _parse_grading_response(
        raw_response=raw_response,
        max_marks=max_marks,
        question=question,
        branch=branch,
        subject=subject,
        context_found=context_found,
    )

    logger.info(
        "Grading complete",
        branch=branch,
        subject=subject,
        score=f"{result.score}/{result.max_score}",
        grade=result.grade_letter,
    )

    return result
