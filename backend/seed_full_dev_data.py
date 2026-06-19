"""Seed ampliado de datos de prueba para desarrollo local.

Asume que seed_dev_data.py ya fue ejecutado. Recupera los IDs existentes
por query y agrega: Padron, Calificaciones, Umbrales, Comunicaciones,
Avisos, Tareas, Salarios y Liquidaciones.

Uso: python seed_full_dev_data.py
     (o bien: docker-compose exec api python seed_full_dev_data.py)
"""

import asyncio
import hashlib
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

sys.path.insert(0, ".")


def _hash_email(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()


async def main():
    from sqlalchemy import select, text

    from app.core.config import get_settings
    from app.core.database import get_session_factory, initialize_database
    from app.core.security import encrypt_value
    from app.models import (
        Asignacion,
        AuthUser,
        Aviso,
        Calificacion,
        Comunicacion,
        EntradaPadron,
        FinalizacionActividad,
        Liquidacion,
        Materia,
        SalarioBase,
        SalarioPlus,
        Tarea,
        UmbralMateria,
        Usuario,
        VersionPadron,
    )
    from app.models.estructura import Carrera, Cohorte

    settings = get_settings()
    initialize_database()
    factory = get_session_factory()

    async with factory() as session:

        # ── 0. Recuperar IDs existentes ──
        print("Recuperando IDs existentes del seed base...")

        tenant_row = (await session.execute(
            text("SELECT id FROM tenant WHERE slug = 'demo' LIMIT 1")
        )).fetchone()
        if not tenant_row:
            print("[ERROR] Tenant 'demo' no encontrado. Ejecuta seed_dev_data.py primero.")
            return
        tenant_id = tenant_row[0]
        print(f"  -> Tenant ID: {tenant_id}")

        admin_auth_row = (await session.execute(
            text("SELECT id FROM auth_user WHERE email = 'admin@demo.com' AND tenant_id = :tid LIMIT 1"),
            {"tid": tenant_id},
        )).fetchone()
        if not admin_auth_row:
            print("[ERROR] AuthUser admin@demo.com no encontrado.")
            return
        admin_auth_user_id = admin_auth_row[0]
        print(f"  -> Admin AuthUser ID: {admin_auth_user_id}")

        admin_perfil_row = (await session.execute(
            text("SELECT id FROM usuario WHERE auth_user_id = :uid AND tenant_id = :tid LIMIT 1"),
            {"uid": admin_auth_user_id, "tid": tenant_id},
        )).fetchone()
        if not admin_perfil_row:
            print("[ERROR] Usuario perfil del admin no encontrado.")
            return
        admin_perfil_id = admin_perfil_row[0]
        print(f"  -> Admin perfil (Usuario) ID: {admin_perfil_id}")

        materia_row = (await session.execute(
            text("SELECT id FROM materia WHERE codigo = 'ING-SIS-101' AND tenant_id = :tid LIMIT 1"),
            {"tid": tenant_id},
        )).fetchone()
        if not materia_row:
            print("[ERROR] Materia ING-SIS-101 no encontrada.")
            return
        materia_id = materia_row[0]
        print(f"  -> Materia ID: {materia_id}")

        cohorte_row = (await session.execute(
            text("SELECT id FROM cohorte WHERE nombre = '2026' AND tenant_id = :tid LIMIT 1"),
            {"tid": tenant_id},
        )).fetchone()
        if not cohorte_row:
            print("[ERROR] Cohorte 2026 no encontrada.")
            return
        cohorte_id = cohorte_row[0]
        print(f"  -> Cohorte ID: {cohorte_id}")

        asignacion_row = (await session.execute(
            text(
                "SELECT id FROM asignacion "
                "WHERE usuario_id = :uid AND materia_id = :mid AND tenant_id = :tid "
                "LIMIT 1"
            ),
            {"uid": admin_perfil_id, "mid": materia_id, "tid": tenant_id},
        )).fetchone()
        if not asignacion_row:
            print("[ERROR] Asignacion del admin a la materia no encontrada.")
            return
        asignacion_id = asignacion_row[0]
        print(f"  -> Asignacion ID: {asignacion_id}")

        # ── 1. VersionPadron ──
        print("\nCreando VersionPadron...")
        existing_version = (await session.execute(
            text(
                "SELECT id FROM version_padron "
                "WHERE tenant_id = :tid AND materia_id = :mid AND cohorte_id = :cid AND activa = true "
                "LIMIT 1"
            ),
            {"tid": tenant_id, "mid": materia_id, "cid": cohorte_id},
        )).fetchone()

        if existing_version:
            version_id = existing_version[0]
            print(f"  [WARN] VersionPadron activa ya existe (ID: {version_id}), se reutiliza.")
        else:
            version = VersionPadron(
                tenant_id=tenant_id,
                materia_id=materia_id,
                cohorte_id=cohorte_id,
                cargado_por=admin_perfil_id,
                cargado_at=datetime.now(timezone.utc),
                activa=True,
            )
            session.add(version)
            await session.flush()
            version_id = version.id
            print(f"  -> VersionPadron ID: {version_id}")

        # ── 2. EntradaPadron — 4 alumnos ──
        print("\nCreando EntradaPadron (4 alumnos)...")
        alumnos_data = [
            ("alumno1@demo.com", "Lucía", "Fernández"),
            ("alumno2@demo.com", "Marcos", "Díaz"),
            ("alumno3@demo.com", "Valentina", "Ruiz"),
            ("alumno4@demo.com", "Tomás", "Medina"),
        ]

        entradas = {}
        for email, nombre, apellidos in alumnos_data:
            email_hash = _hash_email(email)
            existing_entrada = (await session.execute(
                text(
                    "SELECT id FROM entrada_padron "
                    "WHERE tenant_id = :tid AND email_hash = :ehash AND version_id = :vid "
                    "LIMIT 1"
                ),
                {"tid": tenant_id, "ehash": email_hash, "vid": version_id},
            )).fetchone()

            if existing_entrada:
                entradas[email] = existing_entrada[0]
                print(f"  [WARN] EntradaPadron {email} ya existe (ID: {existing_entrada[0]}), se reutiliza.")
            else:
                entrada = EntradaPadron(
                    tenant_id=tenant_id,
                    version_id=version_id,
                    nombre=nombre,
                    apellidos=apellidos,
                    email_encrypted=encrypt_value(email),
                    email_hash=email_hash,
                    comision="A",
                    regional="CABA",
                )
                session.add(entrada)
                await session.flush()
                entradas[email] = entrada.id
                print(f"  -> EntradaPadron {email} ID: {entrada.id}")

        # ── 3. UmbralMateria ──
        print("\nCreando UmbralMateria...")
        existing_umbral = (await session.execute(
            text(
                "SELECT id FROM umbral_materia "
                "WHERE tenant_id = :tid AND asignacion_id = :aid AND materia_id = :mid "
                "LIMIT 1"
            ),
            {"tid": tenant_id, "aid": asignacion_id, "mid": materia_id},
        )).fetchone()

        if existing_umbral:
            print(f"  [WARN] UmbralMateria ya existe (ID: {existing_umbral[0]}), se omite.")
        else:
            umbral = UmbralMateria(
                tenant_id=tenant_id,
                asignacion_id=asignacion_id,
                materia_id=materia_id,
                umbral_pct=Decimal("60.00"),
                valores_aprobatorios=["Satisfactorio", "Supera lo esperado"],
            )
            session.add(umbral)
            await session.flush()
            print(f"  -> UmbralMateria ID: {umbral.id}")

        # ── 4. Calificaciones + FinalizacionActividad ──
        print("\nCreando Calificaciones y FinalizacionActividad...")

        # (email, actividad, nota_numerica, nota_textual)
        # aprobado = nota_numerica >= 60 si numerica, sino nota_textual in valores_aprobatorios
        valores_aprobatorios = {"Satisfactorio", "Supera lo esperado"}
        calificaciones_data = [
            # alumno1: todos aprobados
            ("alumno1@demo.com", "TP1",      Decimal("80"), None),
            ("alumno1@demo.com", "TP2",      Decimal("75"), None),
            ("alumno1@demo.com", "Parcial 1", Decimal("85"), None),
            # alumno2: todos reprobados
            ("alumno2@demo.com", "TP1",      Decimal("45"), None),
            ("alumno2@demo.com", "TP2",      Decimal("55"), None),
            ("alumno2@demo.com", "Parcial 1", Decimal("40"), None),
            # alumno3: mixto — TP2 es textual aprobatorio
            ("alumno3@demo.com", "TP1",      Decimal("70"), None),
            ("alumno3@demo.com", "TP2",      None,          "Satisfactorio"),
            ("alumno3@demo.com", "Parcial 1", Decimal("60"), None),
            # alumno4: casi todo aprobado — Parcial1 es textual aprobatorio
            ("alumno4@demo.com", "TP1",      Decimal("90"), None),
            ("alumno4@demo.com", "TP2",      Decimal("85"), None),
            ("alumno4@demo.com", "Parcial 1", None,         "Supera lo esperado"),
        ]

        for email, actividad, nota_num, nota_txt in calificaciones_data:
            entrada_id = entradas[email]

            # Determinar aprobado
            if nota_num is not None:
                aprobado = nota_num >= Decimal("60")
            else:
                aprobado = nota_txt in valores_aprobatorios

            es_textual = nota_txt is not None

            # Calificacion — unique: (tenant_id, entrada_padron_id, actividad, actor_id)
            existing_cal = (await session.execute(
                text(
                    "SELECT id FROM calificacion "
                    "WHERE tenant_id = :tid AND entrada_padron_id = :eid "
                    "AND actividad = :act AND actor_id = :aid "
                    "LIMIT 1"
                ),
                {"tid": tenant_id, "eid": entrada_id, "act": actividad, "aid": admin_perfil_id},
            )).fetchone()

            if existing_cal:
                print(f"  [WARN] Calificacion {email}/{actividad} ya existe, se omite.")
            else:
                cal = Calificacion(
                    tenant_id=tenant_id,
                    entrada_padron_id=entrada_id,
                    actor_id=admin_perfil_id,
                    actividad=actividad,
                    nota_numerica=nota_num,
                    nota_textual=nota_txt,
                    aprobado=aprobado,
                    origen="Importado",
                )
                session.add(cal)

            # FinalizacionActividad — unique: (tenant_id, entrada_padron_id, actividad)
            existing_fin = (await session.execute(
                text(
                    "SELECT id FROM finalizacion_actividad "
                    "WHERE tenant_id = :tid AND entrada_padron_id = :eid AND actividad = :act "
                    "LIMIT 1"
                ),
                {"tid": tenant_id, "eid": entrada_id, "act": actividad},
            )).fetchone()

            if existing_fin:
                print(f"  [WARN] FinalizacionActividad {email}/{actividad} ya existe, se omite.")
            else:
                fin = FinalizacionActividad(
                    tenant_id=tenant_id,
                    entrada_padron_id=entrada_id,
                    actividad=actividad,
                    es_textual=es_textual,
                    finalizado=aprobado,
                )
                session.add(fin)

        await session.flush()
        print("  -> Calificaciones y FinalizacionActividad creadas.")

        # ── 5. Comunicaciones ──
        print("\nCreando Comunicaciones...")

        comunicaciones_data = [
            {
                "entrada_email": "alumno2@demo.com",
                "asunto": "Seguimiento académico",
                "cuerpo": (
                    "Estimado/a Marcos, te contactamos porque detectamos atrasos "
                    "en las entregas de TP1, TP2 y Parcial 1. "
                    "Te pedimos que te pongas en contacto con tu tutor a la brevedad."
                ),
                "estado": "Pendiente",
                "requiere_aprobacion": True,
            },
            {
                "entrada_email": "alumno1@demo.com",
                "asunto": "Felicitaciones por tu rendimiento",
                "cuerpo": (
                    "Estimada Lucía, queremos felicitarte por tu excelente rendimiento "
                    "durante el cuatrimestre. Seguí así."
                ),
                "estado": "Enviada",
                "requiere_aprobacion": False,
            },
        ]

        for com_data in comunicaciones_data:
            entrada_id = entradas[com_data["entrada_email"]]
            idem_key = str(uuid.uuid4())
            lote = uuid.uuid4()
            now_utc = datetime.now(timezone.utc)

            enviado_at = now_utc if com_data["estado"] == "Enviada" else None

            com = Comunicacion(
                tenant_id=tenant_id,
                materia_id=materia_id,
                entrada_padron_id=entrada_id,
                enviado_por=admin_auth_user_id,
                destinatario_encrypted=encrypt_value(com_data["entrada_email"]),
                asunto=com_data["asunto"],
                cuerpo=com_data["cuerpo"],
                estado=com_data["estado"],
                lote_id=lote,
                idempotency_key=idem_key,
                requiere_aprobacion=com_data["requiere_aprobacion"],
                enviado_at=enviado_at,
                intentos=1 if com_data["estado"] == "Enviada" else 0,
            )
            session.add(com)

        await session.flush()
        print("  -> Comunicaciones creadas.")

        # ── 6. Avisos ──
        print("\nCreando Avisos...")
        now_utc = datetime.now(timezone.utc)

        avisos_data = [
            {
                "titulo": "Recordatorio: Entrega TP2",
                "cuerpo": "Se recuerda que la fecha límite de entrega del TP2 es el viernes de la semana próxima.",
                "alcance": "Materia",
                "materia_id": materia_id,
                "severidad": "Warning",
                "requiere_ack": False,
                "inicio_en": now_utc,
                "fin_en": now_utc + timedelta(days=7),
            },
            {
                "titulo": "Bienvenidos al cuatrimestre",
                "cuerpo": "La coordinación les da la bienvenida al cuatrimestre 2026. Consulten el cronograma en el aula virtual.",
                "alcance": "General",
                "materia_id": None,
                "severidad": "Info",
                "requiere_ack": False,
                "inicio_en": now_utc - timedelta(days=5),
                "fin_en": now_utc + timedelta(days=90),
            },
        ]

        for av_data in avisos_data:
            aviso = Aviso(
                tenant_id=tenant_id,
                alcance=av_data["alcance"],
                materia_id=av_data["materia_id"],
                severidad=av_data["severidad"],
                titulo=av_data["titulo"],
                cuerpo=av_data["cuerpo"],
                inicio_en=av_data["inicio_en"],
                fin_en=av_data["fin_en"],
                orden=0,
                activo=True,
                requiere_ack=av_data["requiere_ack"],
            )
            session.add(aviso)

        await session.flush()
        print("  -> Avisos creados.")

        # ── 7. Tareas ──
        print("\nCreando Tareas...")

        tareas_data = [
            {
                "descripcion": "Corregir TPs pendientes de alumno2 (Marcos Díaz). Revisar TP1, TP2 y Parcial 1.",
                "estado": "Pendiente",
                "materia_id": materia_id,
            },
            {
                "descripcion": "Preparar material del Parcial 2: consignas, criterios de evaluación y rúbrica.",
                "estado": "En Progreso",
                "materia_id": materia_id,
            },
            {
                "descripcion": "Actualizar umbral de aprobación para el período 2026-2.",
                "estado": "Completada",
                "materia_id": None,
            },
        ]

        for t_data in tareas_data:
            tarea = Tarea(
                tenant_id=tenant_id,
                materia_id=t_data["materia_id"],
                asignado_a=admin_perfil_id,
                asignado_por=admin_perfil_id,
                estado=t_data["estado"],
                descripcion=t_data["descripcion"],
            )
            session.add(tarea)

        await session.flush()
        print("  -> Tareas creadas.")

        # ── 8. SalarioBase ──
        print("\nCreando SalarioBase...")

        salarios_base_data = [
            ("PROFESOR",     Decimal("50000.00"), date(2026, 1, 1), None),
            ("TUTOR",        Decimal("30000.00"), date(2026, 1, 1), None),
            ("COORDINADOR",  Decimal("70000.00"), date(2026, 1, 1), None),
        ]

        for rol, monto, desde, hasta in salarios_base_data:
            existing_sb = (await session.execute(
                text(
                    "SELECT id FROM salario_base "
                    "WHERE tenant_id = :tid AND rol = :rol AND desde = :desde "
                    "LIMIT 1"
                ),
                {"tid": tenant_id, "rol": rol, "desde": desde},
            )).fetchone()

            if existing_sb:
                print(f"  [WARN] SalarioBase {rol}/{desde} ya existe, se omite.")
            else:
                sb = SalarioBase(
                    tenant_id=tenant_id,
                    rol=rol,
                    monto=monto,
                    desde=desde,
                    hasta=hasta,
                )
                session.add(sb)

        await session.flush()
        print("  -> SalarioBase creados.")

        # ── 9. SalarioPlus ──
        print("\nCreando SalarioPlus...")

        existing_sp = (await session.execute(
            text(
                "SELECT id FROM salario_plus "
                "WHERE tenant_id = :tid AND grupo = :g AND rol = :r AND desde = :d "
                "LIMIT 1"
            ),
            {
                "tid": tenant_id,
                "g": "Carga Horaria Completa",
                "r": "PROFESOR",
                "d": date(2026, 1, 1),
            },
        )).fetchone()

        if existing_sp:
            print(f"  [WARN] SalarioPlus ya existe, se omite.")
        else:
            sp = SalarioPlus(
                tenant_id=tenant_id,
                grupo="Carga Horaria Completa",
                rol="PROFESOR",
                descripcion="Plus por carga horaria completa asignada al cuatrimestre.",
                monto=Decimal("10000.00"),
                desde=date(2026, 1, 1),
                hasta=None,
            )
            session.add(sp)
            await session.flush()
            print(f"  -> SalarioPlus ID: {sp.id}")

        # ── 10. Liquidacion ──
        print("\nCreando Liquidacion...")

        existing_liq = (await session.execute(
            text(
                "SELECT id FROM liquidacion "
                "WHERE tenant_id = :tid AND cohorte_id = :cid "
                "AND periodo = :p AND usuario_id = :uid AND rol = :r "
                "LIMIT 1"
            ),
            {
                "tid": tenant_id,
                "cid": cohorte_id,
                "p": "2026-06",
                "uid": admin_perfil_id,
                "r": "PROFESOR",
            },
        )).fetchone()

        if existing_liq:
            print(f"  [WARN] Liquidacion ya existe, se omite.")
        else:
            liq = Liquidacion(
                tenant_id=tenant_id,
                cohorte_id=cohorte_id,
                periodo="2026-06",
                usuario_id=admin_perfil_id,
                rol="PROFESOR",
                comisiones=["A"],
                monto_base=Decimal("50000.00"),
                monto_plus=Decimal("10000.00"),
                total=Decimal("60000.00"),
                es_nexo=False,
                excluido_por_factura=False,
                estado="Abierta",
            )
            session.add(liq)
            await session.flush()
            print(f"  -> Liquidacion ID: {liq.id}")

        await session.commit()

        # ── Resumen ──
        print()
        print("=" * 60)
        print("[OK] SEED AMPLIADO COMPLETADO")
        print("=" * 60)
        print(f"  Tenant:            demo (ID: {tenant_id})")
        print(f"  Admin AuthUser ID: {admin_auth_user_id}")
        print(f"  Admin perfil ID:   {admin_perfil_id}")
        print(f"  Materia ID:        {materia_id}")
        print(f"  Cohorte ID:        {cohorte_id}")
        print(f"  Asignacion ID:     {asignacion_id}")
        print(f"  VersionPadron ID:  {version_id}")
        print()
        print("  Entradas de padrón:")
        for email, eid in entradas.items():
            print(f"    {email} -> {eid}")
        print()
        print("  Datos creados:")
        print("    - 1 VersionPadron activa")
        print("    - 4 EntradaPadron (alumno1-4@demo.com)")
        print("    - 1 UmbralMateria (60%)")
        print("    - 12 Calificaciones (4 alumnos x 3 actividades)")
        print("    - 12 FinalizacionActividad")
        print("    - 2 Comunicaciones (1 Pendiente, 1 Enviada)")
        print("    - 2 Avisos")
        print("    - 3 Tareas (variadas)")
        print("    - 3 SalarioBase")
        print("    - 1 SalarioPlus")
        print("    - 1 Liquidacion (2026-06, Abierta)")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
