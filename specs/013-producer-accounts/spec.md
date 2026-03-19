# Feature Specification: Producer Accounts (Cuentas Corrientes)

**Feature Branch**: `013-producer-accounts`
**Created**: 2026-03-19
**Status**: Draft
**Input**: Implement producer current accounts (cuentas corrientes) with dual-ledger grain/monetary tracking, immutable movement ledger, CEG_DEPOSIT trigger from romaneo, posicion consolidada, account statements, and encrypted CUIT blind index search.

## Clarifications

### Session 2026-03-19

- Q: Should ADJUSTMENT be added as a 9th movement type for corrections (following spec-12 GrainMovement precedent + SRS-CC02 "Ajuste")? → A: Yes — add ADJUSTMENT as 9th type with supervisor-only permission, consistent with spec-12 pattern.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic Account Creation on Grain Reception (Priority: P1)

An operator at the acopio plant confirms a romaneo (grain reception) for a producer. The system automatically creates a producer account (if one does not already exist for this combination of producer, plant, grain type, and campaign) and records a grain deposit entry. The producer's grain balance increases by the confirmed net weight. This happens seamlessly as part of the existing romaneo confirmation flow — no additional steps required from the operator.

**Why this priority**: This is the foundational event that creates accounts and populates the grain sub-ledger. Without this, no other account functionality can operate. Every producer interaction begins with grain delivery.

**Independent Test**: Confirm a romaneo and verify that a producer account exists with the correct grain balance. Can be demonstrated by creating a romaneo, advancing it to CONFORME, and checking the account API.

**Acceptance Scenarios**:

1. **Given** a romaneo for producer CUIT 20-12345678-9 delivering 10,000 kg of trigo in campaign 2025/26 at branch "Planta Norte", **When** the operator confirms the romaneo (CONFORME), **Then** a ProducerAccount is created for (CUIT, Planta Norte, trigo, 2025/26) with grain_balance_kg = 10,000.000 and ars_balance = 0.000
2. **Given** a ProducerAccount already exists for (CUIT, branch, grain, campaign), **When** a second romaneo for the same producer/branch/grain/campaign is confirmed with 5,000 kg, **Then** the existing account is reused and grain_balance_kg increases to 15,000.000
3. **Given** the acopiador purchased grain outright (own grain), **When** the romaneo is confirmed, **Then** no ProducerAccount or CEG_DEPOSIT movement is created (own grain bypasses the producer account system)
4. **Given** the romaneo confirmation is in progress, **When** the grain deposit creation fails mid-transaction, **Then** the entire operation rolls back — the romaneo does NOT become CONFORME and no partial records exist

---

### User Story 2 - View Account Balances and Movement History (Priority: P1)

A gestor comercial (commercial manager) looks up a producer's accounts to check their grain and monetary balances. They can filter by producer CUIT, grain type, campaign, and branch. For any account, they can view the complete movement history showing every transaction that affected the balance.

**Why this priority**: Read access to account balances is the most frequent operation after deposits. Operators, managers, and producers all need to see balances and transaction history. This is a prerequisite for account statements and consolidated views.

**Independent Test**: Query the accounts API with a producer CUIT filter and verify the correct accounts are returned with accurate balances. Navigate to a specific account's movements endpoint and verify the chronological ledger.

**Acceptance Scenarios**:

1. **Given** a producer has 3 accounts (trigo, soja, maiz) across 2 branches, **When** the gestor searches by producer CUIT, **Then** all 3 accounts are returned with their current grain and monetary balances
2. **Given** an account with 5 movements (3 CEG_DEPOSIT, 1 SERVICE_CHARGE, 1 RETIRO), **When** the gestor views the movement ledger, **Then** all 5 movements appear in chronological order with type, amount, and document reference
3. **Given** a producer CUIT that does not exist for the tenant, **When** the gestor searches, **Then** an empty result set is returned (not an error)
4. **Given** the movement ledger endpoint, **When** someone attempts to PATCH or DELETE a movement, **Then** the system returns HTTP 405 (append-only violation)

---

### User Story 3 - Record Manual Debit Entries (Priority: P2)

An operator creates manual debit entries against a producer's account for services rendered (storage fees, conditioning charges), cash withdrawals (retiros), or tax retention deductions. A supervisor can also create ADJUSTMENT entries to correct errors via counter-entries (e.g., reversing an incorrect deposit). Each entry includes the amount, a reference document number, and optional notes. The balance updates immediately.

**Why this priority**: Between automated grain deposits and the future settlement system (LPG), operators need to record service charges and cash movements. This enables day-to-day account management without waiting for the full settlement pipeline.

**Independent Test**: Create a SERVICE_CHARGE movement via API for an existing account and verify the ars_balance decreases by the charged amount.

**Acceptance Scenarios**:

1. **Given** a producer account with ars_balance = 50,000.00, **When** the operator creates a SERVICE_CHARGE of -5,000.00 with reference "FAC-2026-00123", **Then** ars_balance becomes 45,000.00 and the movement appears in the ledger
2. **Given** a producer account with ars_balance = 1,000.00, **When** the operator creates a RETIRO of -3,000.00, **Then** ars_balance becomes -2,000.00 (negative monetary balances are allowed — this is normal commercial practice)
3. **Given** the operator attempts to create a SERVICE_CHARGE with a positive amount, **When** the request is submitted, **Then** the system rejects it with a validation error (debit entries must be negative)
4. **Given** the operator attempts to create a movement for an account belonging to a different tenant, **When** the request is submitted, **Then** the system returns 404 (tenant isolation)
5. **Given** a CEG_DEPOSIT of 10,000 kg was recorded incorrectly (should have been 8,000 kg), **When** a supervisor creates an ADJUSTMENT of -2,000 kg with reference and notes explaining the correction, **Then** grain_balance_kg decreases by 2,000 and the correction is traceable in the ledger
6. **Given** a non-supervisor operator attempts to create an ADJUSTMENT movement, **When** the request is submitted, **Then** the system returns 403 (supervisor permission required)

---

### User Story 4 - Consolidated Position Across Plants (Priority: P2)

A manager views a producer's consolidated position — the aggregated grain and monetary balances across all plants (branches) of the acopiador for a given campaign. This cross-plant view is essential for understanding the total commercial relationship with a producer.

**Why this priority**: Multi-plant acopiadores need a single view of their relationship with each producer. This is a key differentiator from paper-based systems and is required before campaign close operations.

**Independent Test**: Create accounts for the same producer across 2+ branches, then query the posicion consolidada endpoint and verify the totals match the sum of individual accounts.

**Acceptance Scenarios**:

1. **Given** producer CUIT 20-12345678-9 has 3 accounts across 2 branches (trigo at branch A: 10,000 kg, trigo at branch B: 5,000 kg, soja at branch A: 8,000 kg), **When** the manager queries posicion consolidada for campaign 2025/26, **Then** the response shows total grain balance by grain type (trigo: 15,000, soja: 8,000) and per-branch breakdown
2. **Given** the producer has no accounts for the requested campaign, **When** posicion consolidada is queried, **Then** the response shows zero totals (not an error)

---

### User Story 5 - Account Statement Generation (Priority: P3)

A gestor comercial generates an account statement for a producer showing the opening balance, all movements within a date range, and the closing balance. The statement separates the kilos sub-ledger from the monetary sub-ledger. Statements are used for periodic reconciliation and can be shared with the producer.

**Why this priority**: Statements are important for transparency and reconciliation but are less frequent than balance queries. The data model and movement ledger must be in place first.

**Independent Test**: Generate a statement for an account with known movements across a date range and verify the opening balance, movement list, and closing balance are mathematically consistent.

**Acceptance Scenarios**:

1. **Given** an account with 10 movements spanning January to March 2026, **When** the gestor requests a statement for February 2026, **Then** the opening balance reflects the sum of all movements before February 1, the statement lists only February movements, and the closing balance equals opening + February movements
2. **Given** an account with no movements in the requested date range, **When** the statement is generated, **Then** the opening and closing balances are equal and the movements list is empty

---

### User Story 6 - Balance Consistency Verification (Priority: P3)

A system administrator runs a periodic consistency check to verify that stored account balances match the sum of all movements in the ledger. Any discrepancies are reported for investigation. This is a safety net for the stored-balance pattern.

**Why this priority**: While the system maintains balance consistency through atomic operations, a background verification provides an additional safety layer. This is a non-user-facing operational requirement.

**Independent Test**: Run the consistency check command on a set of accounts with known correct balances and verify it reports no discrepancies. Then manually corrupt a balance and verify the command detects it.

**Acceptance Scenarios**:

1. **Given** 100 accounts with correct balances, **When** the check command runs, **Then** it reports 0 discrepancies
2. **Given** an account where grain_balance_kg was manually set to an incorrect value, **When** the check command runs, **Then** it reports the account ID and the expected vs actual balance

---

### Edge Cases

- What happens when two concurrent romaneo confirmations for the same producer/branch/grain/campaign arrive simultaneously? The system must handle the get-or-create race condition using database-level locking to prevent duplicate account creation.
- What happens when a producer CUIT is invalid or malformed? The system validates CUIT format (11 digits, valid check digit) before creating or searching accounts.
- What happens when the encryption key is not configured? The system fails fast with a clear error message rather than storing plaintext CUITs.
- What happens when a CEG_DEPOSIT movement would result in a negative grain balance (should never happen for deposits, but defensive)? The system rejects the movement.
- What happens when the blind index key is rotated? All hash values must be recomputed for the new key. This is an operational concern documented but not automated in this spec.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST maintain one current account per combination of (tenant, producer CUIT, branch, grain type, campaign) with dual sub-ledgers: grain balance in kilograms and monetary balance in ARS/USD
- **FR-002**: System MUST record all account movements as immutable append-only ledger entries supporting 9 movement types: CEG_DEPOSIT, LPG_SALE, FIJACION, RETIRO, SERVICE_CHARGE, CANJE_GRAIN_DEBIT, CANJE_INPUT_CREDIT, RETENTION_DEDUCTION, ADJUSTMENT
- **FR-003**: System MUST automatically create a producer account and CEG_DEPOSIT movement when a romaneo is confirmed (CONFORME) for third-party grain, using the confirmed net weight as the deposit amount
- **FR-004**: System MUST skip producer account creation for own-grain romaneos (acopiador purchases) — own grain is a balance-sheet asset with no producer-facing account
- **FR-005**: System MUST provide manual entry capability for SERVICE_CHARGE, RETIRO, RETENTION_DEDUCTION, and ADJUSTMENT movements with mandatory reference document and negative amount validation for debit types. ADJUSTMENT movements require supervisor-level permission and can carry positive or negative grain and/or monetary deltas (used for error corrections via counter-entries per SRS-CC02)
- **FR-006**: System MUST compute a consolidated position (posicion consolidada) across all branches for a given producer and campaign as a real-time aggregation — never stored as a separate entity
- **FR-007**: System MUST generate account statements showing opening balance, chronological movement list, and closing balance, with kilos and monetary sub-ledgers presented separately
- **FR-008**: System MUST provide paginated list and detail endpoints for accounts with filtering by producer CUIT (blind index), grain type, campaign, branch, and active status
- **FR-009**: System MUST provide cursor-paginated movement ledger endpoints nested under accounts, with filtering by movement type and ordering by timestamp
- **FR-010**: System MUST store producer CUIT as encrypted ciphertext with a searchable blind index for equality lookups — plaintext CUIT returned in responses via transparent decryption
- **FR-011**: System MUST reject any attempt to update or delete existing account movements, returning appropriate error responses
- **FR-012**: System MUST ensure all account operations (romaneo confirmation, grain deposit, account credit) happen atomically within a single transaction — partial failures must roll back all changes
- **FR-013**: System MUST provide a balance consistency verification tool that compares stored balances against the sum of all movements for each account

### Key Entities

- **ProducerAccount**: A per-plant, per-grain-type, per-campaign account for a producer identified by encrypted CUIT. Carries running grain balance (kg), ARS balance, and USD balance. Composite uniqueness: (tenant, producer CUIT hash, branch, grain type, campaign).
- **AccountMovement**: An immutable ledger entry recording a single change to a producer account. Contains the movement type (one of 9 types including ADJUSTMENT for corrections), grain quantity delta, monetary amount deltas, source references (romaneo for deposits), document references, and operator provenance. Movements are append-only — corrections are made via ADJUSTMENT counter-entries (supervisor-only), never by editing or deleting.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Grain deposits are recorded within the romaneo confirmation flow with zero additional operator steps — the account is created and credited automatically
- **SC-002**: Account balance queries return results within acceptable interactive response times for tenants with up to 5,000 accounts
- **SC-003**: Consolidated position queries return results within acceptable response times for producers with accounts across up to 10 branches
- **SC-004**: 100% of account movements are traceable to their source event (romaneo, reference document, or operator) via the immutable ledger
- **SC-005**: Balance consistency verification confirms zero discrepancies between stored balances and ledger-derived totals under normal operation
- **SC-006**: Encrypted CUIT searches return correct results using the blind index with no false positives or negatives
- **SC-007**: Cross-tenant account isolation is enforced — a tenant can never access, view, or modify accounts belonging to another tenant
- **SC-008**: All 40+ automated tests pass covering models, immutability, endpoints, tenant isolation, blind index search, CEG_DEPOSIT integration, and balance consistency

## Assumptions

- Producer CUIT values on existing romaneo records are valid 11-digit Argentine tax identifiers. No data migration of existing romaneos is needed — accounts are created prospectively as new romaneos are confirmed.
- The own-grain flag defaults to False (third-party grain) for all romaneo confirmations in the MVP scope. A future spec may add a UI toggle or inference logic for own-grain purchases.
- Monetary balances can go negative (producers can owe the acopiador). Grain balances cannot go negative (cannot withdraw more grain than deposited).
- The FijacionRecord entity (price fixation) and its endpoints are deferred because they depend on LiquidacionPrimaria (Form 1116-C) which does not yet exist in the codebase.
- The liquidacion FK on account movements is deferred for the same reason. LPG_SALE and FIJACION movement types exist in the enum for forward compatibility but have no automated triggers in this spec.
- SISA retention calculation, WSLPG settlement, electronic invoice generation, and commission calculation are deferred to the spec that implements LiquidacionPrimaria.
- Account statements are delivered as structured data responses. PDF export and email delivery are deferred to a future spec.

## Dependencies

- **Depends on spec-10**: GrainType and CampanaConfig reference data (account scoping dimensions)
- **Depends on spec-11**: Romaneo model with CONFORME state machine, confirmed net weight, and producer CUIT fields
- **Depends on spec-12**: Grain deposit flow in the romaneo confirmation action — this spec extends the same integration point
- **Blocks spec-15**: WSLPG integration (LiquidacionPrimaria) will add the deferred liquidacion FK and FijacionRecord
- **Blocks spec-14**: Agronomia adaptation may reference producer accounts for input invoicing
