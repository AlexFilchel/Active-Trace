## Verification Report

**Change**: analisis-atrasados-reportes
**Version**: N/A

---

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 20 |
| Tasks complete | 20 |
| Tasks incomplete | 0 |

All tasks in `tasks.md` are marked complete.

---

### Build & Tests Execution

**Build**: ➖ Skipped
```text
No `openspec/config.yaml` verify.build_command found.
AGENTS.md hard rule forbids automatic build/compile without explicit user request.
```

**Tests**: ✅ Passed
```text
Command: pytest tests/test_analisis_tdd.py tests/test_calificaciones_migration_tdd.py -q
Result: 22 passed, 0 failed, 0 skipped
```

**OpenSpec validation**: ✅ Passed
```json
{
  "items": [
    {
      "id": "analisis-atrasados-reportes",
      "type": "change",
      "valid": true,
      "issues": [],
      "durationMs": 3
    }
  ],
  "summary": {
    "totals": {
      "items": 1,
      "passed": 1,
      "failed": 0
    },
    "byType": {
      "change": {
        "items": 1,
        "passed": 1,
        "failed": 0
      }
    }
  },
  "version": "1.0"
}
```

**Coverage**: ➖ Not configured

---

### Spec Compliance Matrix

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Consultar alumnos atrasados | Alumno con actividad faltante aparece como atrasado | `backend/tests/test_analisis_tdd.py > test_service_detects_atrasados_for_missing_activity_and_threshold` | ✅ COMPLIANT |
| Consultar alumnos atrasados | Alumno con nota inferior al umbral aparece como atrasado | `backend/tests/test_analisis_tdd.py > test_service_detects_atrasados_for_missing_activity_and_threshold` | ✅ COMPLIANT |
| Consultar alumnos atrasados | Usuario sin permiso no accede a atrasados | `backend/tests/test_analisis_tdd.py > test_analisis_endpoints_require_permission_fail_closed` | ✅ COMPLIANT |
| Consultar alumnos atrasados | Tenant isolation en consulta de atrasados | `backend/tests/test_analisis_tdd.py > test_repository_filters_tenant_and_assignment_scope` | ✅ COMPLIANT |
| Consultar ranking de actividades aprobadas | Alumno sin aprobadas queda excluido | `backend/tests/test_analisis_tdd.py > test_service_ranking_excludes_students_without_approved_activities` | ✅ COMPLIANT |
| Consultar ranking de actividades aprobadas | Ranking ordena por aprobadas descendente | `backend/tests/test_analisis_tdd.py > test_service_ranking_excludes_students_without_approved_activities` | ✅ COMPLIANT |
| Consultar reportes rápidos por materia | Materia sin datos importados retorna estado informativo | `backend/tests/test_analisis_tdd.py > test_service_summary_reports_sin_datos_and_sin_actividades` | ✅ COMPLIANT |
| Consultar reportes rápidos por materia | Materia con datos retorna métricas consolidadas | `backend/tests/test_analisis_tdd.py > test_service_notas_finales_and_summary_handle_edge_cases` | ✅ COMPLIANT |
| Consultar notas finales agrupadas | Nota final agrupada por alumno | `backend/tests/test_analisis_tdd.py > test_service_notas_finales_and_summary_handle_edge_cases` | ✅ COMPLIANT |
| Consultar notas finales agrupadas | Alumno sin notas numéricas calculables queda marcado sin nota final | `backend/tests/test_analisis_tdd.py > test_service_notas_finales_and_summary_handle_edge_cases` | ✅ COMPLIANT |
| Consultar monitores de seguimiento | Profesor ve solo alumnos de su alcance | `backend/tests/test_analisis_tdd.py > test_service_monitor_limits_profesor_to_authorized_scope` | ✅ COMPLIANT |
| Consultar monitores de seguimiento | Coordinación filtra por rango de fechas | `backend/tests/test_analisis_tdd.py > test_service_monitor_filters_and_export_requires_finalized_textual_signal` | ✅ COMPLIANT |
| Consultar monitores de seguimiento | Filtros combinados reducen resultados | `backend/tests/test_analisis_tdd.py > test_service_monitor_filters_and_export_requires_finalized_textual_signal` | ✅ COMPLIANT |
| Exportar TPs sin corregir | Export incluye entrega textual finalizada sin calificación | `backend/tests/test_analisis_tdd.py > test_service_monitor_filters_and_export_requires_finalized_textual_signal` | ✅ COMPLIANT |
| Exportar TPs sin corregir | Export excluye actividad numérica sin nota | `backend/tests/test_analisis_tdd.py > test_service_monitor_filters_and_export_requires_finalized_textual_signal` | ✅ COMPLIANT |
| Exportar TPs sin corregir | Export sin permiso retorna 403 | `backend/tests/test_analisis_tdd.py > test_export_endpoint_requires_permission_fail_closed` | ✅ COMPLIANT |

**Compliance summary**: 16/16 scenarios compliant

---

### Correctness (Static — Structural Evidence)
| Requirement | Status | Notes |
|------------|--------|-------|
| Scope fail-closed | ✅ Implemented | `services.py:72-96` corta sin perfil/asignaciones; `repositories.py:103-123` devuelve `literal(False)` para scope vacío. |
| Tenant scoping / RBAC | ✅ Implemented | Router usa `require_permission("atrasados:ver")`; service toma `tenant_id` desde JWT; repository filtra `tenant_id` en todos los datasets. |
| Boundaries router → service → repository | ✅ Implemented | Router solo valida/inyecta; service compone reglas; repository concentra SQL. |
| RN-06 atrasados | ✅ Implemented | Motivos `actividad_faltante` y `nota_bajo_umbral` calculados en `_load_metrics()`. |
| RN-07 / RN-08 export | ✅ Implemented | `export_tps_sin_corregir()` cruza `FinalizacionActividad` persistida con ausencia de calificación y excluye numéricas / ya calificadas. |
| RN-09 ranking | ✅ Implemented | `list_ranking()` excluye `aprobadas_count < 1` y ordena estable. |
| Migración/modelo | ✅ Implemented | Modelo `FinalizacionActividad` tenant-scoped, exportado en `models.__init__`, migración `008` crea tabla/índices/unique y downgrade limpio. |

---

### Coherence (Design)
| Decision | Followed? | Notes |
|----------|-----------|-------|
| Módulo nuevo `analisis-atrasados-reportes` | ✅ Yes | Implementado en `backend/app/analisis/`. |
| Services calculan reglas; repositories preparan datasets | ✅ Yes | No SQL en `services.py`; joins/filtros quedan en `repositories.py`. |
| Atrasado derivado en tiempo de consulta | ✅ Yes | Estado de atraso no se persiste. |
| Export reutiliza caso RN-07/RN-08 | ✅ Yes | Ahora usa señal persistida `finalizacion_actividad` como fuente real de finalización. |
| No agregar tablas salvo necesidad explícita | ⚠️ Deviated | Se agregó tabla `finalizacion_actividad`; desviación justificada para cerrar RN-07 correctamente. |

---

### Issues Found

**CRITICAL** (must fix before archive):
- None.

**WARNING** (should fix):
- `proposal.md` y `design.md` decían “sin nuevas tablas/migraciones” como plan inicial; hoy quedó una desviación documentable, no bloqueo funcional.

**SUGGESTION** (nice to have):
- Agregar un test HTTP end-to-end explícito de tenant isolation sobre `/api/analisis/atrasados` para reforzar evidencia runtime, aunque repository/service ya cubren el leak previo.

---

### Verdict
PASS WITH WARNINGS

La implementación ahora satisface RN-07/RN-08/RN-09, mantiene tenant scope y permisos, pasa tests relevantes y valida en OpenSpec. Está lista para continuar con la siguiente instrucción del usuario; no requiere más implementación antes de seguir, pero todavía no se archiva en esta fase.
