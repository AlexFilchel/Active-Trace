## ADDED Requirements

### Requirement: Vista de alumnos atrasados

El sistema SHALL mostrar los alumnos atrasados de la comisión obtenidos desde `GET /api/atrasados?comision_id=`. Un alumno atrasado es el que tiene actividades faltantes o nota por debajo del umbral configurado.

#### Scenario: Se listan los alumnos atrasados

- **WHEN** la comisión tiene alumnos atrasados
- **THEN** el sistema muestra una tabla con cada alumno y el motivo del atraso

#### Scenario: No hay alumnos atrasados

- **WHEN** la respuesta de atrasados es una lista vacía
- **THEN** el sistema muestra un estado informativo "Sin alumnos atrasados"

### Requirement: Ranking de actividades aprobadas

El sistema SHALL mostrar el ranking obtenido desde `GET /api/analisis/ranking?comision_id=`, ordenado por cantidad de actividades aprobadas por alumno.

#### Scenario: Se muestra el ranking ordenado

- **WHEN** la comisión tiene alumnos con actividades aprobadas
- **THEN** el sistema muestra una tabla ordenada de mayor a menor cantidad de actividades aprobadas

#### Scenario: Ranking vacío

- **WHEN** ningún alumno tiene actividades aprobadas
- **THEN** el sistema muestra un estado informativo y no renderiza la tabla

### Requirement: Notas finales agrupadas

El sistema SHALL mostrar las notas finales por alumno obtenidas desde `GET /api/calificaciones/notas-finales?comision_id=`.

#### Scenario: Se muestran las notas finales

- **WHEN** la comisión tiene notas finales calculadas
- **THEN** el sistema muestra una tabla con cada alumno y su nota final

### Requirement: Reporte rápido por comisión

El sistema SHALL mostrar el reporte rápido obtenido desde `GET /api/analisis/reporte-rapido?comision_id=`, con un estado informativo cuando no hay datos o no se seleccionaron actividades.

#### Scenario: Se muestra el reporte con métricas

- **WHEN** la comisión tiene datos de análisis
- **THEN** el sistema muestra las métricas clave del reporte (actividades, aprobaciones, tendencias)

#### Scenario: Reporte sin datos

- **WHEN** el reporte rápido indica ausencia de datos
- **THEN** el sistema muestra el estado informativo correspondiente

### Requirement: Entregas sin corregir con exportación

El sistema SHALL mostrar las posibles entregas sin corregir desde `GET /api/analisis/entregas-sin-corregir?comision_id=` y permitir exportarlas a un archivo descargable.

#### Scenario: Se listan las entregas sin corregir

- **WHEN** la comisión tiene entregas detectadas como pendientes de corrección
- **THEN** el sistema muestra la tabla por alumno y actividad, y habilita el botón de exportación

#### Scenario: Exportar el listado

- **WHEN** el PROFESOR hace clic en exportar con entregas presentes
- **THEN** el sistema genera la descarga del archivo con el listado de entregas sin corregir

#### Scenario: No hay entregas sin corregir

- **WHEN** la respuesta es una lista vacía
- **THEN** el sistema muestra un estado informativo y deshabilita la exportación

### Requirement: Monitor de seguimiento de la comisión

El sistema SHALL ofrecer una vista filtrable del estado de actividades de los alumnos de la comisión para tutor/profesor, permitiendo acotar por alumno y por actividad mínima cumplida.

#### Scenario: Se filtra por alumno

- **WHEN** el PROFESOR escribe un término de búsqueda de alumno
- **THEN** la vista muestra solo los alumnos cuyo nombre o correo coincide con el término

#### Scenario: Se filtra por actividad mínima cumplida

- **WHEN** el PROFESOR establece un mínimo de actividades cumplidas
- **THEN** la vista muestra solo los alumnos que alcanzan ese mínimo
