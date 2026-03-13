# Feature Specification: Crypto Acceleration Layer

**Feature Branch**: `018-rust-crypto`
**Created**: 2026-02-25
**Status**: Draft
**Input**: Replace CPU-bound PII encryption internals with a high-performance compiled acceleration layer, maintaining full byte-level compatibility with existing encrypted data and transparent fallback behaviour.

---

## Clarifications

### Session 2026-02-25

- Q: Should the system emit an observable signal when the software fallback is active in place of the acceleration layer? → A: Log a single warning-level entry at application startup when the fallback is active.
- Q: Must blind-index normalisation apply Unicode form normalisation in addition to lowercase and whitespace stripping? → A: Yes — normalise to NFC (precomposed form) before hashing.
- Q: What is the maximum acceptable wall-clock time for a single PII field encryption or decryption operation? → A: Under 5 µs per operation.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Faster PII Read/Write for All Tenant Operations (Priority: P1)

When a tenant creates or updates a customer record, the system encrypts several PII fields (name, CUIT, address, phone). Today each of those operations incurs measurable CPU cost that accumulates under concurrent load. After this feature ships, those same operations complete significantly faster, increasing the number of requests the system can serve without degrading response times.

**Why this priority**: Every model with PII fields is affected on every read and write. This is the core motivation for the entire feature.

**Independent Test**: Load-test customer creation with 50 concurrent users. Measure throughput (requests/second) before and after deployment. Delivers value independently of any other user story.

**Acceptance Scenarios**:

1. **Given** a tenant with 100 customer records, **When** a background job reads and re-encrypts all records, **Then** the job completes in less than half the time it took before the acceleration layer was deployed.
2. **Given** a customer creation request with three PII fields, **When** the request is processed, **Then** the total time spent in encryption across all three fields is under 15 µs (3 × 5 µs ceiling), contributing negligible overhead to the overall API response time.
3. **Given** 1 000 sequential encrypt-decrypt cycles run against the same plaintext value, **When** the cycle completes, **Then** every decrypted value exactly matches the original input.

---

### User Story 2 — Existing Encrypted Data Remains Fully Accessible (Priority: P1)

Tenants have existing PII data that was encrypted before this feature was deployed. After deployment, all of that data must decrypt correctly without any migration, intervention, or re-encryption step.

**Why this priority**: Data loss or inaccessibility is a critical failure. Ranked P1 alongside throughput because it is a non-negotiable correctness requirement.

**Independent Test**: Take a snapshot of 20 real encrypted database values, deploy the acceleration layer, and verify each decrypts to its known plaintext. Fully verifiable without any UI or end-to-end flow.

**Acceptance Scenarios**:

1. **Given** encrypted PII data written before the acceleration layer was deployed, **When** the system reads that data after deployment, **Then** the decrypted value matches the original plaintext exactly.
2. **Given** a blind index computed before deployment for a customer's CUIT, **When** a search is performed after deployment using the same CUIT, **Then** the customer record is found (blind index values are identical).
3. **Given** the acceleration layer is present, **When** new data is written and then read back, **Then** the data roundtrips correctly regardless of which path handled the write and which handled the read.

---

### User Story 3 — Transparent Operation Without the Acceleration Layer (Priority: P2)

On development machines, CI pipelines, or platforms where the acceleration layer cannot be compiled or installed, all encryption and search operations must continue to work correctly using the existing implementation. No configuration change should be required.

**Why this priority**: Supports developer experience and deployment flexibility. Failure here does not affect production tenants but blocks developers and breaks CI.

**Independent Test**: Remove the acceleration layer from the environment and run the full automated test suite. All 2 200+ tests must pass without any code changes.

**Acceptance Scenarios**:

1. **Given** an environment where the acceleration layer is not installed, **When** the application starts, **Then** all PII field operations work correctly using the fallback implementation.
2. **Given** the acceleration layer is not installed, **When** the full test suite runs, **Then** zero tests fail due to missing crypto functionality.
3. **Given** the acceleration layer is uninstalled from a running system, **When** the application is restarted, **Then** no data loss or error occurs and all tenant operations resume normally.

---

### User Story 4 — Blind Index Searches Return Consistent Results (Priority: P2)

Operators and end-users search for customers by CUIT, name, or phone. These searches rely on blind indexes — deterministic hashes computed from the plaintext at write time. After deployment, search results must be identical to those before deployment.

**Why this priority**: Inconsistent search results would directly degrade user experience and could cause duplicate records or missed lookups.

**Independent Test**: Compute blind indexes for 50 representative values (CUITs, Spanish-accented names, mixed-case inputs) using both the old and new paths. Every pair must match.

**Acceptance Scenarios**:

1. **Given** a search for "García" and a search for "  GARCÍA  ", **When** both are executed, **Then** they return the same results (case and whitespace normalisation is consistent).
2. **Given** a blind index computed by the acceleration layer, **When** that index is compared to one computed by the software fallback for the same input, **Then** the values are identical.
3. **Given** Argentine PII data containing `ñ`, `á`, `é`, `ü`, and numeric CUITs, **When** blind indexes are computed and stored, **Then** searching by any of those values returns the correct records.

---

### Edge Cases

- What happens when a null value is passed to an encryption operation? → The system returns null without raising an error.
- What happens when an empty string is passed to an encryption operation? → The system returns an empty string without raising an error.
- What happens when a null value is passed to blind-index computation? → The system returns null without raising an error.
- How does the system handle an encryption key that is the wrong length? → The system raises a clear validation error immediately; no encryption attempt is made.
- How does the system handle data that has been tampered with (authentication tag mismatch)? → Decryption fails with a clear error; the system never silently returns corrupted plaintext.
- How does the system behave when the acceleration layer binary is present but corrupted? → The fallback activates as if the module were absent; no crash at application startup.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST encrypt PII string values using authenticated encryption with a random 96-bit nonce, producing output that includes the nonce, ciphertext, and authentication tag in a single base64-encoded blob.
- **FR-002**: The system MUST produce encrypted output that is byte-for-byte compatible with data encrypted by the previous implementation — any value encrypted by either path must be decryptable by the other.
- **FR-003**: The system MUST compute searchable blind indexes by normalising the input in the following order — (1) Unicode NFC normalisation, (2) lowercase, (3) strip leading/trailing whitespace — before hashing, ensuring lookups are consistent regardless of input source or character encoding form.
- **FR-004**: The system MUST reject an encryption or hashing key that is not exactly 32 bytes, returning a clear validation error before any cryptographic operation is attempted.
- **FR-005**: The system MUST return null for null inputs and an empty value for empty-string inputs to all three crypto operations, without raising an error.
- **FR-006**: The system MUST fall back transparently to the existing implementation when the acceleration layer is not installed — no configuration change required, no user-visible difference in behaviour.
- **FR-007**: The system MUST NOT require changes to any call site; all existing code that invokes encryption utilities continues to work without modification after deployment.
- **FR-008**: The acceleration layer MUST be available and functional inside the containerised deployment environment used for production.
- **FR-009**: The full automated test suite (≥ 2 200 tests) MUST pass with zero new failures in both accelerated and fallback modes.
- **FR-010**: When the application starts in fallback mode (acceleration layer absent or failed to load), the system MUST emit exactly one warning-level log entry identifying that the software fallback is active. No warning is emitted when the acceleration layer loads successfully.

### Key Entities

- **Plaintext PII value**: A string (potentially containing Unicode, Spanish-accented characters, or numeric CUITs) that must be protected at rest.
- **Encrypted blob**: A base64-encoded value stored in the database. Consists of a random nonce, the ciphertext, and an authentication tag. Must be stable across implementation versions.
- **Blind index**: A fixed-length hex string derived from a normalised PII value. Normalisation order: NFC → lowercase → strip whitespace. Stored in the database to enable exact-match searches without decryption. Must be identical whether computed by the acceleration layer or the fallback, and must be stable across data sources that may represent the same character in different Unicode encoding forms.
- **Encryption key**: A 32-byte secret used for symmetric-key encryption. Sourced from application configuration; never stored in the database.
- **HMAC key**: A separate 32-byte secret used for blind-index computation. Sourced from application configuration; never stored in the database.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: PII encryption and decryption operations complete in under 5 µs per operation (a 50-character plaintext, measured in the containerised deployment environment), representing at least a 5× improvement over the baseline of approximately 15 µs.
- **SC-002**: Every PII value encrypted before the upgrade decrypts correctly after the upgrade — zero data incompatibility across all existing records.
- **SC-003**: Blind index values computed after deployment are identical to those computed before deployment for the same inputs — zero search regressions.
- **SC-004**: Removing the acceleration layer produces no test failures and no change in observable behaviour — 100% fallback compatibility.
- **SC-005**: The production deployment image builds successfully with the acceleration layer installed and all crypto operations callable from within the containerised environment.
- **SC-006**: The full automated test suite passes with zero new failures in both the accelerated and fallback configurations.
- **SC-007**: Cross-path compatibility: encrypting 1 000 distinct Argentine PII strings with the acceleration layer and decrypting with the software fallback (and vice versa) produces zero mismatches.

---

## Assumptions

- All existing encrypted PII data in the database was produced by the current existing implementation. No legacy format variants exist.
- The primary data corpus consists of Argentine business data: 11-digit CUIT numbers, Spanish-accented names and addresses (`á`, `é`, `í`, `ó`, `ú`, `ñ`, `ü`). CJK and RTL scripts are not in scope.
- The acceleration layer is compiled once as part of the Docker image build; runtime or on-demand compilation is not required.
- The 32-byte encryption key and HMAC key are already present in the application's configuration. Key rotation is out of scope for this feature.
- Performance benchmarks are measured inside the Docker container environment, not on developer workstations.
- Property-based testing uses at least 500 randomly-generated Unicode strings to cover edge cases beyond the Argentine corpus.
