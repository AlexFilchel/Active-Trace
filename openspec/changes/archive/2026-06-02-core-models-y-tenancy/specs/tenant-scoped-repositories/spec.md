## ADDED Requirements

### Requirement: Repository operations require tenant context
The system SHALL provide a repository base contract that requires explicit tenant context for tenant-owned entities. Repository operations MUST fail closed when tenant context is absent.

#### Scenario: Missing tenant context is rejected
- **WHEN** application code attempts to instantiate or execute a tenant-scoped repository operation without a tenant identifier
- **THEN** the operation is rejected before executing the query
- **AND** no unscoped database read or write occurs

### Requirement: Tenant scope is applied to all default queries
The system SHALL apply `tenant_id` filtering to every default repository query for tenant-owned entities.

#### Scenario: Cross-tenant reads are blocked by default
- **WHEN** tenant A queries a repository for tenant-owned records
- **THEN** only rows whose `tenant_id` belongs to tenant A are returned
- **AND** rows owned by tenant B are never returned

#### Scenario: Cross-tenant updates do not affect foreign rows
- **WHEN** tenant A attempts to update or delete a row owned by tenant B through the repository contract
- **THEN** the repository does not mutate the foreign row
- **AND** the operation reports not found or equivalent tenant-safe failure

### Requirement: Soft-deleted rows are excluded by default
The system MUST exclude rows with `deleted_at` set from normal repository reads unless the caller explicitly opts in to include deleted rows.

#### Scenario: Default list excludes soft-deleted rows
- **WHEN** a repository list or get operation runs without an explicit include-deleted flag
- **THEN** rows whose `deleted_at` is not null are excluded from the result

#### Scenario: Administrative read can opt in to deleted rows
- **WHEN** a repository operation explicitly requests deleted rows
- **THEN** the result may include rows whose `deleted_at` is set
- **AND** tenant scope still remains active
