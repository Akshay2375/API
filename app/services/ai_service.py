import logging
import re
import time
import random
from typing import Any

from google import genai
from google.genai import types

from app.core.config import settings
from app.core.exceptions import SQLGenerationError
from app.core.prompts import SQL_SYSTEM_PROMPT, RESPONSE_SYSTEM_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

# Regex to strip markdown code fences
_CODE_FENCE_RE = re.compile(r"^```(?:sql)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)

# Global Gemini client (optimized)
client = genai.Client(api_key=settings.GEMINI_API_KEY)

# Retry config
MAX_RETRIES = 3


def _call_gemini_with_retry(**kwargs):
    """
    Wrapper to call Gemini API with retry + exponential backoff.
    """
    for attempt in range(MAX_RETRIES):
        try:
            return client.models.generate_content(**kwargs)

        except Exception as exc:
            error_str = str(exc)

            if "503" in error_str or "UNAVAILABLE" in error_str:
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                logger.warning(
                    "Gemini overloaded (attempt %d/%d). Retrying in %.2fs...",
                    attempt + 1,
                    MAX_RETRIES,
                    wait_time,
                )
                time.sleep(wait_time)
            else:
                logger.error("Gemini API error: %s", exc)
                raise

    raise Exception("Gemini API failed after maximum retries")


def generate_sql(natural_language_query: str) -> str:
    """
    Convert a natural language query into a PostgreSQL SELECT statement.
    Returns the cleaned SQL string.
    """
    try:
        response = _call_gemini_with_retry(
            model=settings.GEMINI_MODEL,
            config=types.GenerateContentConfig(
                system_instruction=SQL_SYSTEM_PROMPT,
                temperature=0.1,
                max_output_tokens=1024,
            ),
            contents=natural_language_query,
        )

        raw_sql = response.text or ""

    except Exception as exc:
        logger.error("Gemini SQL generation error: %s", exc)
        raise SQLGenerationError(f"AI failed to generate SQL: {exc}") from exc

    # Clean markdown fences
    cleaned_sql = _CODE_FENCE_RE.sub("", raw_sql).strip()

    # Validate SQL
    if not cleaned_sql or not cleaned_sql.upper().startswith("SELECT"):
        logger.warning("Unexpected SQL output: %s", cleaned_sql)
        raise SQLGenerationError(
            "The AI did not return a valid SELECT statement. Please rephrase your query."
        )

    logger.debug("Generated SQL:\n%s", cleaned_sql)
    return cleaned_sql


def generate_natural_response(
    natural_language_query: str,
    rows: list[tuple[Any, ...]],
) -> str:
    """
    Convert raw database rows into a human-friendly answer.
    """
    import json

    data_str = json.dumps(rows, default=str)
    system_instruction = RESPONSE_SYSTEM_PROMPT_TEMPLATE.format(data=data_str)

    try:
        response = _call_gemini_with_retry(
            model=settings.GEMINI_MODEL,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.4,
                max_output_tokens=2048,
            ),
            contents=natural_language_query,
        )

        return response.text or "I could not generate a response. Please try again."

    except Exception as exc:
        logger.error("Gemini response generation error: %s", exc)

        return (
            "I fetched the data but could not format a response due to high load. "
            "Please try again in a moment."
        )