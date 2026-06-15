from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mensajeria import HiloMensaje, MensajeInterno
from app.models.usuarios import Usuario
from app.repositories.mensajeria import HiloMensajeRepository, MensajeInternoRepository
from app.schemas.mensajeria import HiloMensajeResponse, MensajeInternoResponse


class MensajeriaService:
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self._hilos = HiloMensajeRepository(session=session, tenant_id=tenant_id)
        self._mensajes = MensajeInternoRepository(session=session, tenant_id=tenant_id)

    async def _get_usuario_en_tenant(self, usuario_id: uuid.UUID) -> Usuario | None:
        stmt = (
            select(Usuario)
            .where(Usuario.tenant_id == self.tenant_id)
            .where(Usuario.id == usuario_id)
            .where(Usuario.deleted_at.is_(None))
        )
        return await self.session.scalar(stmt)

    async def crear_hilo(
        self,
        *,
        remitente_id: uuid.UUID,
        destinatario_id: uuid.UUID,
        asunto: str,
        cuerpo: str,
    ) -> HiloMensajeResponse:
        if remitente_id == destinatario_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="No podés enviarte mensajes a vos mismo.",
            )
        destinatario = await self._get_usuario_en_tenant(destinatario_id)
        if destinatario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destinatario no encontrado.")

        hilo = await self._hilos.crear(asunto=asunto, creado_por=remitente_id)
        mensaje = await self._mensajes.crear(
            hilo_id=hilo.id,
            remitente_id=remitente_id,
            destinatario_id=destinatario_id,
            cuerpo=cuerpo,
        )
        await self.session.commit()
        return self._build_hilo_response(hilo, no_leidos=0, ultimo=mensaje)

    async def listar_hilos(self, usuario_id: uuid.UUID) -> list[HiloMensajeResponse]:
        rows = await self._hilos.listar_por_destinatario(usuario_id)
        return [
            self._build_hilo_response(r["hilo"], r["mensajes_no_leidos"], r["ultimo_mensaje"])
            for r in rows
        ]

    async def listar_mensajes(
        self, hilo_id: uuid.UUID, usuario_id: uuid.UUID
    ) -> list[MensajeInternoResponse]:
        hilo = await self._hilos.get(hilo_id)
        if hilo is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hilo no encontrado.")

        es_participante = await self._hilos.es_participante(hilo_id, usuario_id)
        if not es_participante:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No sos participante de este hilo.")

        mensajes = await self._mensajes.listar_por_hilo(hilo_id)
        # Build responses before marking as read so the response reflects the pre-read state
        response = [self._build_mensaje_response(m) for m in mensajes]
        await self._mensajes.marcar_leidos(hilo_id, usuario_id)
        await self.session.commit()
        return response

    async def responder(
        self,
        *,
        hilo_id: uuid.UUID,
        remitente_id: uuid.UUID,
        destinatario_id: uuid.UUID,
        cuerpo: str,
    ) -> MensajeInternoResponse:
        if remitente_id == destinatario_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="No podés enviarte mensajes a vos mismo.",
            )
        hilo = await self._hilos.get(hilo_id)
        if hilo is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hilo no encontrado.")

        es_participante = await self._hilos.es_participante(hilo_id, remitente_id)
        if not es_participante:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No sos participante de este hilo.")

        destinatario = await self._get_usuario_en_tenant(destinatario_id)
        if destinatario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destinatario no encontrado.")

        mensaje = await self._mensajes.crear(
            hilo_id=hilo_id,
            remitente_id=remitente_id,
            destinatario_id=destinatario_id,
            cuerpo=cuerpo,
        )
        await self.session.commit()
        return self._build_mensaje_response(mensaje)

    def _build_hilo_response(
        self,
        hilo: HiloMensaje,
        no_leidos: int,
        ultimo: MensajeInterno | None,
    ) -> HiloMensajeResponse:
        return HiloMensajeResponse(
            id=hilo.id,
            asunto=hilo.asunto,
            creado_por=hilo.creado_por,
            created_at=hilo.created_at,
            mensajes_no_leidos=no_leidos,
            ultimo_mensaje=self._build_mensaje_response(ultimo) if ultimo else None,
        )

    def _build_mensaje_response(self, msg: MensajeInterno) -> MensajeInternoResponse:
        return MensajeInternoResponse(
            id=msg.id,
            hilo_id=msg.hilo_id,
            remitente_id=msg.remitente_id,
            destinatario_id=msg.destinatario_id,
            cuerpo=msg.cuerpo,
            leido=msg.leido,
            sent_at=msg.sent_at,
        )
