from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AuthenticatedUser, get_db
from app.core.permissions import require_permission
from app.repositories.liquidaciones import SalarioBaseRepository, SalarioPlusRepository
from app.schemas.liquidaciones import (
    CrearSalarioBaseRequest,
    CrearSalarioPlusRequest,
    EditarSalarioBaseRequest,
    EditarSalarioPlusRequest,
    SalarioBaseResponse,
    SalarioPlusResponse,
)

router = APIRouter(prefix="/api/salarios", tags=["salarios"])

RequiereConfigurar = Annotated[AuthenticatedUser, require_permission("liquidaciones:configurar-salarios")]


# ── Base ──────────────────────────────────────────────────────────────────────

@router.post("/base", response_model=SalarioBaseResponse, status_code=201)
async def crear_salario_base(
    payload: CrearSalarioBaseRequest,
    user: RequiereConfigurar,
    db: AsyncSession = Depends(get_db),
) -> SalarioBaseResponse:
    repo = SalarioBaseRepository(session=db, tenant_id=user.tenant_id)
    obj = await repo.create(**payload.model_dump())
    await db.commit()
    return SalarioBaseResponse.model_validate(obj, from_attributes=True)


@router.get("/base", response_model=list[SalarioBaseResponse])
async def listar_salarios_base(
    user: RequiereConfigurar,
    db: AsyncSession = Depends(get_db),
    rol: str | None = None,
    periodo: str | None = None,
) -> list[SalarioBaseResponse]:
    repo = SalarioBaseRepository(session=db, tenant_id=user.tenant_id)
    items = await repo.listar(rol=rol, periodo=periodo)
    return [SalarioBaseResponse.model_validate(i, from_attributes=True) for i in items]


@router.patch("/base/{salario_id}", response_model=SalarioBaseResponse)
async def editar_salario_base(
    salario_id: uuid.UUID,
    payload: EditarSalarioBaseRequest,
    user: RequiereConfigurar,
    db: AsyncSession = Depends(get_db),
) -> SalarioBaseResponse:
    repo = SalarioBaseRepository(session=db, tenant_id=user.tenant_id)
    obj = await repo.update(salario_id, **payload.model_dump(exclude_unset=True))
    if obj is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Salario base no encontrado.")
    await db.commit()
    return SalarioBaseResponse.model_validate(obj, from_attributes=True)


@router.delete("/base/{salario_id}", status_code=204)
async def eliminar_salario_base(
    salario_id: uuid.UUID,
    user: RequiereConfigurar,
    db: AsyncSession = Depends(get_db),
) -> None:
    repo = SalarioBaseRepository(session=db, tenant_id=user.tenant_id)
    await repo.soft_delete(salario_id)
    await db.commit()


# ── Plus ──────────────────────────────────────────────────────────────────────

@router.post("/plus", response_model=SalarioPlusResponse, status_code=201)
async def crear_salario_plus(
    payload: CrearSalarioPlusRequest,
    user: RequiereConfigurar,
    db: AsyncSession = Depends(get_db),
) -> SalarioPlusResponse:
    repo = SalarioPlusRepository(session=db, tenant_id=user.tenant_id)
    obj = await repo.create(**payload.model_dump())
    await db.commit()
    return SalarioPlusResponse.model_validate(obj, from_attributes=True)


@router.get("/plus", response_model=list[SalarioPlusResponse])
async def listar_salarios_plus(
    user: RequiereConfigurar,
    db: AsyncSession = Depends(get_db),
    grupo: str | None = None,
    rol: str | None = None,
    periodo: str | None = None,
) -> list[SalarioPlusResponse]:
    repo = SalarioPlusRepository(session=db, tenant_id=user.tenant_id)
    items = await repo.listar(grupo=grupo, rol=rol, periodo=periodo)
    return [SalarioPlusResponse.model_validate(i, from_attributes=True) for i in items]


@router.patch("/plus/{plus_id}", response_model=SalarioPlusResponse)
async def editar_salario_plus(
    plus_id: uuid.UUID,
    payload: EditarSalarioPlusRequest,
    user: RequiereConfigurar,
    db: AsyncSession = Depends(get_db),
) -> SalarioPlusResponse:
    repo = SalarioPlusRepository(session=db, tenant_id=user.tenant_id)
    obj = await repo.update(plus_id, **payload.model_dump(exclude_unset=True))
    if obj is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Salario plus no encontrado.")
    await db.commit()
    return SalarioPlusResponse.model_validate(obj, from_attributes=True)


@router.delete("/plus/{plus_id}", status_code=204)
async def eliminar_salario_plus(
    plus_id: uuid.UUID,
    user: RequiereConfigurar,
    db: AsyncSession = Depends(get_db),
) -> None:
    repo = SalarioPlusRepository(session=db, tenant_id=user.tenant_id)
    await repo.soft_delete(plus_id)
    await db.commit()
