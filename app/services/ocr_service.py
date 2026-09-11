"""
app/services/ocr_service.py

OCR service: converts uploaded images/PDFs into Markdown text.
Uses Gemini Vision API for high-quality extraction of handwritten notes.

Supported input formats: JPEG, PNG, WebP (direct image)
PDF support: extracts pages as images via pdf2image (optional dependency).
"""
import io
import mimetypes
from pathlib import Path
from typing import Optional

import structlog

from app.services.llm_service import extract_text_from_image

logger = structlog.get_logger(__name__)

# MIME types that can be sent directly to Gemini Vision
SUPPORTED_IMAGE_MIMES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}

# File extension → MIME type mapping
EXTENSION_MIME_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".pdf": "application/pdf",
}


async def extract_text_from_file(
    file_bytes: bytes,
    filename: str,
    mime_type: Optional[str] = None,
) -> str:
    """
    Main entry point: extracts Markdown text from an uploaded file.
    
    Handles:
    - Single images (JPEG, PNG, WebP) → direct Gemini Vision OCR
    - PDFs → native Gemini multimodal document processing (no poppler needed)
    
    Args:
        file_bytes: Raw file content as bytes
        filename: Original filename (used to detect format)
        mime_type: Optional explicit MIME type (auto-detected from filename if None)
    
    Returns:
        Extracted Markdown text
    """
    # Auto-detect MIME type from filename if not provided
    if not mime_type:
        suffix = Path(filename).suffix.lower()
        mime_type = EXTENSION_MIME_MAP.get(suffix)

        if not mime_type:
            detected, _ = mimetypes.guess_type(filename)
            mime_type = detected

    if not mime_type:
        raise ValueError(
            f"Cannot determine file type for '{filename}'. "
            f"Supported formats: JPEG, PNG, WebP, PDF"
        )

    logger.info("Starting OCR", filename=filename, mime_type=mime_type, size_bytes=len(file_bytes))

    if mime_type in SUPPORTED_IMAGE_MIMES:
        return await _ocr_single_image(file_bytes, mime_type, filename)

    elif mime_type == "application/pdf":
        return await _ocr_pdf(file_bytes, filename)

    else:
        raise ValueError(
            f"Unsupported MIME type: '{mime_type}'. "
            f"Supported: JPEG, PNG, WebP, PDF"
        )


async def _ocr_single_image(file_bytes: bytes, mime_type: str, filename: str) -> str:
    """
    Runs Gemini Vision OCR on a single image.
    """
    logger.info("OCR: processing single image", filename=filename)

    markdown_text = await extract_text_from_image(
        image_bytes=file_bytes,
        mime_type=mime_type,
    )

    logger.info(
        "OCR: single image complete",
        filename=filename,
        output_chars=len(markdown_text),
    )
    return markdown_text


async def _ocr_pdf(file_bytes: bytes, filename: str) -> str:
    """
    Processes a PDF using Gemini's native multimodal document understanding.
    Directly extracts formulas, tables, headings, and handwritten notes
    without requiring poppler or pdf2image system binaries.
    """
    logger.info("OCR: processing PDF natively with Gemini", filename=filename, size_bytes=len(file_bytes))

    markdown_text = await extract_text_from_image(
        image_bytes=file_bytes,
        mime_type="application/pdf",
    )

    logger.info(
        "OCR: PDF complete",
        filename=filename,
        total_chars=len(markdown_text),
    )
    return markdown_text
