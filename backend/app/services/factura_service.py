from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.liquidaciones import Factura
from app.models.usuarios import Usuario
from app.repositories.audit import AuditLogRepository
from app.repositories.liquidaciones import FacturaRepository
from app.schemas.liquidaciones import CrearFacturaRequest, FacturaResponse


class FacturaService:
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        self.session = session
        self.tenant_id = uuid.UUID(str(tenant_id)) if not isinstance(tenant_id, uuid.UUID) else tenant_id
        self._repo = FacturaRepository(session=session, tenant_id=self.tenant_id)
        self._audit = AuditLogRepository(session=session, tenant_id=self.tenant_id)

    async def crear(self, payload: CrearFacturaRequest, actor_id: uuid.UUID) -> Factura:
        usuario = await self.session.scalar(
            select(Usuario)
            .where(Usuario.tenant_id == self.tenant_id)
            .where(Usuario.id == payload.usuario_id)
            .where(Usuario.deleted_at.is_(None))
        )
        if usuario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")
        if not usuario.facturador:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El usuario no tiene modalidad de facturación habilitada.",
            )

        factura = await self._repo.create(
            usuario_id=payload.usuario_id,
            periodo=payload.periodo,
            detalle=payload.detalle,
            referencia_archivo=payload.referencia_archivo,
            tamano_kb=payload.tamano_kb,
        )
        await self._audit.create(
            actor_id=actor_id,
            accion="FACTURA_CREAR",
            detalle={"factura_id": str(factura.id), "usuario_id": str(payload.usuario_id)},
        )
        await self.session.commit()
        return factura

    async def abonar(self, factura_id: uuid.UUID, actor_id: uuid.UUID) -> Factura:
        factura = await self._repo.abonar(factura_id)
        if factura is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Factura no encontrada.")
        await self._audit.create(
            actor_id=actor_id,
            accion="FACTURA_ABONAR",
            detalle={"factura_id": str(factura_id)},
        )
        await self.session.commit()
        return factura

    async def listar(
        self,
        usuario_id: uuid.UUID | None = None,
        estado: str | None = None,
        periodo: str | None = None,
    ) -> list[Factura]:
        return await self._repo.listar(usuario_id=usuario_id, estado=estado, periodo=periodo)
