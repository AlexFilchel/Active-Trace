from app.repositories.audit import AuditLogRepository
from app.repositories.auth import (
    AuthChallengeRepository,
    AuthIdentityRepository,
    AuthPasswordResetRepository,
    AuthTotpRepository,
    AuthUserRepository,
    LoginChallengeRepository,
    PasswordResetRepository,
    RefreshSessionRepository,
    normalize_email,
)
from app.repositories.estructura import CarreraRepository, CohorteRepository, MateriaRepository
from app.repositories.rbac import RbacRepository
from app.repositories.tenant_scoped import TenantScopedRepository
from app.repositories.usuarios import AsignacionRepository, UsuarioRepository

__all__ = [
    "AuditLogRepository",
    "AuthChallengeRepository",
    "AuthIdentityRepository",
    "AuthPasswordResetRepository",
    "AuthTotpRepository",
    "AuthUserRepository",
    "AsignacionRepository",
    "CarreraRepository",
    "CohorteRepository",
    "LoginChallengeRepository",
    "MateriaRepository",
    "PasswordResetRepository",
    "RbacRepository",
    "RefreshSessionRepository",
    "TenantScopedRepository",
    "UsuarioRepository",
    "normalize_email",
]
