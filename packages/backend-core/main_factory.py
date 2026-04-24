# packages/backend-core/main_factory.py

import logging
from contextlib import asynccontextmanager
from typing import List

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import auth_router
from .config import get_settings
from .database import create_db_and_tables
from .stripe_handler import stripe_router, webhook_router

logger = logging.getLogger(__name__)


def create_app(
    title: str,
    description: str = "",
    domain_routers: List[APIRouter] | None = None,
) -> FastAPI:
    settings = get_settings()

    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    scheduler = AsyncIOScheduler()
    app_instance = None # Placeholder for closure access

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("Starting %s...", title)
        await create_db_and_tables()
        scheduler.start()
        logger.info("Database tables created & Scheduler started")
        yield
        scheduler.shutdown()
        logger.info("Shutting down %s...", title)

    app = FastAPI(
        title=title,
        description=description,
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )
    app.state.scheduler = scheduler

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": title}

    # Core routers
    app.include_router(auth_router)
    app.include_router(stripe_router)
    app.include_router(webhook_router)

    # Domain-specific routers
    if domain_routers:
        for router in domain_routers:
            app.include_router(router)

    return app
