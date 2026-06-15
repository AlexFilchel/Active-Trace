from __future__ import annotations

import uuid
from calendar import monthrange
from collections import defaultdict
from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.liquidaciones import Liquidacion
from app.models.usuarios import Asignacion, Usuario
from app.models.rbac import Rol
from app.models.estructura import Materia
from app.repositories.audit import AuditLogRepository
from app.repositories.liquidaciones import (
    LiquidacionRepository,
    SalarioBaseRepository,
    SalarioPlusRepository,
)
from app.schemas.liquidaciones import LiquidacionKpisResponse


def _periodo_rango(periodo: str) -> tuple[date, date]:
    year, month = int(periodo[:4]), int(periodo[5:7])
    primer_dia = date(year, month, 1)
    ultimo_dia = date(year, month, monthrange(year, month)[1])
    return primer_dia, ultimo_dia


class LiquidacionService:
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        self.session = session
        self.tenant_id = uuid.UUID(str(tenant_id)) if not isinstance(tenant_id, uuid.UUID) else tenant_id
        self._repo = LiquidacionRepository(session=session, tenant_id=self.tenant_id)
        self._base_repo = SalarioBaseRepository(session=session, tenant_id=self.tenant_id)
        self._plus_repo = SalarioPlusRepository(session=session, tenant_id=self.tenant_id)
        self._audit = AuditLogRepository(session=session, tenant_id=self.tenant_id)

    async def _asignaciones_periodo(
        self, cohorte_id: uuid.UUID, periodo: str
    ) -> list[Asignacion]:
        primer_dia, ultimo_dia = _periodo_rango(periodo)
        stmt = (
            select(Asignacion)
            .where(Asignacion.tenant_id == self.tenant_id)
            .where(Asignacion.cohorte_id == cohorte_id)
            .where(Asignacion.desde <= ultimo_dia)
            .where(
                (Asignacion.hasta.is_(None)) | (Asignacion.hasta >= primer_dia)
            )
            .where(Asignacion.deleted_at.is_(None))
            .where(Asignacion.materia_id.isnot(None))
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def calcular(
        self,
        cohorte_id: uuid.UUID,
        periodo: str,
        actor_id: uuid.UUID,
    ) -> list[Liquidacion]:
        estado = await self._repo.estado_periodo(cohorte_id, periodo)
        if estado == "Cerrada":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La liquidación de este período está cerrada y no puede recalcularse.",
            )

        asignaciones = await self._asignaciones_periodo(cohorte_id, periodo)

        # Agrupa por (usuario_id, rol_id) → lista de materia_ids
        grupos: dict[tuple[uuid.UUID, uuid.UUID], list[uuid.UUID]] = defaultdict(list)
        for a in asignaciones:
            if a.materia_id:
                grupos[(a.usuario_id, a.rol_id)].append(a.materia_id)

        # Carga rol.nombre y usuario.facturador para los IDs involucrados
        rol_ids = {rol_id for _, rol_id in grupos}
        usuario_ids = {uid for uid, _ in grupos}
        materia_ids = {mid for mids in grupos.values() for mid in mids}

        roles_map: dict[uuid.UUID, str] = {}
        if rol_ids:
            result = await self.session.execute(
                select(Rol.id, Rol.nombre)
                .where(Rol.tenant_id == self.tenant_id)
                .where(Rol.id.in_(rol_ids))
            )
            roles_map = {row[0]: row[1] for row in result.all()}

        usuarios_map: dict[uuid.UUID, bool] = {}
        if usuario_ids:
            result = await self.session.execute(
                select(Usuario.id, Usuario.facturador)
                .where(Usuario.tenant_id == self.tenant_id)
                .where(Usuario.id.in_(usuario_ids))
            )
            usuarios_map = {row[0]: row[1] for row in result.all()}

        categorias_map: dict[uuid.UUID, str | None] = {}
        if materia_ids:
            result = await self.session.execute(
                select(Materia.id, Materia.categoria_plus)
                .where(Materia.tenant_id == self.tenant_id)
                .where(Materia.id.in_(materia_ids))
            )
            categorias_map = {row[0]: row[1] for row in result.all()}

        # Plus vigentes del periodo indexados por (grupo, rol)
        plus_vigentes = await self._plus_repo.vigentes_para_periodo(periodo)
        plus_map: dict[tuple[str, str], Decimal] = {
            (p.grupo, p.rol): Decimal(str(p.monto)) for p in plus_vigentes
        }

        rows = []
        for (usuario_id, rol_id), materia_ids_docente in grupos.items():
            rol_nombre = roles_map.get(rol_id, "PROFESOR")
            facturador = usuarios_map.get(usuario_id, False)

            base_rec = await self._base_repo.vigente_para(rol_nombre, periodo)
            monto_base = Decimal(str(base_rec.monto)) if base_rec else Decimal("0")

            # Cuenta comisiones por categoria_plus
            n_por_grupo: dict[str, int] = defaultdict(int)
            for mid in materia_ids_docente:
                cat = categorias_map.get(mid)
                if cat:
                    n_por_grupo[cat] += 1

            monto_plus = Decimal("0")
            for grupo, n in n_por_grupo.items():
                plus_monto = plus_map.get((grupo, rol_nombre), Decimal("0"))
                monto_plus += plus_monto * n

            total = monto_base + monto_plus
            rows.append({
                "usuario_id": usuario_id,
                "rol": rol_nombre,
                "comisiones": [str(mid) for mid in materia_ids_docente],
                "monto_base": monto_base,
                "monto_plus": monto_plus,
                "total": total,
                "es_nexo": rol_nombre == "NEXO",
                "excluido_por_factura": facturador,
                "estado": "Abierta",
            })

        liquidaciones = await self._repo.upsert_para_periodo(cohorte_id, periodo, rows)
        await self._audit.create(
            actor_id=actor_id,
            accion="LIQUIDACION_CALCULAR",
            detalle={"cohorte_id": str(cohorte_id), "periodo": periodo, "docentes": len(rows)},
        )
        await self.session.commit()
        return liquidaciones

    async def cerrar(
        self,
        cohorte_id: uuid.UUID,
        periodo: str,
        actor_id: uuid.UUID,
    ) -> int:
        estado = await self._repo.estado_periodo(cohorte_id, periodo)
        if estado == "Cerrada":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La liquidación de este período ya está cerrada.",
            )
        count = await self._repo.cerrar_periodo(cohorte_id, periodo)
        await self._audit.create(
            actor_id=actor_id,
            accion="LIQUIDACION_CERRAR",
            detalle={"cohorte_id": str(cohorte_id), "periodo": periodo, "filas": count},
        )
        await self.session.commit()
        return count

    async def kpis(self, cohorte_id: uuid.UUID, periodo: str) -> LiquidacionKpisResponse:
        rows = await self._repo.listar(cohorte_id=cohorte_id, periodo=periodo)
        estado = rows[0].estado if rows else None

        total_nexo = Decimal("0")
        total_sin_factura = Decimal("0")
        total_con_factura = Decimal("0")
        cantidad_docentes = 0
        cantidad_facturantes = 0

        for r in rows:
            t = Decimal(str(r.total))
            total_con_factura += t
            if r.excluido_por_factura:
                cantidad_facturantes += 1
            else:
                total_sin_factura += t
                cantidad_docentes += 1
                if r.es_nexo:
                    total_nexo += t

        return LiquidacionKpisResponse(
            cohorte_id=cohorte_id,
            periodo=periodo,
            estado=estado,
            total_sin_factura=total_sin_factura,
            total_con_factura=total_con_factura,
            total_nexo=total_nexo,
            cantidad_docentes=cantidad_docentes,
            cantidad_facturantes=cantidad_facturantes,
        )
