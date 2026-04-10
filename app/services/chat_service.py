import logging

from app.models.schemas import ChatResponse
from app.services.ai_service import generate_sql, generate_natural_response
from app.services.database import DatabaseService
from app.core.exceptions import (
    DatabaseError,
    EmptyResultError,
    SQLGenerationError,
    InvalidQueryError,
)

logger = logging.getLogger(__name__)


def process_chat(query: str) -> ChatResponse:
    """
    Full pipeline:
      1. NLQ  →  SQL  (Gemini)
      2. SQL  →  Rows (PostgreSQL)
      3. Rows →  Answer (Gemini)

    Returns a ChatResponse or raises a ChatbotException subclass.
    """
    logger.info("Processing query: %s", query)

    # Step 1: Generate SQL
    sql = generate_sql(query)

    # Step 2: Execute against DB
    rows = DatabaseService.execute(sql)

    if not rows:
        raise EmptyResultError(
            "No colleges match your criteria. Try broadening your search "
            "(e.g., relax percentile requirements or check city/branch spelling)."
        )

    # Step 3: Natural language answer
    answer = generate_natural_response(query, rows)

    return ChatResponse(
        query=query,
        sql_generated=sql,
        answer=answer,
        row_count=len(rows),
    )
