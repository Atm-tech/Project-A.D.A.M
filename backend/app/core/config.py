from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central application configuration."""

    PROJECT_NAME: str = "Retail Data Backend"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = Field(default="local", validation_alias="ENV", description="Deployment environment")

    # Database
    DATABASE_URL: str = Field(..., env="DATABASE_URL")

    # Background jobs (Celery/Redis)
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/1")

    # Observability
    LOG_LEVEL: str = Field(default="INFO")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
