from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import dataclass
import uuid

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comunicacion import Comunicacion
from app.models.estructura import Materia
from app.models.padron import EntradaPadron
from app.models.base import Tenant
from app.repositories.tenant_scoped import TenantScopedRepository


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class CommunicationApprovalPolicy:
    requires_approval: bool | None
    requires_massive_approval: bool | None


class ComunicacionRepository(TenantScopedRepository[Comunicacion]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        super().__init__(session=session, model=Comunicacion, tenant_id=tenant_id)

    async def list_by_idempotency_key(self, idempotency_key: str) -> list[Comunicacion]:
        stmt = self._base_query().where(Comunicacion.idempotency_key == idempotency_key).order_by(Comunicacion.created_at.asc())
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def list_by_lote_id(self, lote_id: uuid.UUID) -> list[Comunicacion]:
        stmt = self._base_query().where(Comunicacion.lote_id == lote_id).order_by(Comunicacion.created_at.asc())
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def list_dispatchable_for_update(self, *, limit: int) -> list[Comunicacion]:
        stmt: Select[tuple[Comunicacion]] = (
            self._base_query()
            .where(Comunicacion.estado == "Pendiente")
            .where((Comunicacion.requiere_aprobacion.is_(False)) | (Comunicacion.aprobado_at.is_not(None)))
            .order_by(Comunicacion.created_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self.session.scalars(stmt)
        return list(result.all())


class CommunicationRecipientRepository:
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        self.session = session
        self.tenant_id = uuid.UUID(str(tenant_id)) if not isinstance(tenant_id, uuid.UUID) else tenant_id

    async def get_materia(self, materia_id: uuid.UUID) -> Materia | None:
        stmt = select(Materia).where(Materia.tenant_id == self.tenant_id).where(Materia.deleted_at.is_(None)).where(Materia.id == materia_id)
        return await self.session.scalar(stmt)

    async def list_entries(self, entry_ids: list[uuid.UUID]) -> list[EntradaPadron]:
        if not entry_ids:
            return []
        stmt = (
            select(EntradaPadron)
            .where(EntradaPadron.tenant_id == self.tenant_id)
            .where(EntradaPadron.deleted_at.is_(None))
            .where(EntradaPadron.id.in_(entry_ids))
        )
        result = await self.session.scalars(stmt)
        return list(result.all())


class CommunicationTenantRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def get_approval_policy(self, tenant_id: uuid.UUID) -> CommunicationApprovalPolicy:
        stmt = (
            select(Tenant.comunicaciones_aprobacion_requerida, Tenant.comunicaciones_aprobacion_masiva)
            .where(Tenant.id == tenant_id)
            .where(Tenant.deleted_at.is_(None))
        )
        row = (await self.session.execute(stmt)).one_or_none()
        if row is None:
            return CommunicationApprovalPolicy(requires_approval=None, requires_massive_approval=None)
        return CommunicationApprovalPolicy(
            requires_approval=row[0],
            requires_massive_approval=row[1],
        )

    async def list_tenant_ids_with_pending(self) -> list[uuid.UUID]:
        stmt = (
            select(Comunicacion.tenant_id)
            .where(Comunicacion.deleted_at.is_(None))
            .where(Comunicacion.estado == "Pendiente")
            .distinct()
        )
        result = await self.session.scalars(stmt)
        return list(result.all())
