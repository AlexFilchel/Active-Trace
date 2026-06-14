from app.models.audit import AuditLog
from app.models.avisos import AcknowledgmentAviso, Aviso
from app.models.comunicacion import Comunicacion
from app.models.auth import AuthLoginChallenge, AuthPasswordResetToken, AuthRefreshSession, AuthTotpCredential, AuthUser
from app.models.base import Tenant, TenantScopedMixin, UuidLifecycleMixin
from app.models.calificacion import Calificacion, FinalizacionActividad, UmbralMateria
from app.models.encuentros import Guardia, InstanciaEncuentro, SlotEncuentro
from app.models.estructura import Carrera, Cohorte, Materia
from app.models.evaluaciones import (
    CandidatoEvaluacion,
    DiaEvaluacion,
    Evaluacion,
    ReservaEvaluacion,
    ResultadoEvaluacion,
)
from app.models.padron import EntradaPadron, VersionPadron
from app.models.rbac import Permiso, Rol, RolPermiso
from app.models.tareas import ComentarioTarea, Tarea
from app.models.usuarios import Asignacion, Usuario

__all__ = [
    "AcknowledgmentAviso",
    "AuditLog",
    "Aviso",
    "CandidatoEvaluacion",
    "Comunicacion",
    "AuthLoginChallenge",
    "AuthPasswordResetToken",
    "AuthRefreshSession",
    "AuthTotpCredential",
    "AuthUser",
    "Asignacion",
    "Calificacion",
    "Carrera",
    "Cohorte",
    "DiaEvaluacion",
    "EntradaPadron",
    "Evaluacion",
    "FinalizacionActividad",
    "Guardia",
    "InstanciaEncuentro",
    "Materia",
    "Permiso",
    "ReservaEvaluacion",
    "ResultadoEvaluacion",
    "Rol",
    "RolPermiso",
    "SlotEncuentro",
    "ComentarioTarea",
    "Tarea",
    "Tenant",
    "TenantScopedMixin",
    "UmbralMateria",
    "Usuario",
    "UuidLifecycleMixin",
    "VersionPadron",
]
