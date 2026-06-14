from __future__ import annotations

import hashlib
import hmac
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import uuid

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.core.dependencies import AuthenticatedUser
from app.core.security import create_access_token, hash_password
from app.models import AuthUser, Carrera, Cohorte, Materia, Permiso, Rol, RolPermiso, Tenant
from app.models.calificacion import Calificacion, FinalizacionActividad, UmbralMateria
from app.models.padron import EntradaPadron, VersionPadron
from app.models.usuarios import Asignacion, Usuario
from tests.usuarios_test_utils import clean_database, ensure_schema


def _hash_email(email: str) -> str:
    secret = get_settings().secret_key.encode("utf-8")
    return hmac.new(secret, email.strip().lower().encode("utf-8"), hashlib.sha256).hexdigest()


@pytest.fixture
async def analisis_app(valid_env):
    from app.api.v1.routers.analisis import router as analisis_router

    await ensure_schema()
    session_factory = get_session_factory()

    async with session_factory() as session:
        await clean_database(session)

        tenant_a = Tenant(name="Analisis A", slug=f"analisis-a-{uuid.uuid4()}")
        tenant_b = Tenant(name="Analisis B", slug=f"analisis-b-{uuid.uuid4()}")
        session.add_all([tenant_a, tenant_b])
        await session.flush()

        auth_prof = AuthUser(tenant_id=tenant_a.id, email="prof@analisis.local", password_hash=hash_password("P1!"), roles=["PROFESOR"])
        auth_tutor = AuthUser(tenant_id=tenant_a.id, email="tutor@analisis.local", password_hash=hash_password("P1!"), roles=["TUTOR"])
        auth_coord = AuthUser(tenant_id=tenant_a.id, email="coord@analisis.local", password_hash=hash_password("P1!"), roles=["COORDINADOR"])
        auth_admin = AuthUser(tenant_id=tenant_a.id, email="admin@analisis.local", password_hash=hash_password("P1!"), roles=["ADMIN"])
        auth_plain = AuthUser(tenant_id=tenant_a.id, email="plain@analisis.local", password_hash=hash_password("P1!"), roles=["ALUMNO"])
        auth_unassigned = AuthUser(tenant_id=tenant_a.id, email="unassigned@analisis.local", password_hash=hash_password("P1!"), roles=["PROFESOR"])
        auth_b = AuthUser(tenant_id=tenant_b.id, email="prof@tenantb.local", password_hash=hash_password("P1!"), roles=["PROFESOR"])
        session.add_all([auth_prof, auth_tutor, auth_coord, auth_admin, auth_plain, auth_unassigned, auth_b])
        await session.flush()

        roles_a = {
            name: Rol(tenant_id=tenant_a.id, nombre=name)
            for name in ["PROFESOR", "TUTOR", "COORDINADOR", "ADMIN", "ALUMNO"]
        }
        role_b = Rol(tenant_id=tenant_b.id, nombre="PROFESOR")
        session.add_all([*roles_a.values(), role_b])
        await session.flush()

        permiso_a = Permiso(tenant_id=tenant_a.id, nombre="atrasados:ver")
        permiso_b = Permiso(tenant_id=tenant_b.id, nombre="atrasados:ver")
        session.add_all([permiso_a, permiso_b])
        await session.flush()

        session.add_all([
            RolPermiso(tenant_id=tenant_a.id, rol_id=roles_a["PROFESOR"].id, permiso_id=permiso_a.id),
            RolPermiso(tenant_id=tenant_a.id, rol_id=roles_a["TUTOR"].id, permiso_id=permiso_a.id),
            RolPermiso(tenant_id=tenant_a.id, rol_id=roles_a["COORDINADOR"].id, permiso_id=permiso_a.id),
            RolPermiso(tenant_id=tenant_a.id, rol_id=roles_a["ADMIN"].id, permiso_id=permiso_a.id),
            RolPermiso(tenant_id=tenant_b.id, rol_id=role_b.id, permiso_id=permiso_b.id),
        ])

        carrera_a = Carrera(tenant_id=tenant_a.id, codigo="CAR-A", nombre="Carrera A")
        carrera_b = Carrera(tenant_id=tenant_b.id, codigo="CAR-B", nombre="Carrera B")
        session.add_all([carrera_a, carrera_b])
        await session.flush()

        cohorte_a = Cohorte(tenant_id=tenant_a.id, carrera_id=carrera_a.id, nombre="2026-A", anio=2026, vig_desde=date(2026, 1, 1))
        cohorte_b = Cohorte(tenant_id=tenant_b.id, carrera_id=carrera_b.id, nombre="2026-B", anio=2026, vig_desde=date(2026, 1, 1))
        materia_a = Materia(tenant_id=tenant_a.id, codigo="MAT-A", nombre="Materia A")
        materia_b = Materia(tenant_id=tenant_b.id, codigo="MAT-B", nombre="Materia B")
        session.add_all([cohorte_a, cohorte_b, materia_a, materia_b])
        await session.flush()

        usuario_prof = Usuario(tenant_id=tenant_a.id, auth_user_id=auth_prof.id, nombre="Profe", apellidos="A", email_encrypted="enc-prof", email_hash=_hash_email("prof@analisis.local"))
        usuario_tutor = Usuario(tenant_id=tenant_a.id, auth_user_id=auth_tutor.id, nombre="Tutor", apellidos="A", email_encrypted="enc-tutor", email_hash=_hash_email("tutor@analisis.local"))
        usuario_coord = Usuario(tenant_id=tenant_a.id, auth_user_id=auth_coord.id, nombre="Coord", apellidos="A", email_encrypted="enc-coord", email_hash=_hash_email("coord@analisis.local"))
        usuario_admin = Usuario(tenant_id=tenant_a.id, auth_user_id=auth_admin.id, nombre="Admin", apellidos="A", email_encrypted="enc-admin", email_hash=_hash_email("admin@analisis.local"))
        usuario_unassigned = Usuario(tenant_id=tenant_a.id, auth_user_id=auth_unassigned.id, nombre="Sin", apellidos="Asignacion", email_encrypted="enc-unassigned", email_hash=_hash_email("unassigned@analisis.local"))
        usuario_b = Usuario(tenant_id=tenant_b.id, auth_user_id=auth_b.id, nombre="Profe", apellidos="B", email_encrypted="enc-b", email_hash=_hash_email("prof@tenantb.local"))
        usuario_ana = Usuario(tenant_id=tenant_a.id, nombre="Ana", apellidos="Atria", email_encrypted="enc-st-ana", email_hash=_hash_email("ana@student.local"))
        usuario_caro = Usuario(tenant_id=tenant_a.id, nombre="Caro", apellidos="Campos", email_encrypted="enc-st-caro", email_hash=_hash_email("caro@student.local"))
        session.add_all([usuario_prof, usuario_tutor, usuario_coord, usuario_admin, usuario_unassigned, usuario_b, usuario_ana, usuario_caro])
        await session.flush()

        asignacion_prof = Asignacion(
            tenant_id=tenant_a.id,
            usuario_id=usuario_prof.id,
            rol_id=roles_a["PROFESOR"].id,
            materia_id=materia_a.id,
            carrera_id=carrera_a.id,
            cohorte_id=cohorte_a.id,
            comisiones=["A"],
            desde=date.today() - timedelta(days=30),
            hasta=date.today() + timedelta(days=30),
        )
        asignacion_tutor = Asignacion(
            tenant_id=tenant_a.id,
            usuario_id=usuario_tutor.id,
            rol_id=roles_a["TUTOR"].id,
            materia_id=materia_a.id,
            carrera_id=carrera_a.id,
            cohorte_id=cohorte_a.id,
            comisiones=["A"],
            desde=date.today() - timedelta(days=30),
            hasta=date.today() + timedelta(days=30),
        )
        asignacion_coord = Asignacion(
            tenant_id=tenant_a.id,
            usuario_id=usuario_coord.id,
            rol_id=roles_a["COORDINADOR"].id,
            desde=date.today() - timedelta(days=30),
            hasta=date.today() + timedelta(days=30),
        )
        asignacion_b = Asignacion(
            tenant_id=tenant_b.id,
            usuario_id=usuario_b.id,
            rol_id=role_b.id,
            materia_id=materia_b.id,
            carrera_id=carrera_b.id,
            cohorte_id=cohorte_b.id,
            comisiones=["B"],
            desde=date.today() - timedelta(days=30),
            hasta=date.today() + timedelta(days=30),
        )
        session.add_all([asignacion_prof, asignacion_tutor, asignacion_coord, asignacion_b])
        await session.flush()

        version_a = VersionPadron(tenant_id=tenant_a.id, materia_id=materia_a.id, cohorte_id=cohorte_a.id, cargado_por=usuario_prof.id, activa=True)
        version_b = VersionPadron(tenant_id=tenant_b.id, materia_id=materia_b.id, cohorte_id=cohorte_b.id, cargado_por=usuario_b.id, activa=True)
        session.add_all([version_a, version_b])
        await session.flush()

        entrada_ana = EntradaPadron(tenant_id=tenant_a.id, version_id=version_a.id, usuario_id=usuario_ana.id, nombre="Ana", apellidos="Atria", email_encrypted="enc-ana", email_hash=_hash_email("ana@student.local"), comision="A", regional="Norte")
        entrada_beto = EntradaPadron(tenant_id=tenant_a.id, version_id=version_a.id, usuario_id=None, nombre="Beto", apellidos="Bustos", email_encrypted="enc-beto", email_hash=_hash_email("beto@student.local"), comision="A", regional="Norte")
        entrada_caro = EntradaPadron(tenant_id=tenant_a.id, version_id=version_a.id, usuario_id=usuario_caro.id, nombre="Caro", apellidos="Campos", email_encrypted="enc-caro", email_hash=_hash_email("caro@student.local"), comision="B", regional="Sur")
        entrada_dani = EntradaPadron(tenant_id=tenant_a.id, version_id=version_a.id, usuario_id=None, nombre="Dani", apellidos="Diaz", email_encrypted="enc-dani", email_hash=_hash_email("dani@student.local"), comision="A", regional="Norte")
        entrada_b = EntradaPadron(tenant_id=tenant_b.id, version_id=version_b.id, usuario_id=None, nombre="Otro", apellidos="Tenant", email_encrypted="enc-otro", email_hash=_hash_email("otro@student.local"), comision="B", regional="Oeste")
        session.add_all([entrada_ana, entrada_beto, entrada_caro, entrada_dani, entrada_b])
        await session.flush()

        session.add(UmbralMateria(
            tenant_id=tenant_a.id,
            asignacion_id=asignacion_prof.id,
            materia_id=materia_a.id,
            umbral_pct=Decimal("60"),
            valores_aprobatorios=["Satisfactorio", "Supera lo esperado"],
        ))

        now = datetime.now(timezone.utc)
        calificaciones = [
            Calificacion(tenant_id=tenant_a.id, entrada_padron_id=entrada_ana.id, actor_id=usuario_prof.id, actividad="TP 1 (Real)", nota_numerica=Decimal("50"), nota_textual=None, aprobado=False, origen="Importado", created_at=now - timedelta(days=10), updated_at=now - timedelta(days=10)),
            Calificacion(tenant_id=tenant_a.id, entrada_padron_id=entrada_ana.id, actor_id=usuario_prof.id, actividad="TP 2 (Real)", nota_numerica=Decimal("80"), nota_textual=None, aprobado=True, origen="Importado", created_at=now - timedelta(days=9), updated_at=now - timedelta(days=9)),
            Calificacion(tenant_id=tenant_a.id, entrada_padron_id=entrada_ana.id, actor_id=usuario_prof.id, actividad="Trabajo Final", nota_numerica=None, nota_textual="Satisfactorio", aprobado=True, origen="Importado", created_at=now - timedelta(days=8), updated_at=now - timedelta(days=8)),
            Calificacion(tenant_id=tenant_a.id, entrada_padron_id=entrada_beto.id, actor_id=usuario_prof.id, actividad="TP 1 (Real)", nota_numerica=Decimal("90"), nota_textual=None, aprobado=True, origen="Importado", created_at=now - timedelta(days=7), updated_at=now - timedelta(days=7)),
            Calificacion(tenant_id=tenant_a.id, entrada_padron_id=entrada_caro.id, actor_id=usuario_prof.id, actividad="TP 1 (Real)", nota_numerica=Decimal("70"), nota_textual=None, aprobado=True, origen="Importado", created_at=now - timedelta(days=6), updated_at=now - timedelta(days=6)),
            Calificacion(tenant_id=tenant_a.id, entrada_padron_id=entrada_caro.id, actor_id=usuario_prof.id, actividad="TP 2 (Real)", nota_numerica=Decimal("75"), nota_textual=None, aprobado=True, origen="Importado", created_at=now - timedelta(days=5), updated_at=now - timedelta(days=5)),
            Calificacion(tenant_id=tenant_a.id, entrada_padron_id=entrada_caro.id, actor_id=usuario_prof.id, actividad="Trabajo Final", nota_numerica=None, nota_textual="No satisfactorio", aprobado=False, origen="Importado", created_at=now - timedelta(days=4), updated_at=now - timedelta(days=4)),
            Calificacion(tenant_id=tenant_b.id, entrada_padron_id=entrada_b.id, actor_id=usuario_b.id, actividad="TP 1 (Real)", nota_numerica=Decimal("20"), nota_textual=None, aprobado=False, origen="Importado", created_at=now - timedelta(days=3), updated_at=now - timedelta(days=3)),
        ]
        finalizaciones = [
            FinalizacionActividad(
                tenant_id=tenant_a.id,
                entrada_padron_id=entrada_ana.id,
                actividad="Trabajo Final",
                es_textual=True,
                finalizado=True,
                created_at=now - timedelta(days=8),
                updated_at=now - timedelta(days=8),
            ),
            FinalizacionActividad(
                tenant_id=tenant_a.id,
                entrada_padron_id=entrada_beto.id,
                actividad="Trabajo Final",
                es_textual=True,
                finalizado=True,
                created_at=now - timedelta(days=7),
                updated_at=now - timedelta(days=7),
            ),
            FinalizacionActividad(
                tenant_id=tenant_a.id,
                entrada_padron_id=entrada_dani.id,
                actividad="Trabajo Final",
                es_textual=True,
                finalizado=False,
                created_at=now - timedelta(days=6),
                updated_at=now - timedelta(days=6),
            ),
            FinalizacionActividad(
                tenant_id=tenant_a.id,
                entrada_padron_id=entrada_dani.id,
                actividad="TP 2 (Real)",
                es_textual=False,
                finalizado=True,
                created_at=now - timedelta(days=5),
                updated_at=now - timedelta(days=5),
            ),
        ]
        session.add_all([*calificaciones, *finalizaciones])
        await session.commit()

        app = FastAPI()
        app.include_router(analisis_router)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            yield {
                "client": client,
                "session": session,
                "tenant_a_id": tenant_a.id,
                "tenant_b_id": tenant_b.id,
                "materia_a_id": materia_a.id,
                "cohorte_a_id": cohorte_a.id,
                "usuario_prof_id": usuario_prof.id,
                "usuario_coord_id": usuario_coord.id,
                "asignacion_prof_id": asignacion_prof.id,
                "version_a_id": version_a.id,
                "entrada_ana_id": entrada_ana.id,
                "entrada_beto_id": entrada_beto.id,
                "entrada_caro_id": entrada_caro.id,
                "entrada_dani_id": entrada_dani.id,
                "prof_user": AuthenticatedUser(user_id=auth_prof.id, tenant_id=tenant_a.id, roles=["PROFESOR"]),
                "coord_user": AuthenticatedUser(user_id=auth_coord.id, tenant_id=tenant_a.id, roles=["COORDINADOR"]),
                "unassigned_user": AuthenticatedUser(user_id=auth_unassigned.id, tenant_id=tenant_a.id, roles=["PROFESOR"]),
                "missing_profile_user": AuthenticatedUser(user_id=uuid.uuid4(), tenant_id=tenant_a.id, roles=["PROFESOR"]),
                "token_prof": create_access_token(user_id=str(auth_prof.id), tenant_id=str(tenant_a.id), roles=["PROFESOR"]),
                "token_tutor": create_access_token(user_id=str(auth_tutor.id), tenant_id=str(tenant_a.id), roles=["TUTOR"]),
                "token_coord": create_access_token(user_id=str(auth_coord.id), tenant_id=str(tenant_a.id), roles=["COORDINADOR"]),
                "token_admin": create_access_token(user_id=str(auth_admin.id), tenant_id=str(tenant_a.id), roles=["ADMIN"]),
                "token_plain": create_access_token(user_id=str(auth_plain.id), tenant_id=str(tenant_a.id), roles=["ALUMNO"]),
                "token_unassigned": create_access_token(user_id=str(auth_unassigned.id), tenant_id=str(tenant_a.id), roles=["PROFESOR"]),
                "token_b": create_access_token(user_id=str(auth_b.id), tenant_id=str(tenant_b.id), roles=["PROFESOR"]),
            }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "token"),
    [
        ("/api/analisis/atrasados", None),
        ("/api/analisis/ranking-aprobadas", None),
        ("/api/analisis/materia/resumen", None),
        ("/api/analisis/notas-finales", None),
        ("/api/analisis/monitor", None),
        ("/api/analisis/tps-sin-corregir/export", None),
    ],
)
async def test_analisis_endpoints_require_authentication(analisis_app, path, token):
    response = await analisis_app["client"].get(path)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_analisis_endpoints_require_permission_fail_closed(analisis_app):
    response = await analisis_app["client"].get(
        "/api/analisis/atrasados",
        headers={"Authorization": f"Bearer {analisis_app['token_plain']}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_monitor_forbids_extra_query_params(analisis_app):
    response = await analisis_app["client"].get(
        "/api/analisis/monitor?unexpected=value",
        headers={"Authorization": f"Bearer {analisis_app['token_coord']}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_repository_filters_tenant_and_assignment_scope(analisis_app):
    from app.analisis.repositories import AnalisisQueryFilters, AnalisisRepository, AuthorizedScope, AuthorizedScopeAssignment

    repo = AnalisisRepository(session=analisis_app["session"], tenant_id=analisis_app["tenant_a_id"])
    scope = AuthorizedScope(
        is_global=False,
        assignments=[
            AuthorizedScopeAssignment(
                materia_id=analisis_app["materia_a_id"],
                cohorte_id=analisis_app["cohorte_a_id"],
                comisiones=("A",),
            )
        ],
    )

    entries = await repo.list_active_padron_entries(AnalisisQueryFilters(), scope)
    latest = await repo.list_latest_calificaciones(AnalisisQueryFilters(), scope)

    assert {row.nombre for row in entries} == {"Ana", "Beto", "Dani"}
    assert all(row.comision == "A" for row in entries)
    assert {row.actividad for row in latest} == {"TP 1 (Real)", "TP 2 (Real)", "Trabajo Final"}
    assert all(row.tenant_id == analisis_app["tenant_a_id"] for row in latest)


@pytest.mark.asyncio
async def test_repository_fail_closes_when_scope_has_no_assignments(analisis_app):
    from app.analisis.repositories import AnalisisQueryFilters, AnalisisRepository, AuthorizedScope

    repo = AnalisisRepository(session=analisis_app["session"], tenant_id=analisis_app["tenant_a_id"])
    scope = AuthorizedScope(is_global=False, assignments=())

    entries = await repo.list_active_padron_entries(AnalisisQueryFilters(), scope)
    activities = await repo.list_actividades_analizadas(AnalisisQueryFilters(), scope)
    latest = await repo.list_latest_calificaciones(AnalisisQueryFilters(), scope)
    umbrales = await repo.list_umbral_vigente(AnalisisQueryFilters(), scope)

    assert entries == []
    assert activities == []
    assert latest == []
    assert umbrales == []


@pytest.mark.asyncio
async def test_repository_lists_umbral_vigente_for_actor_materia(analisis_app):
    from app.analisis.repositories import AnalisisQueryFilters, AnalisisRepository, AuthorizedScope

    repo = AnalisisRepository(session=analisis_app["session"], tenant_id=analisis_app["tenant_a_id"])
    umbrales = await repo.list_umbral_vigente(AnalisisQueryFilters(materia_id=analisis_app["materia_a_id"]), AuthorizedScope(is_global=True))

    assert len(umbrales) == 1
    assert umbrales[0].umbral_pct == Decimal("60")
    assert umbrales[0].actor_id == analisis_app["usuario_prof_id"]


@pytest.mark.asyncio
async def test_service_detects_atrasados_for_missing_activity_and_threshold(analisis_app):
    from app.analisis.services import AnalisisService

    service = AnalisisService(session=analisis_app["session"], tenant_id=analisis_app["tenant_a_id"])
    result = await service.list_atrasados(analisis_app["prof_user"], materia_id=analisis_app["materia_a_id"])

    ids = {item.entrada_padron_id for item in result.items}
    assert analisis_app["entrada_ana_id"] in ids
    assert analisis_app["entrada_beto_id"] in ids
    assert analisis_app["entrada_dani_id"] in ids
    assert analisis_app["entrada_caro_id"] not in ids

    ana = next(item for item in result.items if item.entrada_padron_id == analisis_app["entrada_ana_id"])
    beto = next(item for item in result.items if item.entrada_padron_id == analisis_app["entrada_beto_id"])
    dani = next(item for item in result.items if item.entrada_padron_id == analisis_app["entrada_dani_id"])

    assert {m.tipo for m in ana.motivos} == {"nota_bajo_umbral"}
    assert {m.tipo for m in beto.motivos} == {"actividad_faltante"}
    assert {m.tipo for m in dani.motivos} == {"actividad_faltante"}


@pytest.mark.asyncio
async def test_service_ranking_excludes_students_without_approved_activities(analisis_app):
    from app.analisis.services import AnalisisService

    service = AnalisisService(session=analisis_app["session"], tenant_id=analisis_app["tenant_a_id"])
    result = await service.list_ranking(analisis_app["coord_user"], materia_id=analisis_app["materia_a_id"])

    assert [item.nombre for item in result.items] == ["Ana", "Caro", "Beto"]
    assert all(item.aprobadas_count >= 1 for item in result.items)
    assert all(item.entrada_padron_id != analisis_app["entrada_dani_id"] for item in result.items)


@pytest.mark.asyncio
async def test_service_notas_finales_and_summary_handle_edge_cases(analisis_app):
    from app.analisis.services import AnalisisService

    service = AnalisisService(session=analisis_app["session"], tenant_id=analisis_app["tenant_a_id"])

    notas = await service.list_notas_finales(analisis_app["coord_user"], materia_id=analisis_app["materia_a_id"])
    summary = await service.get_materia_resumen(analisis_app["coord_user"], materia_id=analisis_app["materia_a_id"])

    ana = next(item for item in notas.items if item.entrada_padron_id == analisis_app["entrada_ana_id"])
    dani = next(item for item in notas.items if item.entrada_padron_id == analisis_app["entrada_dani_id"])

    assert ana.nota_final == Decimal("65")
    assert dani.nota_final is None
    assert dani.tiene_nota_final is False
    assert summary.alumnos_activos == 4
    assert summary.actividades_analizadas == 3
    assert summary.alumnos_atrasados == 4


@pytest.mark.asyncio
async def test_service_summary_reports_sin_datos_and_sin_actividades(analisis_app):
    from app.analisis.services import AnalisisService

    service = AnalisisService(session=analisis_app["session"], tenant_id=analisis_app["tenant_a_id"])

    resumen_sin_datos = await service.get_materia_resumen(analisis_app["coord_user"], materia_id=uuid.uuid4())
    await analisis_app["session"].execute(
        delete(Calificacion).where(Calificacion.tenant_id == analisis_app["tenant_a_id"]).where(Calificacion.deleted_at.is_(None))
    )
    await analisis_app["session"].commit()
    resumen_sin_actividades = await service.get_materia_resumen(analisis_app["coord_user"], materia_id=analisis_app["materia_a_id"])

    assert resumen_sin_datos.estado == "sin_datos"
    assert resumen_sin_actividades.estado == "sin_actividades"


@pytest.mark.asyncio
async def test_service_monitor_filters_and_export_requires_finalized_textual_signal(analisis_app):
    from app.analisis.services import AnalisisService

    service = AnalisisService(session=analisis_app["session"], tenant_id=analisis_app["tenant_a_id"])

    monitor = await service.list_monitor(
        analisis_app["coord_user"],
        materia_id=analisis_app["materia_a_id"],
        comision="A",
        regional="Norte",
        search="be",
        fecha_desde=date.today() - timedelta(days=20),
        fecha_hasta=date.today() - timedelta(days=1),
    )
    export_result = await service.export_tps_sin_corregir(analisis_app["coord_user"], materia_id=analisis_app["materia_a_id"])

    assert [item.nombre for item in monitor.items] == ["Beto"]
    csv_text = export_result.content.decode("utf-8")
    assert "Trabajo Final" in csv_text
    assert "TP 1 (Real)" not in csv_text
    assert "TP 2 (Real)" not in csv_text
    assert "Ana" not in csv_text
    assert "Beto" in csv_text
    assert "Dani" not in csv_text


@pytest.mark.asyncio
async def test_service_monitor_limits_profesor_to_authorized_scope(analisis_app):
    from app.analisis.services import AnalisisService

    service = AnalisisService(session=analisis_app["session"], tenant_id=analisis_app["tenant_a_id"])

    monitor = await service.list_monitor(analisis_app["prof_user"], materia_id=analisis_app["materia_a_id"])
    monitor_comision_b = await service.list_monitor(
        analisis_app["prof_user"],
        materia_id=analisis_app["materia_a_id"],
        comision="B",
    )

    assert {item.nombre for item in monitor.items} == {"Ana", "Beto", "Dani"}
    assert all(item.comision == "A" for item in monitor.items)
    assert monitor_comision_b.items == []


@pytest.mark.asyncio
async def test_service_fail_closes_without_active_assignments_or_profile(analisis_app):
    from app.analisis.services import AnalisisService

    service = AnalisisService(session=analisis_app["session"], tenant_id=analisis_app["tenant_a_id"])

    unassigned = await service.list_monitor(analisis_app["unassigned_user"], materia_id=analisis_app["materia_a_id"])
    missing_profile = await service.list_atrasados(analisis_app["missing_profile_user"], materia_id=analisis_app["materia_a_id"])

    assert unassigned.items == []
    assert unassigned.pagination.total_items == 0
    assert missing_profile.items == []
    assert missing_profile.total_items == 0


@pytest.mark.asyncio
async def test_export_endpoint_requires_permission_fail_closed(analisis_app):
    response = await analisis_app["client"].get(
        "/api/analisis/tps-sin-corregir/export",
        headers={"Authorization": f"Bearer {analisis_app['token_plain']}"},
    )

    assert response.status_code == 403
