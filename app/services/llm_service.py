"""
app/services/llm_service.py

Abstraction layer for Google Gemini LLM and embedding calls.
Uses the current `google-genai` SDK (google-generativeai is deprecated).

All AI calls go through here for centralized retry logic,
error handling, and future provider swapping.
"""
import asyncio
from typing import List, Optional

import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import get_settings

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Client Initialization (lazy, cached per module)
# ---------------------------------------------------------------------------

_client = None
_client_lock = asyncio.Lock() if False else None  # Will be set on first use


def _get_client():
    """Lazily initializes and returns the google-genai Client singleton."""
    global _client
    if _client is None:
        from google import genai
        settings = get_settings()
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


# ---------------------------------------------------------------------------
# Text Generation
# ---------------------------------------------------------------------------

@retry(
    retry=retry_if_exception_type(Exception),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(3),
)
async def generate_text(
    prompt: str,
    system_instruction: Optional[str] = None,
    temperature: float = 0.2,
    max_output_tokens: int = 2048,
) -> str:
    """
    Generates text using Gemini LLM.

    Args:
        prompt: The user-facing prompt / question
        system_instruction: System-level instruction for the model
        temperature: Sampling temperature (lower = more deterministic)
        max_output_tokens: Maximum tokens in the response

    Returns:
        Generated text string

    Raises:
        RuntimeError: If generation fails after all retries
    """
    from google.genai import types as genai_types

    client = _get_client()
    settings = get_settings()

    config = genai_types.GenerateContentConfig(
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        system_instruction=system_instruction,
    )

    logger.debug("Calling Gemini LLM", model=settings.llm_model, prompt_len=len(prompt))

    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: client.models.generate_content(
            model=settings.llm_model,
            contents=prompt,
            config=config,
        ),
    )

    if not response.text:
        raise RuntimeError("Gemini returned an empty response")

    logger.debug("Gemini LLM response received", response_len=len(response.text))
    return response.text


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------

@retry(
    retry=retry_if_exception_type(Exception),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(3),
)
async def embed_text(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> List[float]:
    """
    Generates a single text embedding using Google's text-embedding-004 model.

    Args:
        text: The text to embed
        task_type: "RETRIEVAL_DOCUMENT" (indexing) | "RETRIEVAL_QUERY" (querying)

    Returns:
        List of floats representing the embedding vector
    """
    from google.genai import types as genai_types

    client = _get_client()
    settings = get_settings()

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: client.models.embed_content(
            model=settings.embedding_model,
            contents=text,
            config=genai_types.EmbedContentConfig(task_type=task_type),
        ),
    )

    return result.embeddings[0].values


async def embed_batch(
    texts: List[str],
    task_type: str = "RETRIEVAL_DOCUMENT",
    batch_size: int = 100,
) -> List[List[float]]:
    """
    Generates embeddings for a list of texts in batches.
    Google's embedding API supports batches up to 100 items.

    Args:
        texts: List of text strings to embed
        task_type: Embedding task type (see embed_text)
        batch_size: Number of texts per API call (max 100)

    Returns:
        List of embedding vectors, one per input text
    """
    from google.genai import types as genai_types

    client = _get_client()
    settings = get_settings()
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        logger.debug("Embedding batch", batch_num=i // batch_size + 1, size=len(batch))

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda b=batch: client.models.embed_content(
                model=settings.embedding_model,
                contents=b,
                config=genai_types.EmbedContentConfig(task_type=task_type),
            ),
        )

        all_embeddings.extend([emb.values for emb in result.embeddings])

    return all_embeddings


# ---------------------------------------------------------------------------
# Vision / OCR
# ---------------------------------------------------------------------------

@retry(
    retry=retry_if_exception_type(Exception),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(3),
)
async def extract_text_from_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    """
    Extracts text from an image using Gemini Vision API.
    Optimized for handwritten academic notes — outputs clean Markdown.

    Args:
        image_bytes: Raw image file bytes
        mime_type: MIME type of the image ("image/jpeg", "image/png", "image/webp")

    Returns:
        Extracted text as Markdown string
    """
    from google.genai import types as genai_types

    client = _get_client()
    settings = get_settings()

    ocr_system_prompt = """You are an expert OCR system specializing in handwritten academic notes.
Your task is to accurately transcribe the content of the provided image.

Instructions:
1. Extract ALL text visible in the image, including headings, body text, and any diagrams described in words.
2. Format the output as clean Markdown:
   - Use # for main headings, ## for subheadings
   - Use bullet points (- ) for lists
   - Use **bold** for important terms
   - Use `code` for formulas, variables, and code snippets
3. If there are mathematical equations, write them in LaTeX-style notation (e.g., $E = mc^2$).
4. If text is unclear or illegible, mark it as [ILLEGIBLE].
5. Do NOT add any commentary, preamble, or explanation — output ONLY the transcribed Markdown content.
"""

    image_part = genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type)

    logger.info("Running Gemini Vision OCR", mime_type=mime_type, size_bytes=len(image_bytes))

    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: client.models.generate_content(
            model=settings.vision_model,
            contents=[
                genai_types.Content(
                    parts=[
                        genai_types.Part.from_text(text="Please transcribe all text from this academic note image."),
                        image_part,
                    ]
                )
            ],
            config=genai_types.GenerateContentConfig(
                system_instruction=ocr_system_prompt,
                temperature=0.0,
            ),
        ),
    )

    if not response.text or not response.text.strip():
        logger.warning("Gemini Vision returned empty text for image", mime_type=mime_type)
        return "[Note: No readable text found in document image]"

    logger.info("OCR complete", output_chars=len(response.text))
    return response.text
