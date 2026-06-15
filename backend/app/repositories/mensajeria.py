from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mensajeria import HiloMensaje, MensajeInterno


class HiloMensajeRepository:
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id

    async def crear(self, *, asunto: str, creado_por: uuid.UUID) -> HiloMensaje:
        hilo = HiloMensaje(tenant_id=self.tenant_id, asunto=asunto, creado_por=creado_por)
        self.session.add(hilo)
        await self.session.flush()
        return hilo

    async def get(self, hilo_id: uuid.UUID) -> HiloMensaje | None:
        stmt = (
            select(HiloMensaje)
            .where(HiloMensaje.tenant_id == self.tenant_id)
            .where(HiloMensaje.id == hilo_id)
            .where(HiloMensaje.deleted_at.is_(None))
        )
        return await self.session.scalar(stmt)

    async def listar_por_destinatario(self, destinatario_id: uuid.UUID) -> list[dict]:
        # Hilos donde el usuario es destinatario de al menos un mensaje
        hilo_ids_stmt = (
            select(MensajeInterno.hilo_id)
            .where(MensajeInterno.tenant_id == self.tenant_id)
            .where(MensajeInterno.destinatario_id == destinatario_id)
            .where(MensajeInterno.deleted_at.is_(None))
            .distinct()
        )
        hilo_ids = list((await self.session.scalars(hilo_ids_stmt)).all())
        if not hilo_ids:
            return []

        hilos_stmt = (
            select(HiloMensaje)
            .where(HiloMensaje.tenant_id == self.tenant_id)
            .where(HiloMensaje.id.in_(hilo_ids))
            .where(HiloMensaje.deleted_at.is_(None))
            .order_by(HiloMensaje.created_at.desc())
        )
        hilos = list((await self.session.scalars(hilos_stmt)).all())

        result = []
        for hilo in hilos:
            no_leidos_stmt = (
                select(func.count())
                .select_from(MensajeInterno)
                .where(MensajeInterno.hilo_id == hilo.id)
                .where(MensajeInterno.destinatario_id == destinatario_id)
                .where(MensajeInterno.leido.is_(False))
                .where(MensajeInterno.deleted_at.is_(None))
            )
            no_leidos = (await self.session.scalar(no_leidos_stmt)) or 0

            ultimo_stmt = (
                select(MensajeInterno)
                .where(MensajeInterno.hilo_id == hilo.id)
                .where(MensajeInterno.deleted_at.is_(None))
                .order_by(MensajeInterno.sent_at.desc())
                .limit(1)
            )
            ultimo = await self.session.scalar(ultimo_stmt)

            result.append({
                "hilo": hilo,
                "mensajes_no_leidos": no_leidos,
                "ultimo_mensaje": ultimo,
            })
        return result

    async def es_participante(self, hilo_id: uuid.UUID, usuario_id: uuid.UUID) -> bool:
        stmt = (
            select(func.count())
            .select_from(MensajeInterno)
            .where(MensajeInterno.tenant_id == self.tenant_id)
            .where(MensajeInterno.hilo_id == hilo_id)
            .where(
                (MensajeInterno.remitente_id == usuario_id)
                | (MensajeInterno.destinatario_id == usuario_id)
            )
            .where(MensajeInterno.deleted_at.is_(None))
        )
        count = (await self.session.scalar(stmt)) or 0
        return count > 0


class MensajeInternoRepository:
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id

    async def crear(
        self,
        *,
        hilo_id: uuid.UUID,
        remitente_id: uuid.UUID,
        destinatario_id: uuid.UUID,
        cuerpo: str,
    ) -> MensajeInterno:
        msg = MensajeInterno(
            tenant_id=self.tenant_id,
            hilo_id=hilo_id,
            remitente_id=remitente_id,
            destinatario_id=destinatario_id,
            cuerpo=cuerpo,
        )
        self.session.add(msg)
        await self.session.flush()
        return msg

    async def listar_por_hilo(self, hilo_id: uuid.UUID) -> list[MensajeInterno]:
        stmt = (
            select(MensajeInterno)
            .where(MensajeInterno.tenant_id == self.tenant_id)
            .where(MensajeInterno.hilo_id == hilo_id)
            .where(MensajeInterno.deleted_at.is_(None))
            .order_by(MensajeInterno.sent_at.asc())
        )
        return list((await self.session.scalars(stmt)).all())

    async def marcar_leidos(self, hilo_id: uuid.UUID, destinatario_id: uuid.UUID) -> None:
        stmt = (
            update(MensajeInterno)
            .where(MensajeInterno.tenant_id == self.tenant_id)
            .where(MensajeInterno.hilo_id == hilo_id)
            .where(MensajeInterno.destinatario_id == destinatario_id)
            .where(MensajeInterno.leido.is_(False))
            .values(leido=True, updated_at=datetime.now(timezone.utc))
        )
        await self.session.execute(stmt)
