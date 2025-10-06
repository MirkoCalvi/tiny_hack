import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers.analysis import router as analysis_router
from app.services.ai_service import lifespan_context


def create_app() -> FastAPI:
    app = FastAPI(
        title="MoodSip API",
        description="Analyzes facial expressions for signs of dehydration and fatigue.",
        version="1.0.0",
        lifespan=lifespan_context,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    app.include_router(analysis_router)
    return app
