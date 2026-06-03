## ADDED Requirements

### Requirement: Baseline migration creates the tenant root
The system SHALL define an Alembic baseline revision `001_tenant` that creates the `tenant` table as the first domain schema object.

#### Scenario: Applying the baseline migration
- **WHEN** Alembic upgrades a fresh database to revision `001_tenant`
- **THEN** the database contains the `tenant` table
- **AND** the table includes the UUID/lifecycle fields required by the core model contract

### Requirement: Migration naming stays sequential and auditable
The system MUST use zero-padded sequential migration identifiers for schema revisions and create only one migration per schema change.

#### Scenario: First domain migration follows the convention
- **WHEN** the first domain migration for activia-trace is created
- **THEN** its revision label follows the `001_*` pattern
- **AND** it represents the tenant baseline as a single schema change unit

#### Scenario: Future migrations continue from the baseline
- **WHEN** later domain schema changes are introduced after the tenant baseline
- **THEN** each change is authored in its own subsequent sequential revision
- **AND** the baseline remains the audit starting point for the domain model
