"""Router package for API v1."""
from app.api.v1.routers.auth import router as auth_router
from app.api.v1.routers.health import router as health_router
from app.api.v1.routers.usuarios import asignaciones_router, usuarios_router

__all__ = ["asignaciones_router", "auth_router", "health_router", "usuarios_router"]
