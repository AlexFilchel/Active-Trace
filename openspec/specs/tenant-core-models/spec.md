## ADDED Requirements

### Requirement: Tenant root entity exists
The system SHALL persist a root `Tenant` entity representing one isolated institution. `Tenant` SHALL use an internal UUID identifier and lifecycle timestamps so future domain entities can reference it as the top-level ownership boundary.

#### Scenario: Creating a tenant root
- **WHEN** a new tenant is created in persistence
- **THEN** the record stores an internal UUID identifier
- **AND** the record stores `created_at` and `updated_at`
- **AND** the tenant can be referenced by future `tenant_id` foreign keys

### Requirement: Lifecycle fields are standardized for core models
The system SHALL define reusable ORM conventions for lifecycle fields. Root entities SHALL share `id`, `created_at`, `updated_at`, and `deleted_at`; tenant-owned entities SHALL additionally include `tenant_id` referencing `Tenant`.

#### Scenario: Tenant-owned model inherits the standard lifecycle
- **WHEN** a tenant-owned domain model is declared using the core conventions
- **THEN** it includes `id`, `tenant_id`, `created_at`, `updated_at`, and `deleted_at`
- **AND** `tenant_id` references an existing tenant

#### Scenario: Updated timestamp changes on mutation
- **WHEN** a persisted core model is modified and saved
- **THEN** `updated_at` is refreshed to the latest persistence timestamp
- **AND** `created_at` remains unchanged

### Requirement: Soft delete is the default deletion contract
The system MUST preserve records through soft delete instead of physical deletion for core domain models covered by the shared lifecycle conventions.

#### Scenario: Deleting a tenant-owned record performs a soft delete
- **WHEN** an application-layer delete operation is requested for a tenant-owned record
- **THEN** the row remains stored in the database
- **AND** `deleted_at` is set to a timestamp
- **AND** the record is considered deleted for default reads
