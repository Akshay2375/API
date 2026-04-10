import logging

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import ChatRequest, ChatResponse, ErrorResponse
from app.services.chat_service import process_chat
from app.core.exceptions import (
    SQLGenerationError,
    DatabaseError,
    EmptyResultError,
    InvalidQueryError,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid or empty query"},
        404: {"model": ErrorResponse, "description": "No results found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        503: {"model": ErrorResponse, "description": "AI or database unavailable"},
    },
    summary="Chat with the College Advisor",
    description=(
        "Send a natural language question about Maharashtra engineering colleges. "
        "The API generates SQL, queries the database, and returns a human-readable answer."
    ),
)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        return process_chat(request.query)

    except InvalidQueryError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except SQLGenerationError as exc:
        logger.warning("SQL generation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )

    except EmptyResultError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    except DatabaseError as exc:
        logger.error("Database error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )

    except Exception as exc:
        logger.exception("Unexpected error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again.",
        )
