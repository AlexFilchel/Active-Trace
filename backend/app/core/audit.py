"""Audit helper for recording significant actions.

Design decision D3 (from design.md):
    audit_action is a simple async function, not a decorator.
    Explicit, testeable, composable — the caller decides what to audit.

Usage example::

    await audit_action(
        session=db,
        actor_id=current_user.user_id,
        tenant_id=current_user.tenant_id,
        accion="CALIFICACIONES_IMPORTAR",
        filas_afectadas=len(rows),
        ip=request.client.host,
    )
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


async def audit_action(
    *,
    session: AsyncSession,
    actor_id: uuid.UUID,
    tenant_id: uuid.UUID,
    accion: str,
    detalle: dict[str, Any] | None = None,
    materia_id: uuid.UUID | None = None,
    filas_afectadas: int = 0,
    ip: str | None = None,
    user_agent: str | None = None,
    impersonando_id: uuid.UUID | None = None,
) -> AuditLog:
    """Create and flush an AuditLog entry.

    Always called within the same transaction as the audited action.
    If this raises, the whole transaction rolls back — by design
    (if the action cannot be audited, it should not proceed).

    Args:
        session:          Active async DB session.
        actor_id:         UUID of the real actor (never the impersonated user).
        tenant_id:        Tenant scope for the record.
        accion:           Standardised action code (e.g. "CALIFICACIONES_IMPORTAR").
        detalle:          Optional JSON dict with additional context.
        materia_id:       Optional FK to a Materia entity.
        filas_afectadas:  Number of rows affected by the action (default 0).
        ip:               Client IP address, if available.
        user_agent:       HTTP User-Agent header, if available.
        impersonando_id:  UUID of the impersonated user (when in impersonation session).

    Returns:
        The created AuditLog instance (already flushed).
    """
    entry = AuditLog(
        tenant_id=tenant_id,
        actor_id=actor_id,
        impersonado_id=impersonando_id,
        materia_id=materia_id,
        accion=accion,
        detalle=detalle,
        filas_afectadas=filas_afectadas,
        ip=ip,
        user_agent=user_agent,
    )
    session.add(entry)
    await session.flush()
    return entry
