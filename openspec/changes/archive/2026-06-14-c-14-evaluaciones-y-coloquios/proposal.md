# Proposal: C-14 Evaluaciones y Coloquios

## Why

La Épica 7 (Coloquios) y el flujo FL-07 exigen gestionar evaluaciones orales finales de punta a punta: una coordinación crea una convocatoria de coloquio (materia, instancia, días y cupos), importa el padrón de alumnos habilitados, y los alumnos reservan su turno en un día con cupo disponible. Hoy el dominio de Evaluación (E14: `Evaluacion`, `ReservaEvaluacion`, `ResultadoEvaluacion`) no existe en el modelo: no hay tablas, ni servicios, ni endpoints. Sin esto no se puede convocar a coloquio, controlar cupos, ni consolidar resultados.

El RBAC ya trae `evaluacion:reservar_instancia` para el rol ALUMNO, pero **no existe ningún permiso para que COORDINADOR/ADMIN gestionen convocatorias**. Esa es la brecha principal a cerrar en este change.

## What Changes

- **Modelos** (`E14`): `Evaluacion` (convocatoria: materia, cohorte, tipo, instancia, dias_disponibles, cupos por día), `ReservaEvaluacion` (turno reservado por un alumno con estado Activa/Cancelada), `ResultadoEvaluacion` (nota final consolidada por alumno).
- **Convocatoria de coloquio** (F7.3): crear convocatoria definiendo materia, instancia, días y cupos. La operación genera los turnos reservables con su cupo.
- **Importar alumnos a convocatoria** (F7.2): cargar/actualizar el padrón de candidatos habilitados de una convocatoria.
- **Listado de convocatorias** (F7.4): vista tabular con métricas operativas (materia, instancia, días, convocados, reservas activas, cupos libres).
- **Panel de métricas** (F7.1): total de convocados, instancias activas, reservas activas, notas registradas.
- **Administración global** (F7.5): gestión de convocatorias (alta/edición/cierre), registro académico consolidado de resultados, agenda de reservas activas.
- **Reserva de turno por ALUMNO** (FL-07 / F7): el alumno habilitado ve la convocatoria y reserva un día con cupo; la reserva descuenta cupo; sin cupo se rechaza; puede cancelar (estado Cancelada libera cupo).
- **Endpoints** `/api/coloquios/*`: gestión bajo permiso nuevo `coloquios:gestionar` (COORDINADOR/ADMIN); reserva bajo `evaluacion:reservar_instancia` (ALUMNO).
- **Migración 011**: tablas `evaluacion`, `reserva_evaluacion`, `resultado_evaluacion` + seed del permiso `coloquios:gestionar` para COORDINADOR y ADMIN.
- **Auditoría**: cada alta/edición/cierre de convocatoria y cada reserva/cancelación emite `AuditLog`.

## Capabilities

- `evaluaciones-y-coloquios`: gestión de convocatorias de evaluación oral, importación de candidatos, reserva de turnos con control de cupo, métricas operativas y consolidación de resultados.

## Impact

- **Dominio nuevo**: modelos E14 (no toca dominios existentes).
- **RBAC**: agrega el permiso `coloquios:gestionar` (no existía) y lo asigna a COORDINADOR/ADMIN; reutiliza `evaluacion:reservar_instancia` ya existente para ALUMNO.
- **Migración**: `011_evaluaciones_coloquios` sobre el head actual `010_encuentros_guardias`.
- **Governance**: MEDIO (lógica de dominio; control de cupos es regla de negocio sensible, requiere checkpoints).
- **Dependencias**: C-07 usuarios-y-asignaciones (COMPLETO) — usa `Usuario`, `Materia`, `Cohorte`.
