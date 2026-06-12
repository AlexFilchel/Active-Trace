from __future__ import annotations

from datetime import date
import hashlib
import hmac
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import decrypt_value, encrypt_value
from app.models import Carrera, Cohorte, Materia, Rol
from app.models.usuarios import Asignacion, Usuario
from app.repositories.auth import normalize_email
from app.repositories.estructura import CarreraRepository, CohorteRepository, MateriaRepository
from app.repositories.rbac import RbacRepository
from app.repositories.usuarios import AsignacionRepository, UsuarioRepository


class ConflictError(Exception):
    status_code = 409

    def __init__(self, detail: str = "Conflict."):
        self.detail = detail
        super().__init__(detail)


class NotFoundError(Exception):
    status_code = 404

    def __init__(self, detail: str = "Resource not found."):
        self.detail = detail
        super().__init__(detail)


class UsuarioService:
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str):
        self.session = session
        self.tenant_id = uuid.UUID(str(tenant_id)) if not isinstance(tenant_id, uuid.UUID) else tenant_id
        self._usuario_repo = UsuarioRepository(session=session, tenant_id=self.tenant_id)
        self._asignacion_repo = AsignacionRepository(session=session, tenant_id=self.tenant_id)
        self._rbac_repo = RbacRepository(session=session, tenant_id=self.tenant_id)
        self._carrera_repo = CarreraRepository(session=session, tenant_id=self.tenant_id)
        self._cohorte_repo = CohorteRepository(session=session, tenant_id=self.tenant_id)
        self._materia_repo = MateriaRepository(session=session, tenant_id=self.tenant_id)

    def _hash_email(self, email: str) -> str:
        normalized_email = normalize_email(email)
        secret = get_settings().secret_key.encode("utf-8")
        return hmac.new(secret, normalized_email.encode("utf-8"), hashlib.sha256).hexdigest()

    def _encrypt_optional(self, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        return encrypt_value(value)

    def _serialize_usuario(self, usuario: Usuario) -> dict[str, object]:
        return {
            "id": usuario.id,
            "tenant_id": usuario.tenant_id,
            "auth_user_id": usuario.auth_user_id,
            "nombre": usuario.nombre,
            "apellidos": usuario.apellidos,
            "email": decrypt_value(usuario.email_encrypted),
            "dni": decrypt_value(usuario.dni_encrypted) if usuario.dni_encrypted else None,
            "cuil": decrypt_value(usuario.cuil_encrypted) if usuario.cuil_encrypted else None,
            "cbu": decrypt_value(usuario.cbu_encrypted) if usuario.cbu_encrypted else None,
            "alias_cbu": decrypt_value(usuario.alias_cbu_encrypted) if usuario.alias_cbu_encrypted else None,
            "banco": usuario.banco,
            "regional": usuario.regional,
            "legajo": usuario.legajo,
            "legajo_profesional": usuario.legajo_profesional,
            "facturador": usuario.facturador,
            "estado": usuario.estado,
            "created_at": usuario.created_at,
            "updated_at": usuario.updated_at,
        }

    async def crear_usuario(
        self,
        *,
        nombre: str,
        apellidos: str,
        email: str,
        auth_user_id: uuid.UUID | None = None,
        dni: str | None = None,
        cuil: str | None = None,
        cbu: str | None = None,
        alias_cbu: str | None = None,
        banco: str | None = None,
        regional: str | None = None,
        legajo: str | None = None,
        legajo_profesional: str | None = None,
        facturador: bool = False,
        estado: str = "Activo",
    ) -> Usuario:
        email_hash = self._hash_email(email)
        if await self._usuario_repo.get_by_email_hash(email_hash) is not None:
            raise ConflictError("Ya existe un usuario con ese email.")

        try:
            return await self._usuario_repo.create(
                auth_user_id=auth_user_id,
                nombre=nombre,
                apellidos=apellidos,
                email_encrypted=encrypt_value(normalize_email(email)),
                email_hash=email_hash,
                dni_encrypted=self._encrypt_optional(dni),
                cuil_encrypted=self._encrypt_optional(cuil),
                cbu_encrypted=self._encrypt_optional(cbu),
                alias_cbu_encrypted=self._encrypt_optional(alias_cbu),
                banco=banco,
                regional=regional,
                legajo=legajo,
                legajo_profesional=legajo_profesional,
                facturador=facturador,
                estado=estado,
            )
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("No se pudo crear el usuario por conflicto de unicidad.") from exc

    async def listar_usuarios(self) -> list[Usuario]:
        return await self._usuario_repo.list()

    async def obtener_usuario(self, usuario_id: uuid.UUID) -> Usuario:
        usuario = await self._usuario_repo.get(usuario_id)
        if usuario is None:
            raise NotFoundError("Usuario no encontrado.")
        return usuario

    async def actualizar_usuario(self, usuario_id: uuid.UUID, **fields: object) -> Usuario:
        await self.obtener_usuario(usuario_id)
        update_fields = dict(fields)

        if "email" in update_fields:
            email = str(update_fields.pop("email"))
            email_hash = self._hash_email(email)
            existing = await self._usuario_repo.get_by_email_hash(email_hash)
            if existing is not None and existing.id != usuario_id:
                raise ConflictError("Ya existe un usuario con ese email.")
            update_fields["email_encrypted"] = encrypt_value(normalize_email(email))
            update_fields["email_hash"] = email_hash

        for input_field, encrypted_field in {
            "dni": "dni_encrypted",
            "cuil": "cuil_encrypted",
            "cbu": "cbu_encrypted",
            "alias_cbu": "alias_cbu_encrypted",
        }.items():
            if input_field in update_fields:
                update_fields[encrypted_field] = self._encrypt_optional(update_fields.pop(input_field))

        updated = await self._usuario_repo.update(usuario_id, **update_fields)
        if updated is None:
            raise NotFoundError("Usuario no encontrado.")
        return updated

    async def eliminar_usuario(self, usuario_id: uuid.UUID) -> None:
        deleted = await self._usuario_repo.soft_delete(usuario_id)
        if not deleted:
            raise NotFoundError("Usuario no encontrado.")

    async def serialize_usuario_response(self, usuario: Usuario) -> dict[str, object]:
        return self._serialize_usuario(usuario)

    async def serialize_usuarios_response(self, usuarios: list[Usuario]) -> list[dict[str, object]]:
        return [self._serialize_usuario(usuario) for usuario in usuarios]

    async def _ensure_usuario(self, usuario_id: uuid.UUID) -> Usuario:
        usuario = await self._usuario_repo.get(usuario_id)
        if usuario is None:
            raise NotFoundError("Usuario no encontrado.")
        return usuario

    async def _ensure_rol(self, rol_id: uuid.UUID) -> Rol:
        rol = await self._rbac_repo.get(rol_id)
        if rol is None:
            raise NotFoundError("Rol no encontrado.")
        return rol

    async def _ensure_carrera(self, carrera_id: uuid.UUID | None) -> Carrera | None:
        if carrera_id is None:
            return None
        carrera = await self._carrera_repo.get(carrera_id)
        if carrera is None:
            raise NotFoundError("Carrera no encontrada.")
        return carrera

    async def _ensure_cohorte(self, cohorte_id: uuid.UUID | None) -> Cohorte | None:
        if cohorte_id is None:
            return None
        cohorte = await self._cohorte_repo.get(cohorte_id)
        if cohorte is None:
            raise NotFoundError("Cohorte no encontrada.")
        return cohorte

    async def _ensure_materia(self, materia_id: uuid.UUID | None) -> Materia | None:
        if materia_id is None:
            return None
        materia = await self._materia_repo.get(materia_id)
        if materia is None:
            raise NotFoundError("Materia no encontrada.")
        return materia

    async def crear_asignacion(
        self,
        *,
        usuario_id: uuid.UUID,
        rol_id: uuid.UUID,
        desde: date,
        hasta: date | None = None,
        materia_id: uuid.UUID | None = None,
        carrera_id: uuid.UUID | None = None,
        cohorte_id: uuid.UUID | None = None,
        responsable_id: uuid.UUID | None = None,
        comisiones: list[str] | None = None,
    ) -> Asignacion:
        await self._ensure_usuario(usuario_id)
        await self._ensure_rol(rol_id)
        await self._ensure_materia(materia_id)
        await self._ensure_carrera(carrera_id)
        await self._ensure_cohorte(cohorte_id)
        if responsable_id is not None:
            await self._ensure_usuario(responsable_id)

        return await self._asignacion_repo.create(
            usuario_id=usuario_id,
            rol_id=rol_id,
            materia_id=materia_id,
            carrera_id=carrera_id,
            cohorte_id=cohorte_id,
            responsable_id=responsable_id,
            comisiones=comisiones or [],
            desde=desde,
            hasta=hasta,
        )

    async def listar_asignaciones(
        self,
        *,
        usuario_id: uuid.UUID | None = None,
        rol_id: uuid.UUID | None = None,
        materia_id: uuid.UUID | None = None,
        carrera_id: uuid.UUID | None = None,
        cohorte_id: uuid.UUID | None = None,
    ) -> list[Asignacion]:
        return await self._asignacion_repo.list(
            usuario_id=usuario_id,
            rol_id=rol_id,
            materia_id=materia_id,
            carrera_id=carrera_id,
            cohorte_id=cohorte_id,
        )

    async def obtener_asignacion(self, asignacion_id: uuid.UUID) -> Asignacion:
        asignacion = await self._asignacion_repo.get(asignacion_id)
        if asignacion is None:
            raise NotFoundError("Asignación no encontrada.")
        return asignacion

    async def actualizar_asignacion(self, asignacion_id: uuid.UUID, **fields: object) -> Asignacion:
        if "rol_id" in fields and fields["rol_id"] is not None:
            await self._ensure_rol(uuid.UUID(str(fields["rol_id"])))
        if "materia_id" in fields:
            await self._ensure_materia(uuid.UUID(str(fields["materia_id"])) if fields["materia_id"] is not None else None)
        if "carrera_id" in fields:
            await self._ensure_carrera(uuid.UUID(str(fields["carrera_id"])) if fields["carrera_id"] is not None else None)
        if "cohorte_id" in fields:
            await self._ensure_cohorte(uuid.UUID(str(fields["cohorte_id"])) if fields["cohorte_id"] is not None else None)
        if "responsable_id" in fields and fields["responsable_id"] is not None:
            await self._ensure_usuario(uuid.UUID(str(fields["responsable_id"])))

        updated = await self._asignacion_repo.update(asignacion_id, **fields)
        if updated is None:
            raise NotFoundError("Asignación no encontrada.")
        return updated

    async def eliminar_asignacion(self, asignacion_id: uuid.UUID) -> None:
        deleted = await self._asignacion_repo.soft_delete(asignacion_id)
        if not deleted:
            raise NotFoundError("Asignación no encontrada.")

    async def listar_asignaciones_vigentes_para_auth_user(self, auth_user_id: uuid.UUID) -> set[str]:
        return await self._rbac_repo.get_active_assignment_permissions_for_auth_user(auth_user_id=auth_user_id)
