## ADDED Requirements

### Requirement: Selección de comisión

El sistema SHALL permitir al PROFESOR seleccionar la comisión (materia + cohorte) a gestionar antes de mostrar cualquier vista de análisis o importación. La comisión seleccionada SHALL acotar todas las llamadas a backend con `comision_id`.

#### Scenario: El profesor selecciona una comisión

- **WHEN** el PROFESOR elige una comisión de la lista de comisiones disponibles
- **THEN** el sistema persiste `comision_id` en el contexto de la vista y habilita las pestañas de importación y análisis

#### Scenario: No hay comisión seleccionada

- **WHEN** el PROFESOR entra a `/comisiones` sin una comisión seleccionada
- **THEN** el sistema muestra un estado informativo solicitando seleccionar una comisión y NO realiza llamadas de análisis

### Requirement: Listado y selección de actividades

El sistema SHALL obtener las actividades de una comisión desde `GET /api/calificaciones/actividades?comision_id=` y permitir al PROFESOR seleccionar cuáles incluir en el análisis.

#### Scenario: Se listan las actividades detectadas

- **WHEN** se selecciona una comisión con actividades disponibles
- **THEN** el sistema muestra cada actividad con su nombre y un control de selección, todas deseleccionadas por defecto

#### Scenario: La comisión no tiene actividades

- **WHEN** la respuesta de actividades es una lista vacía
- **THEN** el sistema muestra un estado informativo "Sin actividades" y deshabilita el botón de importación

### Requirement: Importación de calificaciones con vista previa

El sistema SHALL permitir cargar un archivo de calificaciones del LMS junto con `comision_id` y las actividades seleccionadas mediante `POST /api/calificaciones/importar` (multipart), y mostrar una vista previa del resultado de la importación.

#### Scenario: Importación exitosa

- **WHEN** el PROFESOR carga un archivo válido con al menos una actividad seleccionada y confirma
- **THEN** el sistema envía la petición multipart con `file`, `comision_id` y `actividades[]`, y muestra la vista previa con el resumen de alumnos y actividades importadas

#### Scenario: Importación sin actividades seleccionadas

- **WHEN** el PROFESOR intenta importar sin seleccionar ninguna actividad
- **THEN** el sistema bloquea el envío y muestra un mensaje de validación

#### Scenario: La importación falla en el backend

- **WHEN** `POST /api/calificaciones/importar` responde con error
- **THEN** el sistema muestra un mensaje de error y no muestra la vista previa de éxito

### Requirement: Configuración de umbral de aprobación

El sistema SHALL leer el umbral vigente desde `GET /api/calificaciones/umbral?comision_id=` y permitir actualizarlo vía `PUT /api/calificaciones/umbral`. El valor por defecto SHALL ser 60% cuando no haya umbral configurado.

#### Scenario: Se muestra el umbral vigente

- **WHEN** se selecciona una comisión con umbral configurado en 70%
- **THEN** el control de umbral muestra 70%

#### Scenario: Se actualiza el umbral

- **WHEN** el PROFESOR cambia el umbral a 65% y confirma
- **THEN** el sistema envía `PUT /api/calificaciones/umbral` con `comision_id`, `umbral_pct` y `valores_aprobatorios[]`, y refleja el nuevo valor

#### Scenario: Umbral fuera de rango

- **WHEN** el PROFESOR ingresa un umbral menor a 0 o mayor a 100
- **THEN** el sistema bloquea la confirmación y muestra un mensaje de validación
