import logging
from typing import Any, Optional

import psycopg2
from psycopg2 import pool

from app.core.config import settings
from app.core.exceptions import DatabaseError, InvalidQueryError

logger = logging.getLogger(__name__)

# Blocked SQL keywords to prevent write operations via the chat endpoint
_BLOCKED_KEYWORDS = {"drop", "delete", "insert", "update", "truncate", "alter", "create", "grant", "revoke"}


class DatabaseService:
    """Manages a PostgreSQL connection pool and executes read-only queries."""

    _pool: Optional[pool.SimpleConnectionPool] = None

    @classmethod
    def _get_pool(cls) -> pool.SimpleConnectionPool:
        if cls._pool is None:
            try:
                cls._pool = pool.SimpleConnectionPool(
                    minconn=1,
                    maxconn=10,
                    host=settings.DB_HOST,
                    database=settings.DB_NAME,
                    user=settings.DB_USER,
                    password=settings.DB_PASSWORD,
                    port=settings.DB_PORT,
                    sslmode=settings.DB_SSLMODE,
                    connect_timeout=10,
                )
                logger.info("PostgreSQL connection pool initialised.")
            except Exception as exc:
                logger.error("Failed to create DB pool: %s", exc)
                raise DatabaseError(f"Cannot connect to database: {exc}") from exc
        return cls._pool

    @classmethod
    def _validate_query(cls, sql: str) -> None:
        """Reject any SQL that contains write/DDL operations."""
        lower = sql.lower()
        for kw in _BLOCKED_KEYWORDS:
            if kw in lower.split():
                raise InvalidQueryError(
                    f"Query contains a blocked keyword: '{kw}'. "
                    "Only SELECT statements are allowed."
                )

    @classmethod
    def execute(cls, sql: str) -> list[tuple[Any, ...]]:
        """
        Validate and execute a SELECT query.
        Returns a list of rows as tuples.
        Raises DatabaseError or InvalidQueryError on failure.
        """
        cls._validate_query(sql)

        db_pool = cls._get_pool()
        conn = None
        try:
            conn = db_pool.getconn()
            with conn.cursor() as cursor:
                cursor.execute(sql)
                rows = cursor.fetchall()
            conn.rollback()  # keep connection clean for pool reuse
            logger.info("Query returned %d rows.", len(rows))
            return rows
        except InvalidQueryError:
            raise
        except psycopg2.Error as exc:
            logger.error("psycopg2 error: %s | SQL: %s", exc, sql)
            raise DatabaseError(f"Database query failed: {exc.pgerror or str(exc)}") from exc
        except Exception as exc:
            logger.error("Unexpected DB error: %s", exc)
            raise DatabaseError(f"Unexpected database error: {exc}") from exc
        finally:
            if conn:
                db_pool.putconn(conn)

    @classmethod
    def close_pool(cls) -> None:
        if cls._pool:
            cls._pool.closeall()
            cls._pool = None
            logger.info("PostgreSQL connection pool closed.")
