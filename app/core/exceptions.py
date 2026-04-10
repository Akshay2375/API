class ChatbotException(Exception):
    """Base exception for chatbot errors."""
    pass


class SQLGenerationError(ChatbotException):
    """Raised when the AI fails to generate a valid SQL query."""
    pass


class DatabaseError(ChatbotException):
    """Raised when a database operation fails."""
    pass


class EmptyResultError(ChatbotException):
    """Raised when the query returns no results."""
    pass


class InvalidQueryError(ChatbotException):
    """Raised for invalid or dangerous SQL queries."""
    pass
