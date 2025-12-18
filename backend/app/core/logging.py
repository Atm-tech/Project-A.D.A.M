import logging
from logging.config import dictConfig

from app.core.config import settings


def configure_logging() -> None:
    """
    Configure basic structured logging for the service.

    Keeps configuration minimal so it works the same under uvicorn and tests.
    """
    level = settings.LOG_LEVEL.upper()
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                }
            },
            "root": {"level": level, "handlers": ["console"]},
        }
    )
    logging.getLogger(__name__).info("Logging configured", extra={"level": level})
