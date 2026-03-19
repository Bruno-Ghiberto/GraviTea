# Research: Producer Accounts (Spec-13)

**Generated**: 2026-03-19
**Source**: 13-specify.md domain facts, spec.md clarifications, blueprint cross-reference, existing codebase patterns

---

## Summary

No NEEDS CLARIFICATION markers exist in the spec or plan. All domain decisions
were resolved during the specify + clarify phases using the RAG pipeline, blueprint
documents, and codebase inspection. This file consolidates those decisions with
rationale for agent consumption.

---

## Decision 1: New App `apps.cuentas` (Not Extending `apps.acopio`)

**Decision**: Producer accounts live in a new, standalone Django app `apps.cuentas`
(label: `gravitea_cuentas`), not as models appended to `apps.acopio`.

**Rationale**:
- Constitution §III explicitly lists `cuentas` as a separate Acopio Vertical module
  with its own label, confirming the architectural intent.
- The producer current account is a commercial/financial domain concept, while
  `acopio` is a grain reception/logistics domain. Cross-cutting concerns (e.g.,
  future price fixation, LiquidacionPrimaria) will live in `cuentas`, not `acopio`.
- Separation enables independent testing, migration management, and future service
  extraction without touching the grain reception flow.

**Alternatives Considered**:
- Add ProducerAccount to `apps.acopio` → rejected (violates module boundary,
  acopio already covers 10+ models, constitution disagrees)
- Create under `apps.ventas` → rejected (wrong domain vertical)

---

## Decision 2: ADJUSTMENT as 9th Movement Type (Not 8)

**Decision**: AccountMovement supports 9 types including ADJUSTMENT, not 8.

**Rationale**:
- SRS-CC02 explicitly describes "Ajuste" as a correction mechanism in the spec.
- spec-12 GrainMovement precedent already uses ADJUSTMENT as a correction type.
- Immutable ledgers require ADJUSTMENT counter-entries (not edits) for error
  correction — this is the standard accounting pattern.
- ADJUSTMENT is supervisor-gated to prevent abuse.

**Clarification**: Recorded in spec.md: "Q: Should ADJUSTMENT be added as 9th
type? → A: Yes."

---

## Decision 3: Stored Running Balance (Not Always Derived)

**Decision**: ProducerAccount stores `grain_balance_kg`, `ars_balance`, `usd_balance`
as running totals updated atomically on each movement creation.

**Rationale**:
- Data Model v1.0 §6 specifies stored running balance as the canonical pattern.
  SRS-CC01 says "always derived" but the Data Model takes precedence per constitution.
- The same pattern is used by `GrainLot.total_kg` (spec-12) and is validated by
  the balance consistency management command (SC-005).
- Derived-only balance requires a full ledger SUM on every balance query — for
  producers with thousands of movements, this is unacceptable for SC-002 (interactive
  response times for 5,000 accounts).
- A management command (`check_account_balance`) detects stored/ledger drift as
  a safety net, matching the operational pattern of financial ERP systems.

**Alternatives Considered**:
- Always-derived via SUM aggregation → rejected (performance, contradicts Data Model)
- Materialized view → rejected (adds infrastructure complexity, YAGNI)

---

## Decision 4: Deferred Entities (FijacionRecord, CanjeOperation, liquidacion FK)

**Decision**: FijacionRecord, CanjeOperation, and AccountMovement.liquidacion FK are
deferred. LPG_SALE and FIJACION movement type entries exist in the enum for forward
compatibility but have no automated triggers in this spec.

**Rationale**:
- All three depend on `LiquidacionPrimaria` (Form 1116-C), which does not exist in
  the codebase. Implementing them now would require fabricating a dependency or
  building a stub that would need full rewrite later.
- spec.md Assumptions §5-6 explicitly document this deferral.
- The enum entries ensure database migrations do not need to be altered when spec-15
  (WSLPG / LiquidacionPrimaria) lands.

---

## Decision 5: Blind Index for CUIT (Not Asymmetric Encryption Search)

**Decision**: Producer CUIT stored as `EncryptedCharField` (AES-256-GCM ciphertext)
with `BlindIndexField` (HMAC-SHA256 deterministic hash) for equality search.

**Rationale**:
- Follows the existing `barcode_blind_idx` pattern in `Product` and `tax_id_hash`
  in `Supplier` — no new infrastructure needed.
- CUIT equality search is the primary search pattern; range queries on CUIT are
  nonsensical for tax IDs.
- HMAC-SHA256 with a secret key provides preimage resistance — CUIT cannot be
  brute-forced from the hash without the HMAC key.

**Critical Pattern**:
- `EncryptedCharField` auto-encrypts via `get_prep_value` and auto-decrypts via
  `from_db_value`. DO NOT call `encrypt_value()` manually — double-encryption bug.
- `compute_blind_index(plaintext)` in `apps/core/encryption/utils.py` computes
  the hash from plaintext. Must be called before save, not after.

---

## Decision 6: transaction.atomic() Wrapping in confirmar

**Decision**: The romaneo `confirmar` action (romaneo.py) is wrapped in a single
`transaction.atomic()` that encompasses romaneo.save(), create_deposit_from_romaneo(),
and create_ceg_deposit().

**Rationale**:
- The existing confirmar has no transaction wrapping, creating an atomicity bug:
  if `create_deposit_from_romaneo()` fails, the romaneo is already saved as CONFORME
  and the state machine is corrupt.
- Spec-13's CEG_DEPOSIT makes the race condition worse (3 writes: romaneo + grain
  lot + account). The outer transaction ensures all-or-nothing.
- Django supports nested `transaction.atomic()` via savepoints — the existing inner
  atomic in `create_deposit_from_romaneo()` remains safe.
- The storage_unit validation MUST move inside the atomic block to prevent partial
  commits.

**CONFORME Allowlist**: No change needed. Romaneo.save() allowlist already includes
all fields modified by confirmar.

---

## Decision 7: is_own_grain Defaults to False (ADR-020)

**Decision**: `is_own_grain` defaults to `False` in the confirmar action MVP.
CEG_DEPOSIT is only created when `not is_own_grain`.

**Rationale**:
- ADR-020 specifies own-grain bypasses the producer account system.
- The MVP does not yet have UI/logic for operators to declare own-grain purchases.
- Defaulting to `False` is safe and conservative — all grain is assumed third-party
  until proven otherwise.
- A future spec will add the own-grain determination logic.

---

## Decision 8: db_table Explicit Prefix

**Decision**: Both models use `db_table = "cuentas_produceraccount"` and
`db_table = "cuentas_accountmovement"` in Meta.

**Rationale**:
- Default Django behavior would produce `gravitea_cuentas_produceraccount` (very long).
- RLS policy SQL references the table name directly; a shorter prefix is easier
  to write and maintains consistency with `acopio_*` table naming.
- Explicit `db_table` is the established pattern in this codebase.
