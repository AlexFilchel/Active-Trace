"""Servicio de estructura académica: Carrera, Cohorte, Materia.

Reglas de negocio:
- Código único por tenant → ConflictError (409)
- Carrera inactiva no admite nuevas cohortes activas → BusinessRuleError (422)
- Entidad de otro tenant → NotFoundError (404)
"""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.estructura import Carrera, Cohorte, Materia
from app.repositories.estructura import CarreraRepository, CohorteRepository, MateriaRepository


class ConflictError(Exception):
    status_code = 409

    def __init__(self, detail: str = "Resource already exists."):
        self.detail = detail
        super().__init__(detail)


class NotFoundError(Exception):
    status_code = 404

    def __init__(self, detail: str = "Resource not found."):
        self.detail = detail
        super().__init__(detail)


class BusinessRuleError(Exception):
    status_code = 422

    def __init__(self, detail: str = "Business rule violation."):
        self.detail = detail
        super().__init__(detail)


class EstructuraService:
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str):
        self.session = session
        self.tenant_id = uuid.UUID(str(tenant_id)) if not isinstance(tenant_id, uuid.UUID) else tenant_id
        self._carrera_repo = CarreraRepository(session=session, tenant_id=tenant_id)
        self._cohorte_repo = CohorteRepository(session=session, tenant_id=tenant_id)
        self._materia_repo = MateriaRepository(session=session, tenant_id=tenant_id)

    # ------------------------------------------------------------------
    # Carrera
    # ------------------------------------------------------------------

    async def crear_carrera(self, *, codigo: str, nombre: str) -> Carrera:
        existing = await self._carrera_repo.get_by_codigo(codigo)
        if existing is not None:
            raise ConflictError(f"Carrera con código '{codigo}' ya existe en este tenant.")
        return await self._carrera_repo.create(codigo=codigo, nombre=nombre)

    async def listar_carreras(self) -> list[Carrera]:
        return await self._carrera_repo.list()

    async def obtener_carrera(self, carrera_id: uuid.UUID) -> Carrera:
        carrera = await self._carrera_repo.get(carrera_id)
        if carrera is None:
            raise NotFoundError("Carrera no encontrada.")
        return carrera

    async def actualizar_carrera(self, carrera_id: uuid.UUID, **fields: object) -> Carrera:
        carrera = await self._carrera_repo.update(carrera_id, **fields)
        if carrera is None:
            raise NotFoundError("Carrera no encontrada.")
        return carrera

    async def eliminar_carrera(self, carrera_id: uuid.UUID) -> None:
        deleted = await self._carrera_repo.soft_delete(carrera_id)
        if not deleted:
            raise NotFoundError("Carrera no encontrada.")

    # ------------------------------------------------------------------
    # Cohorte
    # ------------------------------------------------------------------

    async def crear_cohorte(
        self,
        *,
        carrera_id: uuid.UUID,
        nombre: str,
        anio: int,
        vig_desde: date,
        vig_hasta: date | None = None,
        estado: str = "Activa",
    ) -> Cohorte:
        carrera = await self._carrera_repo.get(carrera_id)
        if carrera is None:
            raise NotFoundError("Carrera no encontrada.")
        if estado == "Activa" and carrera.estado == "Inactiva":
            raise BusinessRuleError("No se puede crear una cohorte activa en una carrera inactiva.")
        return await self._cohorte_repo.create(
            carrera_id=carrera_id,
            nombre=nombre,
            anio=anio,
            vig_desde=vig_desde,
            vig_hasta=vig_hasta,
            estado=estado,
        )

    async def listar_cohortes(self, *, carrera_id: uuid.UUID | None = None) -> list[Cohorte]:
        if carrera_id is not None:
            return await self._cohorte_repo.list_by_carrera(carrera_id)
        return await self._cohorte_repo.list()

    async def obtener_cohorte(self, cohorte_id: uuid.UUID) -> Cohorte:
        cohorte = await self._cohorte_repo.get(cohorte_id)
        if cohorte is None:
            raise NotFoundError("Cohorte no encontrada.")
        return cohorte

    async def actualizar_cohorte(self, cohorte_id: uuid.UUID, **fields: object) -> Cohorte:
        cohorte = await self._cohorte_repo.update(cohorte_id, **fields)
        if cohorte is None:
            raise NotFoundError("Cohorte no encontrada.")
        return cohorte

    async def eliminar_cohorte(self, cohorte_id: uuid.UUID) -> None:
        deleted = await self._cohorte_repo.soft_delete(cohorte_id)
        if not deleted:
            raise NotFoundError("Cohorte no encontrada.")

    # ------------------------------------------------------------------
    # Materia
    # ------------------------------------------------------------------

    async def crear_materia(self, *, codigo: str, nombre: str) -> Materia:
        existing = await self._materia_repo.get_by_codigo(codigo)
        if existing is not None:
            raise ConflictError(f"Materia con código '{codigo}' ya existe en este tenant.")
        return await self._materia_repo.create(codigo=codigo, nombre=nombre)

    async def listar_materias(self, *, estado: str | None = None) -> list[Materia]:
        if estado is not None:
            return await self._materia_repo.list_by_estado(estado)
        return await self._materia_repo.list()

    async def obtener_materia(self, materia_id: uuid.UUID) -> Materia:
        materia = await self._materia_repo.get(materia_id)
        if materia is None:
            raise NotFoundError("Materia no encontrada.")
        return materia

    async def actualizar_materia(self, materia_id: uuid.UUID, **fields: object) -> Materia:
        materia = await self._materia_repo.update(materia_id, **fields)
        if materia is None:
            raise NotFoundError("Materia no encontrada.")
        return materia

    async def eliminar_materia(self, materia_id: uuid.UUID) -> None:
        deleted = await self._materia_repo.soft_delete(materia_id)
        if not deleted:
            raise NotFoundError("Materia no encontrada.")
