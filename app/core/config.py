from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    APP_NAME: str = "College Chatbot API"
    APP_VERSION: str = "1.0.0"
    ALLOWED_ORIGINS: List[str] = ["*"]

    # Gemini AI
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.5-flash-lite"

    # PostgreSQL (Neon)
    DB_HOST: str
    DB_NAME: str 


    
    DB_USER: str
    DB_PASSWORD: str
    DB_PORT: int = 5432
    DB_SSLMODE: str = "require"

    # Query limits
    DEFAULT_RESULT_LIMIT: int = 10
    MAX_RESULT_LIMIT: int = 50

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
