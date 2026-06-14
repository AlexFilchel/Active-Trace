from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.routers.auth import router as auth_router
from app.api.v1.routers.avisos import router as avisos_router
from app.api.v1.routers.programas import fechas_router, programas_router
from app.api.v1.routers.tareas import router as tareas_router
from app.api.v1.routers.coloquios import router as coloquios_router
from app.api.v1.routers.comunicaciones import router as comunicaciones_router
from app.api.v1.routers.analisis import router as analisis_router
from app.api.v1.routers.calificaciones import router as calificaciones_router
from app.api.v1.routers.encuentros import router as encuentros_router
from app.api.v1.routers.equipos import router as equipos_router
from app.api.v1.routers.estructura import router as estructura_router
from app.api.v1.routers.guardias import router as guardias_router
from app.api.v1.routers.health import router as health_router
from app.api.v1.routers.padron import router as padron_router
from app.api.v1.routers.usuarios import asignaciones_router, usuarios_router
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
    app.include_router(estructura_router)
    app.include_router(usuarios_router)
    app.include_router(asignaciones_router)
    app.include_router(equipos_router)
    app.include_router(padron_router)
    app.include_router(calificaciones_router)
    app.include_router(analisis_router)
    app.include_router(comunicaciones_router)
    app.include_router(encuentros_router)
    app.include_router(guardias_router)
    app.include_router(coloquios_router)
    app.include_router(avisos_router)
    app.include_router(tareas_router)
    app.include_router(programas_router)
    app.include_router(fechas_router)
    configure_observability(app, settings)
    return app


app = create_app()
