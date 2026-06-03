## ADDED Requirements

### Requirement: Sensitive field encryption uses AES-256
The system SHALL provide a reusable utility for encrypting and decrypting sensitive model attributes at rest using AES-256 and the configured `ENCRYPTION_KEY`.

#### Scenario: Encryption round-trip succeeds
- **WHEN** application code encrypts a sensitive plaintext value and then decrypts the produced ciphertext with the configured key
- **THEN** the decrypted value matches the original plaintext

#### Scenario: Persisted representation is not plaintext
- **WHEN** the utility encrypts a sensitive plaintext value
- **THEN** the stored or returned ciphertext differs from the plaintext input
- **AND** the plaintext is not exposed as the persisted representation

### Requirement: Decryption fails safely
The system MUST fail safely when ciphertext is invalid or decrypted with the wrong key, without returning misleading plaintext data.

#### Scenario: Wrong key cannot recover plaintext
- **WHEN** ciphertext is decrypted with a different key than the one used for encryption
- **THEN** the operation fails with a controlled error
- **AND** no plaintext value is returned

#### Scenario: Invalid payload is rejected
- **WHEN** application code passes malformed encrypted payload data to the decrypt utility
- **THEN** the operation fails with a controlled error
- **AND** the failure path does not require exposing the sensitive plaintext input
