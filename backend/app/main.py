from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.routers.auth import router as auth_router
from app.api.v1.routers.health import router as health_router
from app.core.config import get_settings
from app.core.database import dispose_database, initialize_database
from app.core.logging import configure_logging
from app.core.observability import configure_observability
from app.services.auth import InMemoryLoginRateLimiter, NullRecoveryDelivery


@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize_database()
    yield
    await dispose_database()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    initialize_database()

    app = FastAPI(title="activia-trace", lifespan=lifespan)
    app.state.login_rate_limiter = InMemoryLoginRateLimiter()
    app.state.recovery_delivery = NullRecoveryDelivery()
    app.include_router(health_router)
    app.include_router(auth_router)
    configure_observability(app, settings)
    return app


app = create_app()
