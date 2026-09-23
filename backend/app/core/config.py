from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    All app configuration lives here, pulled from environment variables (.env).
    Add new fields here as later steps need them (auth, groq, etc).
    """

    APP_NAME: str = "Legal Document Assistant"
    ENV: str = "development"
    DEBUG: bool = True

    DATABASE_URL: str = "sqlite:///./app.db"

    # Step 4 — document upload
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_MB: int = 20
    ALLOWED_CONTENT_TYPES: tuple[str, ...] = (
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    # Placeholders for future steps — safe to leave blank for now
    JWT_SECRET: str = "changeme_generate_a_real_secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    GROQ_API_BASE: str = "https://api.groq.com/openai/v1"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Import this singleton everywhere instead of re-reading env vars
settings = Settings()
