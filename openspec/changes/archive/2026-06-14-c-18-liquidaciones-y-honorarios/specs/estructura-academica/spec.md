## MODIFIED Requirements

### Requirement: Materia con categoría de Plus

La entidad `Materia` SHALL soportar un campo `categoria_plus` nullable que identifica el grupo de Plus salarial al que pertenece la materia.

#### Scenario: Materia con categoría asignada
- **WHEN** un COORDINADOR o ADMIN edita una materia y asigna `categoria_plus = "PROG"`
- **THEN** el sistema persiste la categoría; el módulo de liquidaciones la usa para calcular el Plus correspondiente

#### Scenario: Materia sin categoría no genera plus
- **WHEN** `categoria_plus` es NULL
- **THEN** la materia no aporta plus a ningún docente en el cálculo de liquidación

#### Scenario: Retrocompatibilidad
- **WHEN** un cliente consulta una materia existente que no tiene `categoria_plus`
- **THEN** el campo aparece como `null` en la respuesta sin romper ningún contrato existente
