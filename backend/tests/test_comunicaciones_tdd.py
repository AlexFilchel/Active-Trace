from __future__ import annotations

import hashlib
import hmac
from datetime import date, datetime, timedelta, timezone
import logging
import uuid

import pytest
from fastapi import FastAPI, HTTPException, Response
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.core.security import create_access_token, decrypt_value, encrypt_value, hash_password
from app.models import AuditLog, AuthUser, Carrera, Cohorte, EntradaPadron, Materia, Permiso, Rol, RolPermiso, Tenant, Usuario, VersionPadron
from tests.usuarios_test_utils import clean_database, ensure_schema


def _hash_email(email: str) -> str:
    secret = get_settings().secret_key.encode("utf-8")
    return hmac.new(secret, email.strip().lower().encode("utf-8"), hashlib.sha256).hexdigest()


@pytest.fixture
async def comunicaciones_app(valid_env):
    from app.api.v1.routers.comunicaciones import router as comunicaciones_router

    await ensure_schema()
    session_factory = get_session_factory()

    async with session_factory() as session:
        await clean_database(session)

        tenant_a = Tenant(
            name="Com Tenant A",
            slug=f"com-a-{uuid.uuid4()}",
            comunicaciones_aprobacion_requerida=False,
            comunicaciones_aprobacion_masiva=True,
        )
        tenant_b = Tenant(
            name="Com Tenant B",
            slug=f"com-b-{uuid.uuid4()}",
            comunicaciones_aprobacion_requerida=False,
            comunicaciones_aprobacion_masiva=False,
        )
        session.add_all([tenant_a, tenant_b])
        await session.flush()

        auth_sender = AuthUser(tenant_id=tenant_a.id, email="sender@tenant-a.local", password_hash=hash_password("P1!"), roles=["PROFESOR"])
        auth_approver = AuthUser(tenant_id=tenant_a.id, email="approver@tenant-a.local", password_hash=hash_password("P1!"), roles=["COORDINADOR"])
        auth_no_approve = AuthUser(tenant_id=tenant_a.id, email="viewer@tenant-a.local", password_hash=hash_password("P1!"), roles=["PROFESOR"])
        auth_forbidden = AuthUser(tenant_id=tenant_a.id, email="forbidden@tenant-a.local", password_hash=hash_password("P1!"), roles=["ALUMNO"])
        auth_b = AuthUser(tenant_id=tenant_b.id, email="sender@tenant-b.local", password_hash=hash_password("P1!"), roles=["PROFESOR"])
        session.add_all([auth_sender, auth_approver, auth_no_approve, auth_forbidden, auth_b])
        await session.flush()

        role_sender = Rol(tenant_id=tenant_a.id, nombre="PROFESOR")
        role_approver = Rol(tenant_id=tenant_a.id, nombre="COORDINADOR")
        role_forbidden = Rol(tenant_id=tenant_a.id, nombre="ALUMNO")
        role_sender_b = Rol(tenant_id=tenant_b.id, nombre="PROFESOR")
        session.add_all([role_sender, role_approver, role_forbidden, role_sender_b])
        await session.flush()

        permiso_enviar_a = Permiso(tenant_id=tenant_a.id, nombre="comunicacion:enviar")
        permiso_aprobar_a = Permiso(tenant_id=tenant_a.id, nombre="comunicacion:aprobar")
        permiso_enviar_b = Permiso(tenant_id=tenant_b.id, nombre="comunicacion:enviar")
        session.add_all([permiso_enviar_a, permiso_aprobar_a, permiso_enviar_b])
        await session.flush()

        session.add_all([
            RolPermiso(tenant_id=tenant_a.id, rol_id=role_sender.id, permiso_id=permiso_enviar_a.id),
            RolPermiso(tenant_id=tenant_a.id, rol_id=role_approver.id, permiso_id=permiso_enviar_a.id),
            RolPermiso(tenant_id=tenant_a.id, rol_id=role_approver.id, permiso_id=permiso_aprobar_a.id),
            RolPermiso(tenant_id=tenant_b.id, rol_id=role_sender_b.id, permiso_id=permiso_enviar_b.id),
        ])

        carrera_a = Carrera(tenant_id=tenant_a.id, codigo="CAR-COM-A", nombre="Carrera Com A")
        carrera_b = Carrera(tenant_id=tenant_b.id, codigo="CAR-COM-B", nombre="Carrera Com B")
        session.add_all([carrera_a, carrera_b])
        await session.flush()

        cohorte_a = Cohorte(tenant_id=tenant_a.id, carrera_id=carrera_a.id, nombre="2026", anio=2026, vig_desde=date(2026, 1, 1))
        materia_a = Materia(tenant_id=tenant_a.id, codigo="MAT-COM-A", nombre="Materia Com A")
        cohorte_b = Cohorte(tenant_id=tenant_b.id, carrera_id=carrera_b.id, nombre="2026", anio=2026, vig_desde=date(2026, 1, 1))
        materia_b = Materia(tenant_id=tenant_b.id, codigo="MAT-COM-B", nombre="Materia Com B")
        session.add_all([cohorte_a, materia_a, cohorte_b, materia_b])
        await session.flush()

        usuario_sender = Usuario(tenant_id=tenant_a.id, auth_user_id=auth_sender.id, nombre="Sender", apellidos="A", email_encrypted=encrypt_value("sender@tenant-a.local"), email_hash=_hash_email("sender@tenant-a.local"))
        usuario_approver = Usuario(tenant_id=tenant_a.id, auth_user_id=auth_approver.id, nombre="Approver", apellidos="A", email_encrypted=encrypt_value("approver@tenant-a.local"), email_hash=_hash_email("approver@tenant-a.local"))
        usuario_b = Usuario(tenant_id=tenant_b.id, auth_user_id=auth_b.id, nombre="Sender", apellidos="B", email_encrypted=encrypt_value("sender@tenant-b.local"), email_hash=_hash_email("sender@tenant-b.local"))
        session.add_all([usuario_sender, usuario_approver, usuario_b])
        await session.flush()

        version_a = VersionPadron(tenant_id=tenant_a.id, materia_id=materia_a.id, cohorte_id=cohorte_a.id, cargado_por=usuario_sender.id, activa=True)
        version_b = VersionPadron(tenant_id=tenant_b.id, materia_id=materia_b.id, cohorte_id=cohorte_b.id, cargado_por=usuario_b.id, activa=True)
        session.add_all([version_a, version_b])
        await session.flush()

        entrada_a1 = EntradaPadron(tenant_id=tenant_a.id, version_id=version_a.id, nombre="Ana", apellidos="Atria", email_encrypted=encrypt_value("ana@tenant-a.local"), email_hash=_hash_email("ana@tenant-a.local"), comision="A", regional="Norte")
        entrada_a2 = EntradaPadron(tenant_id=tenant_a.id, version_id=version_a.id, nombre="Beto", apellidos="Bustos", email_encrypted=encrypt_value("beto@tenant-a.local"), email_hash=_hash_email("beto@tenant-a.local"), comision="A", regional="Norte")
        entrada_b1 = EntradaPadron(tenant_id=tenant_b.id, version_id=version_b.id, nombre="Bruna", apellidos="B", email_encrypted=encrypt_value("bruna@tenant-b.local"), email_hash=_hash_email("bruna@tenant-b.local"), comision="B", regional="Sur")
        session.add_all([entrada_a1, entrada_a2, entrada_b1])
        await session.commit()

        sender_token = create_access_token(user_id=str(auth_sender.id), tenant_id=str(tenant_a.id), roles=["PROFESOR"])
        approver_token = create_access_token(user_id=str(auth_approver.id), tenant_id=str(tenant_a.id), roles=["COORDINADOR"])
        no_approve_token = create_access_token(user_id=str(auth_no_approve.id), tenant_id=str(tenant_a.id), roles=["PROFESOR"])
        forbidden_token = create_access_token(user_id=str(auth_forbidden.id), tenant_id=str(tenant_a.id), roles=["ALUMNO"])
        tenant_b_token = create_access_token(user_id=str(auth_b.id), tenant_id=str(tenant_b.id), roles=["PROFESOR"])

        app = FastAPI()
        app.include_router(comunicaciones_router)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            yield {
                "client": client,
                "session": session,
                "tenant_a_id": tenant_a.id,
                "tenant_b_id": tenant_b.id,
                "materia_a_id": materia_a.id,
                "sender_token": sender_token,
                "approver_token": approver_token,
                "no_approve_token": no_approve_token,
                "forbidden_token": forbidden_token,
                "tenant_b_token": tenant_b_token,
                "sender_auth_user_id": auth_sender.id,
                "approver_auth_user_id": auth_approver.id,
                "entrada_a1_id": entrada_a1.id,
                "entrada_a2_id": entrada_a2.id,
                "entrada_b1_id": entrada_b1.id,
            }


async def _preview(ctx: dict, *, destinatarios: list[uuid.UUID] | None = None):
    destinatarios = destinatarios or [ctx["entrada_a1_id"], ctx["entrada_a2_id"]]
    response = await ctx["client"].post(
        "/api/comunicaciones/preview",
        json={
            "materia_id": str(ctx["materia_a_id"]),
            "destinatarios": [str(destinatario) for destinatario in destinatarios],
            "asunto_template": "Aviso para {{nombre}}",
            "cuerpo_template": "Hola {{nombre}}, materia {{materia}}",
        },
        headers={"Authorization": f"Bearer {ctx['sender_token']}"},
    )
    return response


@pytest.mark.asyncio
async def test_preview_autorizado_profesor_retorna_200(comunicaciones_app):
    ctx = comunicaciones_app

    response = await _preview(ctx, destinatarios=[ctx["entrada_a1_id"]])

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_service_preview_resuelve_materia_fixture_valida(comunicaciones_app):
    ctx = comunicaciones_app
    from app.core.dependencies import AuthenticatedUser
    from app.services.comunicaciones import ComunicacionService

    service = ComunicacionService(session=ctx["session"], tenant_id=ctx["tenant_a_id"])
    payload = await service.preview(
        user=AuthenticatedUser(
            user_id=ctx["sender_auth_user_id"],
            tenant_id=ctx["tenant_a_id"],
            roles=["PROFESOR"],
        ),
        materia_id=ctx["materia_a_id"],
        destinatarios=[ctx["entrada_a1_id"]],
        asunto_template="Aviso para {{nombre}}",
        cuerpo_template="Hola {{nombre}}, materia {{materia}}",
    )

    assert payload["items"][0]["asunto"] == "Aviso para Ana"
    assert "Materia Com A" in payload["items"][0]["cuerpo"]


@pytest.mark.asyncio
async def test_preview_personaliza_y_enqueue_exige_preview(comunicaciones_app):
    ctx = comunicaciones_app

    preview_response = await _preview(ctx, destinatarios=[ctx["entrada_a1_id"]])
    assert preview_response.status_code == 200
    preview_payload = preview_response.json()
    assert preview_payload["items"][0]["asunto"] == "Aviso para Ana"
    assert "Materia Com A" in preview_payload["items"][0]["cuerpo"]
    assert preview_payload["preview_token"]

    enqueue_without_preview = await ctx["client"].post(
        "/api/comunicaciones/enqueue",
        json={
            "materia_id": str(ctx["materia_a_id"]),
            "destinatarios": [str(ctx["entrada_a1_id"])],
            "asunto_template": "Aviso para {{nombre}}",
            "cuerpo_template": "Hola {{nombre}}, materia {{materia}}",
            "idempotency_key": "idem-no-preview",
            "preview_token": "preview-invalido",
        },
        headers={"Authorization": f"Bearer {ctx['sender_token']}"},
    )
    assert enqueue_without_preview.status_code == 422


@pytest.mark.asyncio
async def test_enqueue_masivo_crea_lote_e_idempotencia(comunicaciones_app):
    ctx = comunicaciones_app
    preview_response = await _preview(ctx)
    preview_token = preview_response.json()["preview_token"]

    payload = {
        "materia_id": str(ctx["materia_a_id"]),
        "destinatarios": [str(ctx["entrada_a1_id"]), str(ctx["entrada_a2_id"])],
        "asunto_template": "Aviso para {{nombre}}",
        "cuerpo_template": "Hola {{nombre}}, materia {{materia}}",
        "idempotency_key": "idem-lote-1",
        "preview_token": preview_token,
    }
    first = await ctx["client"].post(
        "/api/comunicaciones/enqueue",
        json=payload,
        headers={"Authorization": f"Bearer {ctx['sender_token']}"},
    )
    assert first.status_code == 201
    first_payload = first.json()
    assert len(first_payload["comunicaciones"]) == 2
    lote_id = first_payload["lote_id"]

    second = await ctx["client"].post(
        "/api/comunicaciones/enqueue",
        json=payload,
        headers={"Authorization": f"Bearer {ctx['sender_token']}"},
    )
    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["lote_id"] == lote_id
    assert len(second_payload["comunicaciones"]) == 2


@pytest.mark.asyncio
async def test_enqueue_no_filtra_destinatario_otro_tenant(comunicaciones_app):
    ctx = comunicaciones_app
    preview_response = await _preview(ctx, destinatarios=[ctx["entrada_b1_id"]])
    assert preview_response.status_code == 404


@pytest.mark.asyncio
async def test_aprobacion_por_lote_y_permiso_fail_closed(comunicaciones_app):
    ctx = comunicaciones_app
    preview_response = await _preview(ctx)
    preview_token = preview_response.json()["preview_token"]

    enqueue = await ctx["client"].post(
        "/api/comunicaciones/enqueue",
        json={
            "materia_id": str(ctx["materia_a_id"]),
            "destinatarios": [str(ctx["entrada_a1_id"]), str(ctx["entrada_a2_id"])],
            "asunto_template": "Aviso para {{nombre}}",
            "cuerpo_template": "Hola {{nombre}}, materia {{materia}}",
            "idempotency_key": "idem-approval-1",
            "preview_token": preview_token,
        },
        headers={"Authorization": f"Bearer {ctx['sender_token']}"},
    )
    lote_id = enqueue.json()["lote_id"]

    forbidden = await ctx["client"].post(
        f"/api/comunicaciones/lotes/{lote_id}/approve",
        headers={"Authorization": f"Bearer {ctx['no_approve_token']}"},
    )
    assert forbidden.status_code == 403

    allowed = await ctx["client"].post(
        f"/api/comunicaciones/lotes/{lote_id}/approve",
        headers={"Authorization": f"Bearer {ctx['approver_token']}"},
    )
    assert allowed.status_code == 200
    assert allowed.json()["aprobadas"] == 2


@pytest.mark.asyncio
async def test_aprobacion_individual_habilita_solo_una(comunicaciones_app):
    ctx = comunicaciones_app
    preview_response = await _preview(ctx)
    preview_token = preview_response.json()["preview_token"]

    enqueue = await ctx["client"].post(
        "/api/comunicaciones/enqueue",
        json={
            "materia_id": str(ctx["materia_a_id"]),
            "destinatarios": [str(ctx["entrada_a1_id"]), str(ctx["entrada_a2_id"])],
            "asunto_template": "Aviso para {{nombre}}",
            "cuerpo_template": "Hola {{nombre}}, materia {{materia}}",
            "idempotency_key": "idem-approval-individual",
            "preview_token": preview_token,
        },
        headers={"Authorization": f"Bearer {ctx['sender_token']}"},
    )
    comunicacion_id = enqueue.json()["comunicaciones"][0]["id"]

    approved = await ctx["client"].post(
        f"/api/comunicaciones/{comunicacion_id}/approve",
        headers={"Authorization": f"Bearer {ctx['approver_token']}"},
    )
    assert approved.status_code == 200
    assert approved.json()["aprobadas"] == 1


@pytest.mark.asyncio
async def test_preview_sin_permiso_retorna_403(comunicaciones_app):
    ctx = comunicaciones_app

    response = await ctx["client"].post(
        "/api/comunicaciones/preview",
        json={
            "materia_id": str(ctx["materia_a_id"]),
            "destinatarios": [str(ctx["entrada_a1_id"])],
            "asunto_template": "Aviso para {{nombre}}",
            "cuerpo_template": "Hola {{nombre}}, materia {{materia}}",
        },
        headers={"Authorization": f"Bearer {ctx['forbidden_token']}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_preview_rechaza_campos_extra_y_no_suplantacion_identidad(comunicaciones_app):
    ctx = comunicaciones_app

    response = await ctx["client"].post(
        "/api/comunicaciones/preview",
        json={
            "materia_id": str(ctx["materia_a_id"]),
            "destinatarios": [str(ctx["entrada_a1_id"])],
            "asunto_template": "Aviso para {{nombre}}",
            "cuerpo_template": "Hola {{nombre}}, materia {{materia}}",
            "tenant_id": str(ctx["tenant_b_id"]),
            "enviado_por": str(ctx["approver_auth_user_id"]),
        },
        headers={"Authorization": f"Bearer {ctx['sender_token']}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_cancelacion_solo_desde_pendiente(comunicaciones_app):
    ctx = comunicaciones_app
    preview_response = await _preview(ctx, destinatarios=[ctx["entrada_a1_id"]])
    preview_token = preview_response.json()["preview_token"]

    enqueue = await ctx["client"].post(
        "/api/comunicaciones/enqueue",
        json={
            "materia_id": str(ctx["materia_a_id"]),
            "destinatarios": [str(ctx["entrada_a1_id"])],
            "asunto_template": "Aviso para {{nombre}}",
            "cuerpo_template": "Hola {{nombre}}, materia {{materia}}",
            "idempotency_key": "idem-cancel-1",
            "preview_token": preview_token,
        },
        headers={"Authorization": f"Bearer {ctx['sender_token']}"},
    )
    comunicacion_id = enqueue.json()["comunicaciones"][0]["id"]

    cancelled = await ctx["client"].post(
        f"/api/comunicaciones/{comunicacion_id}/cancel",
        headers={"Authorization": f"Bearer {ctx['sender_token']}"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["estado"] == "Cancelado"

    cancelled_again = await ctx["client"].post(
        f"/api/comunicaciones/{comunicacion_id}/cancel",
        headers={"Authorization": f"Bearer {ctx['sender_token']}"},
    )
    assert cancelled_again.status_code == 409


@pytest.mark.asyncio
async def test_cancelacion_inexistente_retorna_404(comunicaciones_app):
    ctx = comunicaciones_app
    missing = await ctx["client"].post(
        f"/api/comunicaciones/{uuid.uuid4()}/cancel",
        headers={"Authorization": f"Bearer {ctx['sender_token']}"},
    )
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_cancelacion_enviando_rechazada(comunicaciones_app):
    ctx = comunicaciones_app
    from app.models.comunicacion import Comunicacion

    preview_response = await _preview(ctx, destinatarios=[ctx["entrada_a1_id"]])
    preview_token = preview_response.json()["preview_token"]
    enqueue = await ctx["client"].post(
        "/api/comunicaciones/enqueue",
        json={
            "materia_id": str(ctx["materia_a_id"]),
            "destinatarios": [str(ctx["entrada_a1_id"])],
            "asunto_template": "Aviso para {{nombre}}",
            "cuerpo_template": "Hola {{nombre}}, materia {{materia}}",
            "idempotency_key": "idem-cancel-enviando",
            "preview_token": preview_token,
        },
        headers={"Authorization": f"Bearer {ctx['sender_token']}"},
    )
    comunicacion_id = uuid.UUID(enqueue.json()["comunicaciones"][0]["id"])
    row = await ctx["session"].scalar(select(Comunicacion).where(Comunicacion.id == comunicacion_id))
    row.estado = "Enviando"
    await ctx["session"].commit()

    cancelled = await ctx["client"].post(
        f"/api/comunicaciones/{comunicacion_id}/cancel",
        headers={"Authorization": f"Bearer {ctx['sender_token']}"},
    )
    assert cancelled.status_code == 409

    refreshed = await ctx["session"].scalar(select(Comunicacion).where(Comunicacion.id == comunicacion_id))
    assert refreshed.estado == "Enviando"


@pytest.mark.asyncio
async def test_encrypta_destinatario_y_mascara_api(comunicaciones_app):
    ctx = comunicaciones_app
    preview_response = await _preview(ctx, destinatarios=[ctx["entrada_a1_id"]])
    preview_token = preview_response.json()["preview_token"]

    enqueue = await ctx["client"].post(
        "/api/comunicaciones/enqueue",
        json={
            "materia_id": str(ctx["materia_a_id"]),
            "destinatarios": [str(ctx["entrada_a1_id"])],
            "asunto_template": "Aviso para {{nombre}}",
            "cuerpo_template": "Hola {{nombre}}, materia {{materia}}",
            "idempotency_key": "idem-encryption-1",
            "preview_token": preview_token,
        },
        headers={"Authorization": f"Bearer {ctx['sender_token']}"},
    )
    assert enqueue.status_code == 201

    from app.models.comunicacion import Comunicacion

    session = ctx["session"]
    comunicacion_id = uuid.UUID(enqueue.json()["comunicaciones"][0]["id"])
    comunicacion = await session.scalar(select(Comunicacion).where(Comunicacion.id == comunicacion_id))
    assert comunicacion is not None
    assert comunicacion.destinatario_encrypted != "ana@tenant-a.local"
    assert decrypt_value(comunicacion.destinatario_encrypted) == "ana@tenant-a.local"

    listado = await ctx["client"].get(
        "/api/comunicaciones",
        headers={"Authorization": f"Bearer {ctx['sender_token']}"},
    )
    assert listado.status_code == 200
    assert listado.json()[0]["destinatario_masked"] == "a***@tenant-a.local"


@pytest.mark.asyncio
async def test_worker_transiciones_a_enviado_y_audit(comunicaciones_app):
    ctx = comunicaciones_app
    from app.services.comunicaciones import CommunicationDispatchService, FakeCommunicationProvider

    preview_response = await _preview(ctx, destinatarios=[ctx["entrada_a1_id"]])
    preview_token = preview_response.json()["preview_token"]
    enqueue = await ctx["client"].post(
        "/api/comunicaciones/enqueue",
        json={
            "materia_id": str(ctx["materia_a_id"]),
            "destinatarios": [str(ctx["entrada_a1_id"])],
            "asunto_template": "Aviso para {{nombre}}",
            "cuerpo_template": "Hola {{nombre}}, materia {{materia}}",
            "idempotency_key": "idem-worker-ok",
            "preview_token": preview_token,
        },
        headers={"Authorization": f"Bearer {ctx['sender_token']}"},
    )
    assert enqueue.status_code == 201

    service = CommunicationDispatchService(session=ctx["session"], provider=FakeCommunicationProvider())
    processed = await service.process_pending(limit=10)
    await ctx["session"].commit()
    assert processed == 1

    from app.models.comunicacion import Comunicacion

    comunicacion_id = uuid.UUID(enqueue.json()["comunicaciones"][0]["id"])
    refreshed = await ctx["session"].scalar(select(Comunicacion).where(Comunicacion.id == comunicacion_id))
    assert refreshed.estado == "Enviado"
    assert refreshed.enviado_at is not None

    audit_rows = list((await ctx["session"].scalars(select(AuditLog).where(AuditLog.tenant_id == ctx["tenant_a_id"]))).all())
    acciones = {row.accion for row in audit_rows}
    assert "COMUNICACION_ENVIAR" in acciones


@pytest.mark.asyncio
async def test_transicion_invalida_desde_enviado_rechazada(comunicaciones_app):
    ctx = comunicaciones_app
    from app.core.dependencies import AuthenticatedUser
    from app.models.comunicacion import Comunicacion
    from app.services.comunicaciones import CommunicationError, CommunicationDispatchService, ComunicacionService, FakeCommunicationProvider

    preview_response = await _preview(ctx, destinatarios=[ctx["entrada_a1_id"]])
    preview_token = preview_response.json()["preview_token"]
    enqueue = await ctx["client"].post(
        "/api/comunicaciones/enqueue",
        json={
            "materia_id": str(ctx["materia_a_id"]),
            "destinatarios": [str(ctx["entrada_a1_id"])],
            "asunto_template": "Aviso para {{nombre}}",
            "cuerpo_template": "Hola {{nombre}}, materia {{materia}}",
            "idempotency_key": "idem-invalid-transition",
            "preview_token": preview_token,
        },
        headers={"Authorization": f"Bearer {ctx['sender_token']}"},
    )
    comunicacion_id = uuid.UUID(enqueue.json()["comunicaciones"][0]["id"])

    worker = CommunicationDispatchService(session=ctx["session"], provider=FakeCommunicationProvider())
    await worker.process_pending(limit=10)
    await ctx["session"].commit()

    row = await ctx["session"].scalar(select(Comunicacion).where(Comunicacion.id == comunicacion_id))
    service = ComunicacionService(session=ctx["session"], tenant_id=ctx["tenant_a_id"])
    with pytest.raises(CommunicationError):
        service._transition(row, "Pendiente")
    assert row.estado == "Enviado"


@pytest.mark.asyncio
async def test_worker_bloqueado_hasta_aprobacion_por_tenant(comunicaciones_app):
    ctx = comunicaciones_app
    from app.models import AuditLog
    from app.models.comunicacion import Comunicacion
    from app.services.comunicaciones import CommunicationDispatchService, FakeCommunicationProvider

    preview_response = await _preview(ctx)
    preview_token = preview_response.json()["preview_token"]
    enqueue = await ctx["client"].post(
        "/api/comunicaciones/enqueue",
        json={
            "materia_id": str(ctx["materia_a_id"]),
            "destinatarios": [str(ctx["entrada_a1_id"]), str(ctx["entrada_a2_id"])],
            "asunto_template": "Aviso para {{nombre}}",
            "cuerpo_template": "Hola {{nombre}}, materia {{materia}}",
            "idempotency_key": "idem-gated-worker",
            "preview_token": preview_token,
        },
        headers={"Authorization": f"Bearer {ctx['sender_token']}"},
    )
    lote_id = enqueue.json()["lote_id"]

    worker = CommunicationDispatchService(session=ctx["session"], provider=FakeCommunicationProvider())
    processed_before = await worker.process_pending(limit=10)
    await ctx["session"].commit()
    assert processed_before == 0

    rows_before = list((await ctx["session"].scalars(select(Comunicacion).where(Comunicacion.lote_id == uuid.UUID(lote_id)))).all())
    assert rows_before
    assert {row.estado for row in rows_before} == {"Pendiente"}
    assert all(row.aprobado_at is None for row in rows_before)

    approve = await ctx["client"].post(
        f"/api/comunicaciones/lotes/{lote_id}/approve",
        headers={"Authorization": f"Bearer {ctx['approver_token']}"},
    )
    assert approve.status_code == 200
    assert approve.json()["aprobadas"] == 2

    processed_after = await worker.process_pending(limit=10)
    await ctx["session"].commit()
    assert processed_after == 2

    rows_after = list((await ctx["session"].scalars(select(Comunicacion).where(Comunicacion.lote_id == uuid.UUID(lote_id)))).all())
    assert {row.estado for row in rows_after} == {"Enviado"}

    approval_audit = list((await ctx["session"].scalars(select(AuditLog).where(AuditLog.accion == "COMUNICACION_APROBAR"))).all())
    assert approval_audit
    assert approval_audit[-1].detalle["lote_id"] == lote_id
    assert approval_audit[-1].detalle["filas_afectadas"] == 2
    assert "tenant-a.local" not in str(approval_audit[-1].detalle)


@pytest.mark.asyncio
async def test_worker_error_controlado_sin_pii_en_logs(comunicaciones_app, caplog: pytest.LogCaptureFixture):
    ctx = comunicaciones_app
    from app.services.comunicaciones import CommunicationDispatchService, FailingCommunicationProvider

    preview_response = await _preview(ctx, destinatarios=[ctx["entrada_a1_id"]])
    preview_token = preview_response.json()["preview_token"]
    enqueue = await ctx["client"].post(
        "/api/comunicaciones/enqueue",
        json={
            "materia_id": str(ctx["materia_a_id"]),
            "destinatarios": [str(ctx["entrada_a1_id"])],
            "asunto_template": "Aviso para {{nombre}}",
            "cuerpo_template": "Hola {{nombre}}, materia {{materia}}",
            "idempotency_key": "idem-worker-fail",
            "preview_token": preview_token,
        },
        headers={"Authorization": f"Bearer {ctx['sender_token']}"},
    )
    assert enqueue.status_code == 201

    caplog.set_level(logging.INFO)
    service = CommunicationDispatchService(session=ctx["session"], provider=FailingCommunicationProvider())
    processed = await service.process_pending(limit=10)
    await ctx["session"].commit()
    assert processed == 1

    from app.models.comunicacion import Comunicacion

    comunicacion_id = uuid.UUID(enqueue.json()["comunicaciones"][0]["id"])
    refreshed = await ctx["session"].scalar(select(Comunicacion).where(Comunicacion.id == comunicacion_id))
    assert refreshed.estado in {"Pendiente", "Error"}
    assert refreshed.intentos >= 1

    rendered_logs = " ".join(record.getMessage() for record in caplog.records)
    assert "ana@tenant-a.local" not in rendered_logs


@pytest.mark.asyncio
async def test_worker_omite_canceladas(comunicaciones_app):
    ctx = comunicaciones_app
    from app.services.comunicaciones import CommunicationDispatchService, FakeCommunicationProvider

    preview_response = await _preview(ctx, destinatarios=[ctx["entrada_a1_id"]])
    preview_token = preview_response.json()["preview_token"]
    enqueue = await ctx["client"].post(
        "/api/comunicaciones/enqueue",
        json={
            "materia_id": str(ctx["materia_a_id"]),
            "destinatarios": [str(ctx["entrada_a1_id"])],
            "asunto_template": "Aviso para {{nombre}}",
            "cuerpo_template": "Hola {{nombre}}, materia {{materia}}",
            "idempotency_key": "idem-worker-cancelled",
            "preview_token": preview_token,
        },
        headers={"Authorization": f"Bearer {ctx['sender_token']}"},
    )
    comunicacion_id = enqueue.json()["comunicaciones"][0]["id"]

    cancelled = await ctx["client"].post(
        f"/api/comunicaciones/{comunicacion_id}/cancel",
        headers={"Authorization": f"Bearer {ctx['sender_token']}"},
    )
    assert cancelled.status_code == 200

    processed = await CommunicationDispatchService(session=ctx["session"], provider=FakeCommunicationProvider()).process_pending(limit=10)
    await ctx["session"].commit()
    assert processed == 0


@pytest.mark.asyncio
async def test_cancelacion_audita_sin_plaintext(comunicaciones_app):
    ctx = comunicaciones_app
    from app.models import AuditLog

    preview_response = await _preview(ctx, destinatarios=[ctx["entrada_a1_id"]])
    preview_token = preview_response.json()["preview_token"]
    enqueue = await ctx["client"].post(
        "/api/comunicaciones/enqueue",
        json={
            "materia_id": str(ctx["materia_a_id"]),
            "destinatarios": [str(ctx["entrada_a1_id"])],
            "asunto_template": "Aviso para {{nombre}}",
            "cuerpo_template": "Hola {{nombre}}, materia {{materia}}",
            "idempotency_key": "idem-cancel-audit",
            "preview_token": preview_token,
        },
        headers={"Authorization": f"Bearer {ctx['sender_token']}"},
    )
    comunicacion_id = enqueue.json()["comunicaciones"][0]["id"]

    cancelled = await ctx["client"].post(
        f"/api/comunicaciones/{comunicacion_id}/cancel",
        headers={"Authorization": f"Bearer {ctx['sender_token']}"},
    )
    assert cancelled.status_code == 200

    audit_rows = list((await ctx["session"].scalars(select(AuditLog).where(AuditLog.accion == "COMUNICACION_CANCELAR"))).all())
    assert audit_rows
    assert audit_rows[-1].detalle["comunicacion_id"] == comunicacion_id
    assert audit_rows[-1].detalle["filas_afectadas"] == 1
    assert "tenant-a.local" not in str(audit_rows[-1].detalle)


@pytest.mark.asyncio
async def test_aprobacion_individual_enviado_retorna_409(comunicaciones_app):
    ctx = comunicaciones_app
    from app.services.comunicaciones import CommunicationDispatchService, FakeCommunicationProvider

    preview_response = await _preview(ctx, destinatarios=[ctx["entrada_a1_id"]])
    preview_token = preview_response.json()["preview_token"]
    enqueue = await ctx["client"].post(
        "/api/comunicaciones/enqueue",
        json={
            "materia_id": str(ctx["materia_a_id"]),
            "destinatarios": [str(ctx["entrada_a1_id"])],
            "asunto_template": "Aviso para {{nombre}}",
            "cuerpo_template": "Hola {{nombre}}, materia {{materia}}",
            "idempotency_key": "idem-approved-conflict",
            "preview_token": preview_token,
        },
        headers={"Authorization": f"Bearer {ctx['sender_token']}"},
    )
    comunicacion_id = enqueue.json()["comunicaciones"][0]["id"]

    service = CommunicationDispatchService(session=ctx["session"], provider=FakeCommunicationProvider())
    await service.process_pending(limit=10)
    await ctx["session"].commit()

    approve = await ctx["client"].post(
        f"/api/comunicaciones/{comunicacion_id}/approve",
        headers={"Authorization": f"Bearer {ctx['approver_token']}"},
    )
    assert approve.status_code == 409


@pytest.mark.asyncio
async def test_worker_agota_reintento_y_pasa_a_error(comunicaciones_app):
    ctx = comunicaciones_app
    from app.services.comunicaciones import CommunicationDispatchService, FailingCommunicationProvider

    preview_response = await _preview(ctx, destinatarios=[ctx["entrada_a1_id"]])
    preview_token = preview_response.json()["preview_token"]
    enqueue = await ctx["client"].post(
        "/api/comunicaciones/enqueue",
        json={
            "materia_id": str(ctx["materia_a_id"]),
            "destinatarios": [str(ctx["entrada_a1_id"])],
            "asunto_template": "Aviso para {{nombre}}",
            "cuerpo_template": "Hola {{nombre}}, materia {{materia}}",
            "idempotency_key": "idem-error-final",
            "preview_token": preview_token,
        },
        headers={"Authorization": f"Bearer {ctx['sender_token']}"},
    )
    comunicacion_id = uuid.UUID(enqueue.json()["comunicaciones"][0]["id"])

    service = CommunicationDispatchService(session=ctx["session"], provider=FailingCommunicationProvider(), max_retries=1)
    await service.process_pending(limit=10)
    await ctx["session"].commit()

    from app.models.comunicacion import Comunicacion

    refreshed = await ctx["session"].scalar(select(Comunicacion).where(Comunicacion.id == comunicacion_id))
    assert refreshed.estado == "Error"


@pytest.mark.asyncio
async def test_service_directo_cubre_preview_enqueue_aprobar_cancelar_y_listar(comunicaciones_app):
    ctx = comunicaciones_app
    from app.core.dependencies import AuthenticatedUser
    from app.services.comunicaciones import ComunicacionService

    user = AuthenticatedUser(user_id=ctx["sender_auth_user_id"], tenant_id=ctx["tenant_a_id"], roles=["PROFESOR"])
    approver = AuthenticatedUser(user_id=ctx["approver_auth_user_id"], tenant_id=ctx["tenant_a_id"], roles=["COORDINADOR"])
    service = ComunicacionService(session=ctx["session"], tenant_id=ctx["tenant_a_id"])

    preview = await service.preview(
        user=user,
        materia_id=ctx["materia_a_id"],
        destinatarios=[ctx["entrada_a1_id"]],
        asunto_template="Aviso para {{nombre}}",
        cuerpo_template="Hola {{nombre}}, materia {{materia}}",
    )
    assert preview["items"][0]["destinatario_masked"].startswith("a***")

    enqueue = await service.enqueue(
        user=user,
        materia_id=ctx["materia_a_id"],
        destinatarios=[ctx["entrada_a1_id"]],
        asunto_template="Aviso para {{nombre}}",
        cuerpo_template="Hola {{nombre}}, materia {{materia}}",
        idempotency_key="idem-direct-service",
        preview_token=preview["preview_token"],
    )
    assert enqueue["reused"] is False
    comunicacion_id = enqueue["comunicaciones"][0]["id"]

    approved = await service.approve_one(user=approver, comunicacion_id=comunicacion_id)
    assert approved in {0, 1}

    listed = await service.list_items()
    assert listed

    cancelled_id = (await service.enqueue(
        user=user,
        materia_id=ctx["materia_a_id"],
        destinatarios=[ctx["entrada_a2_id"]],
        asunto_template="Aviso para {{nombre}}",
        cuerpo_template="Hola {{nombre}}, materia {{materia}}",
        idempotency_key="idem-direct-cancel",
        preview_token=(await service.preview(
            user=user,
            materia_id=ctx["materia_a_id"],
            destinatarios=[ctx["entrada_a2_id"]],
            asunto_template="Aviso para {{nombre}}",
            cuerpo_template="Hola {{nombre}}, materia {{materia}}",
        ))["preview_token"],
    ))["comunicaciones"][0]["id"]
    cancelled = await service.cancel(user=user, comunicacion_id=cancelled_id)
    assert cancelled.estado == "Cancelado"


@pytest.mark.asyncio
async def test_router_directo_cubre_ramas_restantes(comunicaciones_app):
    ctx = comunicaciones_app
    from app.api.v1.routers import comunicaciones as router_module
    from app.core.dependencies import AuthenticatedUser
    from app.schemas.comunicaciones import EnqueueRequest, PreviewRequest

    sender = AuthenticatedUser(user_id=ctx["sender_auth_user_id"], tenant_id=ctx["tenant_a_id"], roles=["PROFESOR"])
    approver = AuthenticatedUser(user_id=ctx["approver_auth_user_id"], tenant_id=ctx["tenant_a_id"], roles=["COORDINADOR"])

    preview_payload = PreviewRequest(
        materia_id=ctx["materia_a_id"],
        destinatarios=[ctx["entrada_a1_id"]],
        asunto_template="Aviso para {{nombre}}",
        cuerpo_template="Hola {{nombre}}, materia {{materia}}",
    )
    preview = await router_module.preview(preview_payload, sender, ctx["session"])
    response = Response(status_code=201)
    enqueue_payload = EnqueueRequest(
        **preview_payload.model_dump(),
        idempotency_key="idem-router-directo",
        preview_token=preview.preview_token,
    )

    created = await router_module.enqueue(enqueue_payload, sender, ctx["session"], response)
    await ctx["session"].commit()
    assert response.status_code == 201
    reused = await router_module.enqueue(enqueue_payload, sender, ctx["session"], response)
    await ctx["session"].commit()
    assert reused.reused is True
    assert response.status_code == 200

    approved_lote = await router_module.approve_lote(created.lote_id, approver, ctx["session"])
    await ctx["session"].commit()
    assert approved_lote.aprobadas in {0, 1}

    with pytest.raises(HTTPException) as approve_error:
        await router_module.approve_one(uuid.uuid4(), approver, ctx["session"])
    assert approve_error.value.status_code == 404

    with pytest.raises(HTTPException) as cancel_error:
        await router_module.cancel(uuid.uuid4(), sender, ctx["session"])
    assert cancel_error.value.status_code == 404

    with pytest.raises(HTTPException) as preview_error:
        await router_module.preview(
            PreviewRequest(
                materia_id=ctx["materia_a_id"],
                destinatarios=[ctx["entrada_b1_id"]],
                asunto_template="Aviso para {{nombre}}",
                cuerpo_template="Hola {{nombre}}, materia {{materia}}",
            ),
            sender,
            ctx["session"],
        )
    assert preview_error.value.status_code == 404
