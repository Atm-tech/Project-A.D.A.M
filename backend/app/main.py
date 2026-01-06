import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title=settings.PROJECT_NAME)

    # Allow frontend callers (dev server/static file served)
    default_cors = {
        "allow_origins": [
            # Local static server + common dev ports
            "http://localhost:4173",
            "http://127.0.0.1:4173",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            # Direct backend origin (same host)
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ],
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }

    # Optional override: CORS_ORIGINS="https://app.example.com,https://admin.example.com"
    env_origins = os.getenv("CORS_ORIGINS")
    if env_origins:
        default_cors["allow_origins"].extend(
            [o.strip() for o in env_origins.split(",") if o.strip()]
        )

    app.add_middleware(
        CORSMiddleware,
        **default_cors,
    )

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    return app


app = create_app()
