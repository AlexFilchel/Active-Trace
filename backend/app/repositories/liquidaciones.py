from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.liquidaciones import Factura, Liquidacion, SalarioBase, SalarioPlus
from app.repositories.tenant_scoped import TenantScopedRepository


def _periodo_date(periodo: str) -> date:
    """Convierte 'AAAA-MM' al primer día del mes para comparaciones de vigencia."""
    year, month = int(periodo[:4]), int(periodo[5:7])
    return date(year, month, 1)


class SalarioBaseRepository(TenantScopedRepository[SalarioBase]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        super().__init__(session=session, model=SalarioBase, tenant_id=tenant_id)

    async def listar(
        self,
        rol: str | None = None,
        periodo: str | None = None,
    ) -> list[SalarioBase]:
        stmt = self._base_query()
        if rol is not None:
            stmt = stmt.where(SalarioBase.rol == rol)
        if periodo is not None:
            d = _periodo_date(periodo)
            stmt = stmt.where(SalarioBase.desde <= d).where(
                (SalarioBase.hasta.is_(None)) | (SalarioBase.hasta >= d)
            )
        result = await self.session.scalars(stmt.order_by(SalarioBase.desde.desc()))
        return list(result.all())

    async def vigente_para(self, rol: str, periodo: str) -> SalarioBase | None:
        d = _periodo_date(periodo)
        stmt = (
            self._base_query()
            .where(SalarioBase.rol == rol)
            .where(SalarioBase.desde <= d)
            .where((SalarioBase.hasta.is_(None)) | (SalarioBase.hasta >= d))
            .order_by(SalarioBase.desde.desc())
            .limit(1)
        )
        return await self.session.scalar(stmt)


class SalarioPlusRepository(TenantScopedRepository[SalarioPlus]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        super().__init__(session=session, model=SalarioPlus, tenant_id=tenant_id)

    async def listar(
        self,
        grupo: str | None = None,
        rol: str | None = None,
        periodo: str | None = None,
    ) -> list[SalarioPlus]:
        stmt = self._base_query()
        if grupo is not None:
            stmt = stmt.where(SalarioPlus.grupo == grupo)
        if rol is not None:
            stmt = stmt.where(SalarioPlus.rol == rol)
        if periodo is not None:
            d = _periodo_date(periodo)
            stmt = stmt.where(SalarioPlus.desde <= d).where(
                (SalarioPlus.hasta.is_(None)) | (SalarioPlus.hasta >= d)
            )
        result = await self.session.scalars(stmt.order_by(SalarioPlus.grupo, SalarioPlus.rol))
        return list(result.all())

    async def vigentes_para_periodo(self, periodo: str) -> list[SalarioPlus]:
        d = _periodo_date(periodo)
        stmt = (
            self._base_query()
            .where(SalarioPlus.desde <= d)
            .where((SalarioPlus.hasta.is_(None)) | (SalarioPlus.hasta >= d))
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def vigente_para(self, grupo: str, rol: str, periodo: str) -> SalarioPlus | None:
        d = _periodo_date(periodo)
        stmt = (
            self._base_query()
            .where(SalarioPlus.grupo == grupo)
            .where(SalarioPlus.rol == rol)
            .where(SalarioPlus.desde <= d)
            .where((SalarioPlus.hasta.is_(None)) | (SalarioPlus.hasta >= d))
            .order_by(SalarioPlus.desde.desc())
            .limit(1)
        )
        return await self.session.scalar(stmt)


class LiquidacionRepository(TenantScopedRepository[Liquidacion]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        super().__init__(session=session, model=Liquidacion, tenant_id=tenant_id)

    async def listar(
        self,
        cohorte_id: uuid.UUID | None = None,
        periodo: str | None = None,
        estado: str | None = None,
        usuario_id: uuid.UUID | None = None,
    ) -> list[Liquidacion]:
        stmt = self._base_query()
        if cohorte_id is not None:
            stmt = stmt.where(Liquidacion.cohorte_id == cohorte_id)
        if periodo is not None:
            stmt = stmt.where(Liquidacion.periodo == periodo)
        if estado is not None:
            stmt = stmt.where(Liquidacion.estado == estado)
        if usuario_id is not None:
            stmt = stmt.where(Liquidacion.usuario_id == usuario_id)
        result = await self.session.scalars(stmt.order_by(Liquidacion.usuario_id))
        return list(result.all())

    async def estado_periodo(self, cohorte_id: uuid.UUID, periodo: str) -> str | None:
        stmt = (
            self._base_query()
            .where(Liquidacion.cohorte_id == cohorte_id)
            .where(Liquidacion.periodo == periodo)
            .limit(1)
        )
        row = await self.session.scalar(stmt)
        return row.estado if row else None

    async def upsert_para_periodo(
        self,
        cohorte_id: uuid.UUID,
        periodo: str,
        rows: list[dict[str, Any]],
    ) -> list[Liquidacion]:
        existing = {
            (r.usuario_id, r.rol): r
            for r in await self.listar(cohorte_id=cohorte_id, periodo=periodo)
        }
        result = []
        for row in rows:
            key = (row["usuario_id"], row["rol"])
            if key in existing:
                liq = existing[key]
                for field, val in row.items():
                    setattr(liq, field, val)
                await self.session.flush()
            else:
                liq = Liquidacion(
                    tenant_id=self.context.tenant_id,
                    cohorte_id=cohorte_id,
                    periodo=periodo,
                    **row,
                )
                self.session.add(liq)
                await self.session.flush()
            result.append(liq)
        return result

    async def cerrar_periodo(self, cohorte_id: uuid.UUID, periodo: str) -> int:
        stmt = (
            update(Liquidacion)
            .where(Liquidacion.tenant_id == self.context.tenant_id)
            .where(Liquidacion.cohorte_id == cohorte_id)
            .where(Liquidacion.periodo == periodo)
            .where(Liquidacion.deleted_at.is_(None))
            .values(estado="Cerrada")
        )
        result = await self.session.execute(stmt)
        return result.rowcount


class FacturaRepository(TenantScopedRepository[Factura]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        super().__init__(session=session, model=Factura, tenant_id=tenant_id)

    async def listar(
        self,
        usuario_id: uuid.UUID | None = None,
        estado: str | None = None,
        periodo: str | None = None,
    ) -> list[Factura]:
        stmt = self._base_query()
        if usuario_id is not None:
            stmt = stmt.where(Factura.usuario_id == usuario_id)
        if estado is not None:
            stmt = stmt.where(Factura.estado == estado)
        if periodo is not None:
            stmt = stmt.where(Factura.periodo == periodo)
        result = await self.session.scalars(stmt.order_by(Factura.cargada_at.desc()))
        return list(result.all())

    async def abonar(self, factura_id: uuid.UUID) -> Factura | None:
        factura = await self.get(factura_id)
        if factura is None:
            return None
        factura.estado = "Abonada"
        factura.abonada_at = datetime.now(timezone.utc)
        await self.session.flush()
        return factura
