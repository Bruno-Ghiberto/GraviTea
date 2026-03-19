---
spec: "013"
name: "Producer Accounts"
type: Implementation
branch: 013-producer-accounts
created: 2026-03-19
depends_on: [spec-10, spec-11, spec-12]
blocks: [spec-14, spec-15]
deliverable: "backend/apps/cuentas/ producer account models, dual-ledger movements, account APIs"
qdrant_collections: [acopio_research]
agents: [A1, A2, A3, A4]
---

# Spec-13: Producer Accounts -- Specification Context

## Feature Description

Implement the producer current account (cuenta corriente de productores) module
for the acopio operation. This spec creates a **new** Django app
`backend/apps/cuentas/` (label: `gravitea_cuentas`) with the following
deliverables:

1. **ProducerAccount model** -- dual-ledger per-producer, per-branch,
   per-grain-type, per-campaign account tracking both **grain balance in kg**
   and **monetary balance in ARS/USD**. Composite identity:
   `(tenant, producer_cuit, branch, grain_type, campaign)`.
2. **AccountMovement model** -- immutable append-only ledger recording all
   account entries. 8 movement types: CEG_DEPOSIT, LPG_SALE, FIJACION, RETIRO,
   SERVICE_CHARGE, CANJE_GRAIN_DEBIT, CANJE_INPUT_CREDIT, RETENTION_DEDUCTION.
   Same immutability pattern as `StockMovement` (inventario), `GrainMovement`
   (acopio), and `MermaCalculation` (acopio). ADR-008 mandates append-only.
3. **CEG_DEPOSIT integration** -- when a romaneo transitions to CONFORME,
   the system auto-creates (or finds) a ProducerAccount and inserts a
   CEG_DEPOSIT movement with `quantity_kg = romaneo.peso_neto_conforme_kg`.
   This extends the spec-12 confirmar flow.
4. **Manual movement entry** -- API endpoints for creating SERVICE_CHARGE,
   RETIRO, and RETENTION_DEDUCTION movements (operator-initiated entries).
5. **Posicion Consolidada** -- derived view (ADR-013) aggregating a producer's
   balances across all branches. Computed on demand via SQL, never stored.
6. **Account statement generation** -- kilos and pesos statement per producer
   filterable by grain type and campaign (SRS-CC03).
7. **Blind index search** -- `producer_cuit` uses HMAC-SHA256 blind index
   for equality search (same pattern as `barcode_hash` in inventario).
8. **DRF serializers and viewsets** implementing REST API Design v1.0 Section 9
   -- accounts CRUD, movements ledger, posicion consolidada, manual entries.
9. **Test suite** covering models, immutability enforcement, running balance
   updates, CEG_DEPOSIT trigger, tenant isolation, blind index search, and
   API endpoints.

This builds directly on:
- **Spec-10** reference data: GrainType, CampanaConfig (account scoping dimensions)
- **Spec-11** romaneo lifecycle: Romaneo (CONFORME triggers CEG_DEPOSIT)
- **Spec-12** storage: GrainMovement DEPOSIT (spec-12 deposits grain into
  storage; spec-13 credits the producer's account in parallel)

---

## Current State

### What Exists (from spec-10 + spec-11 + spec-12)

- `backend/apps/acopio/` -- Django app with models: GrainType, CampanaConfig,
  ToleranceTable, MermaTable, Romaneo, QualityAnalysis, MermaCalculation,
  StorageUnit, GrainLot, GrainMovement.
- `backend/apps/acopio/models/romaneo.py` -- `Romaneo` (TenantBound) with
  6-state state machine. At CONFORME, the spec-12 flow creates a GrainMovement
  DEPOSIT. Spec-13 extends this to also create an AccountMovement CEG_DEPOSIT.
  Romaneo carries `producer_cuit` (CharField, max_length=13) -- the producer
  identity key for account lookup/creation.
- `backend/apps/acopio/views/romaneo.py` -- `RomaneoViewSet` with `@action
  confirm` endpoint. This is the integration point for the CEG_DEPOSIT trigger.
- `backend/apps/core/models/mixins.py` -- `TenantBoundModel` (abstract base).
- `backend/apps/core/managers/tenant_bound.py` -- `TenantBoundManager` with
  fail-closed tenant filtering; `AllObjectsManager`.
- `backend/apps/core/encryption/` -- AES-256-GCM encryption utilities and
  HMAC-SHA256 blind index for searchable encrypted fields.
- `backend/apps/inventario/models.py` -- `StockMovement` demonstrates the
  immutable ledger pattern; `Product` demonstrates blind index search via
  `barcode_encrypted` / `barcode_hash`.
- `backend/apps/core/models/branch.py` -- `Branch` model (plant locations).

### What Needs Creating

- **New Django app**: `backend/apps/cuentas/` with full app boilerplate:
  `__init__.py`, `apps.py`, `admin.py`, `urls.py`.
- `backend/apps/cuentas/models/__init__.py` -- re-export all models.
- `backend/apps/cuentas/models/producer_account.py` -- ProducerAccount model.
- `backend/apps/cuentas/models/account_movement.py` -- AccountMovement model.
- `backend/apps/cuentas/services/accounts.py` -- Account creation, CEG_DEPOSIT
  trigger, balance update, posicion consolidada computation.
- `backend/apps/cuentas/services/statements.py` -- Account statement
  generation service.
- `backend/apps/cuentas/serializers/accounts.py` -- ProducerAccount,
  AccountMovement serializers.
- `backend/apps/cuentas/views/accounts.py` -- ProducerAccountViewSet,
  AccountMovementViewSet, PosicionConsolidadaView.
- `backend/apps/cuentas/urls.py` -- DRF router registration.
- `backend/database/sql/cuentas_rls.sql` -- RLS policies for new tables.
- Database migration `0001_producer_accounts.py`.
- Updated `backend/gravitea/settings/base.py` -- register `gravitea_cuentas`
  in INSTALLED_APPS.
- Updated `backend/gravitea/urls.py` -- mount `/api/v1/cuentas/` routes.
- Updated `backend/apps/acopio/views/romaneo.py` -- extend confirmar action
  to trigger CEG_DEPOSIT.
- Test files: `backend/tests/cuentas/` directory with model, API, service,
  and integration tests.

---

## Research Inputs

### RAG Queries (run these FIRST -- do NOT read full research files)

```bash
.venv/bin/python scripts/qdrant/qdrant_batch_search.py \
    -q "producer current account movements dual ledger kilos pesos" \
    -q "cuenta corriente kilos pesos dual ledger grain balance" \
    -q "producer account transaction types entry exit service deduction retention" \
    -q "producer account statement extracto running balance opening closing" \
    -q "canje grain barter supplies input invoice compensation" \
    -q "grain pricing contracts a fijar fijacion price fixing" \
    -q "producer account ERP data model design dual ledger" \
    -q "SISA retention tier IVA ganancias withholding producer" \
    -o Docs/RAG_results/spec-13 -l 5
```

### Source Documents (for reference only -- prefer RAG)

| Doc | Path | Relevant Sections |
|-----|------|-------------------|
| Research 2.3 | `Docs/Researches/Markdown/2.3 Producer Current Accounts (Cuentas Corrientes de Productores).md` | Executive Summary (dual-ledger), Transaction Type Summary, Canje Operations, Account Statements, ERP Design Considerations |
| Research 2.4 | `Docs/Researches/Markdown/2.4 Grain Pricing, Contracts, and Market Mechanisms.md` | Canje (Barter), Price fixing (fijacion), Contract types |
| Research 7.1 | `Docs/Researches/Markdown/7.1 Chart of Accounts for Acopio Operations.md` | Section 5.3 (Productores Cuentas Corrientes as central account) |
| Research 7.3 | `Docs/Researches/Markdown/7.3 Withholding Tax Calculations for Grain Operations.md` | SISA retention tiers, IVA/Ganancias rates |

### Blueprint References

| Doc | Path | Relevant Sections |
|-----|------|-------------------|
| Data Model v1.0 | `Docs/Project Blueprint/Data Model & Domain Model.md` | Section 6 (Producer Accounts -- ProducerAccount, AccountMovement, FijacionRecord field definitions), Section 8.4 (CanjeOperation), Section 10 (Cross-Module Links FK table) |
| REST API Design v1.0 | `Docs/Project Blueprint/REST API Design.md` | Section 9 (Accounts API -- 9.1-9.7: accounts, movements, posicion-consolidada, fijaciones) |
| HLD v1.0 | `Docs/Project Blueprint/High-Level Design (HLD).md` | Section 5.4 (apps/cuentas owned entities, ADR refs), Section 9.1 (Romaneo flow CEG_DEPOSIT trigger) |
| ADR v1.0 | `Docs/Project Blueprint/Architecture Decision Records (ADR).md` | ADR-006 (Ironclad Lineage), ADR-008 (Append-Only Ledger), ADR-009 (Dual Inventory), ADR-013 (Posicion Consolidada as Derived View), ADR-020 (Own Grain vs Third-Party Accounting), ADR-034 (Provenance Fields) |
| SRS v1.0 | `Docs/Project Blueprint/Software Requirements Specification (SRS).md` | SRS-CC01 (Account Structure), SRS-CC02 (Debit/Credit Entries), SRS-CC03 (Account Statement), SRS-CC07 (Commission Calculation) |

### Critical Domain Facts

#### Dual-Ledger Architecture (Research 2.3)

The *cuenta corriente del productor* is a **dual-ledger system** tracking two
independent sub-ledgers simultaneously:

1. **Cuenta corriente en kilos** -- physical grain balance in kg. Updated by:
   grain entries (CEG), exits (sales/LPG, retiros, transfers), merma deductions.
2. **Cuenta corriente en dinero** -- monetary balance in ARS (and optionally
   USD). Updated by: LPG proceeds, service invoices, advances, retentions.

Grain enters the system valued in physical units at zero monetary value (or
"a fijar"). Monetary value is crystallized only at the moment of sale or
price-fixing (fijacion).

#### Transaction Type Summary (Research 2.3, ERP Design Considerations)

| Transaction | Kilos Effect | Pesos Effect | Document |
|-------------|-------------|-------------|----------|
| Grain reception (CEG_DEPOSIT) | + Net kilos | -- | CEG |
| Sale (LPG_SALE) | - Kilos sold | + Net proceeds | LPG |
| Price fixing (FIJACION) | - Kilos fixed | + Fixed price x kilos | LPG |
| Retiro (RETIRO) | -- | - Cash withdrawal | Cert. Retiro |
| Service charge (SERVICE_CHARGE) | -- | - Service fee | Factura Servicios |
| Almacenaje | -- | - Storage charge | LPG or Factura |
| Commission | -- | - Commission amount | LPG |
| Tax retentions (RETENTION_DEDUCTION) | -- | - Retention amounts | LPG + F.2005 |
| Canje grain (CANJE_GRAIN_DEBIT) | - Kilos delivered | + LPG amount | LPG |
| Canje input (CANJE_INPUT_CREDIT) | -- | - Input invoice | Factura compra |

#### Account per (CUIT x Branch x GrainType x Campaign) (Data Model 6.1)

Each ProducerAccount is scoped to a single combination of producer CUIT,
branch (plant), grain type, and campaign. A producer with soja and trigo at
two plants in campaign 2024/25 has **4 separate accounts**.

Composite uniqueness: `(tenant, producer_cuit, branch, grain_type, campaign)`.

#### Posicion Consolidada Is NEVER Stored (ADR-013)

The cross-plant consolidated view is computed on demand by aggregating
per-plant ProducerAccount balances for the same producer CUIT across all
branches of the tenant. No `PosicionConsolidada` model exists. SQL
aggregation only.

#### AccountMovement Is Append-Only (ADR-008)

Same immutability pattern as StockMovement and GrainMovement:
- No UPDATE -- `save()` raises ValueError on existing records.
- No DELETE -- `delete()` raises ValueError.
- Errors are corrected via counter-entries (a new movement that reverses
  the incorrect amount), never by editing the original.
- API returns HTTP 405 for PATCH/DELETE on movements endpoint.

#### Blind Index for Producer CUIT (Encryption Pattern)

`producer_cuit` is PII. The Data Model stores it as a plain CharField for
now, but the REST API Design Section 9.1 notes: "AES-256-GCM encrypted at
rest". For searchability, spec-13 implements:
- `producer_cuit_encrypted` -- AES-256-GCM ciphertext (stored)
- `producer_cuit_hash` -- HMAC-SHA256 blind index (searchable)
- `producer_cuit` -- derived property (decrypted on access)

Same pattern as `barcode_encrypted` / `barcode_hash` in `Product` model.

#### Canje Is the Convergence Point (Data Model 8.4)

Canje (barter) links grain inventory (continuous) with agronomia inputs
(discrete). Both legs flow into ProducerAccount via AccountMovement:
- `CANJE_GRAIN_DEBIT` (kg withdrawn against input value)
- `CANJE_INPUT_CREDIT` (ARS debit for input invoice)

**NOTE**: CanjeOperation model (Data Model 8.4) depends on
LiquidacionPrimaria and Comprobante -- both in `apps/facturacion`. Canje
is structurally supported by the 8 movement types but its automated
triggers are deferred to the spec that implements LiquidacionPrimaria.

#### Account Statements (Research 2.3, SRS-CC03)

The acopiador provides producers with:
- **Kilos account statement**: opening balance, entries (by CEG), exits (by
  LPG, retiro, transfer), mermas, closing balance -- per grain type, campaign.
- **Monetary account statement**: debits (service charges, retentions),
  credits (LPG proceeds, advances), running balance in pesos.
- **Pending items reports**: CEGs pending liquidation, canjes pending.

Statements are provided on demand, at campaign close, or periodically.

---

## Functional Requirements

### FR-001: ProducerAccount Structure

The system shall maintain one current account per combination of
(tenant, producer_cuit, branch, grain_type, campaign). Each account carries
two independent sub-ledgers:
- `grain_balance_kg` (DecimalField 17,3) -- running grain balance
- `ars_balance` (DecimalField 17,3) -- ARS monetary balance
- `usd_balance` (DecimalField 17,3) -- USD monetary balance

Account `is_active` defaults to True. Accounts are auto-created on the first
romaneo CONFORME for a given (producer_cuit, branch, grain_type, campaign).

**Maps to**: Data Model v1.0 Section 6.1, SRS-CC01, REST API Design Section 9.1

### FR-002: AccountMovement Immutable Ledger

The system shall record all account movements as immutable append-only ledger
entries. Each entry contains: producer_account FK, movement_type (one of 8
authoritative types), romaneo FK (for CEG_DEPOSIT; null otherwise),
quantity_kg (grain delta; positive=in, negative=out), ars_amount (ARS delta;
positive=credit, negative=debit), usd_amount (USD delta), movement_at
(auto_now_add), reference_document, notes.

**8 authoritative movement types**:

| Type | Description | Grain Delta | ARS Delta |
|------|-------------|------------|----------|
| `CEG_DEPOSIT` | Grain deposit from romaneo | +kg | -- |
| `LPG_SALE` | Grain sold via liquidacion | -kg | +ARS |
| `FIJACION` | Price fixation event | -- | +ARS |
| `RETIRO` | Cash withdrawal by producer | -- | -ARS |
| `SERVICE_CHARGE` | Storage/service fees | -- | -ARS |
| `CANJE_GRAIN_DEBIT` | Grain leg of canje | -kg | -- |
| `CANJE_INPUT_CREDIT` | Input invoice credit | -- | -ARS |
| `RETENTION_DEDUCTION` | Withholding tax | -- | -ARS |

**Immutability rules** (same pattern as GrainMovement):
- No UPDATE -- save() raises ValueError on existing records.
- No DELETE -- delete() raises ValueError.
- Running balances on ProducerAccount updated atomically with movement creation.

**Maps to**: Data Model v1.0 Section 6.2, SRS-CC02, ADR-008, REST API Design Section 9.4

### FR-003: CEG_DEPOSIT from Romaneo Confirmation

When a romaneo transitions to CONFORME, the system shall:
1. Find or create a `ProducerAccount` for (tenant, romaneo.producer_cuit,
   romaneo.branch, romaneo.grain_type, romaneo.campaign).
2. Create an `AccountMovement` of type `CEG_DEPOSIT` with:
   - `quantity_kg = romaneo.peso_neto_conforme_kg`
   - `romaneo = romaneo` (FK traceability)
   - `ars_amount = None` (no monetary value at reception)
3. Increment `ProducerAccount.grain_balance_kg += quantity_kg`.

This runs alongside (not instead of) the spec-12 GrainMovement DEPOSIT.
Both happen atomically in the same database transaction during the
romaneo confirm action.

**Maps to**: SRS-CC01 ("auto-created on first romaneo"), SRS-CC02 (CEG_DEPOSIT entry), Data Model Section 10 (Romaneo -> ProducerAccount via AccountMovement)

### FR-004: Manual Movement Entry

The system shall provide API endpoints for operators to create manual
account movements of the following types:
- `SERVICE_CHARGE` -- requires: producer_account, ars_amount (negative),
  reference_document, notes.
- `RETIRO` -- requires: producer_account, ars_amount (negative),
  reference_document.
- `RETENTION_DEDUCTION` -- requires: producer_account, ars_amount (negative),
  reference_document.

Validation: ars_amount must be negative for debit types. producer_account
must belong to the requesting tenant.

**Maps to**: SRS-CC02 (service charges, retiro, retentions)

### FR-005: Posicion Consolidada (Derived View)

The system shall provide an API endpoint returning a producer's consolidated
position across all branches of the requesting tenant for a given campaign.
This is computed by SQL aggregation over ProducerAccount records -- no stored
entity. Required query parameters: `producer_cuit` (via blind index) and
`campaign` (UUID).

Response includes: total grain_balance_kg, total ars_balance, total
usd_balance, and per-branch breakdown.

**Maps to**: REST API Design Section 9.5, ADR-013

### FR-006: Account Statement

The system shall generate a current-account statement for a producer,
filterable by grain type and campaign. The statement shows:
- Opening balance (grain kg + ARS at period start)
- Each movement in chronological order with type, amount, document reference
- Closing balance (grain kg + ARS at period end)

The kilos sub-ledger and monetary sub-ledger are presented as separate
columns in the same statement.

**Maps to**: SRS-CC03

### FR-007: Account List and Detail

The system shall provide paginated list and detail endpoints for
ProducerAccount. List supports filtering by: producer_cuit (blind index
equality), grain_type, campaign, branch, is_active.

**Maps to**: REST API Design Section 9.2, Section 9.3

### FR-008: Movements Ledger

The system shall provide a cursor-paginated movements endpoint nested under
a producer account. Supports filtering by: movement_type, ordering by
movement_at. PATCH and DELETE return HTTP 405 (append_only_violation).

**Maps to**: REST API Design Section 9.4

### FR-009: Blind Index for Producer CUIT

The system shall store producer_cuit as:
- `producer_cuit_encrypted` (AES-256-GCM ciphertext)
- `producer_cuit_hash` (HMAC-SHA256 blind index)

API list endpoints use blind index equality for CUIT-based lookups.
The plaintext CUIT is returned in API responses (decrypted on read).

**Maps to**: REST API Design Section 9.1 ("AES-256-GCM encrypted at rest"),
Section 9.2 ("uses HMAC-SHA256 blind index")

### FR-010: Balance Consistency Check

The system shall provide a management command
(`check_account_balance`) that verifies `ProducerAccount.grain_balance_kg`
and `ars_balance` equal the sum of all `AccountMovement` deltas for each
account. Discrepancies are logged and reported.

**Maps to**: SRS-CC01 (derived balance integrity)

---

## Non-Functional Requirements

### NF-001: Balance Consistency

`ProducerAccount.grain_balance_kg` must equal the sum of all
`AccountMovement.quantity_kg` for that account at all times. Similarly for
`ars_balance` and `usd_balance`.

### NF-002: Query Performance

ProducerAccount list with balance fields must respond within 200ms for a
tenant with up to 5,000 accounts. The posicion consolidada aggregation must
respond within 500ms for a producer with accounts across 10 branches.

### NF-003: Immutability Enforcement

AccountMovement must reject UPDATE and DELETE at both the Django model level
(save/delete overrides) and API level (HTTP 405). Same enforcement as
GrainMovement in spec-12.

### NF-004: Tenant Isolation

Both new models (ProducerAccount, AccountMovement) inherit TenantBoundModel
and use TenantBoundManager with fail-closed filtering. Cross-tenant data
leakage is a critical security defect.

### NF-005: Provenance Fields (ADR-034)

All models carry: `created_at` (auto_now_add), `created_by` (FK to AppUser).
ProducerAccount also has `updated_at` (auto_now). AccountMovement omits
`updated_at` because it is immutable.

### NF-006: Encryption at Rest

`producer_cuit` fields use AES-256-GCM encryption with HMAC-SHA256 blind
index. Encryption key management follows the existing pattern in
`apps/core/encryption/`.

---

## Key Technical Details

### Entity Definitions (from Data Model v1.0 Section 6)

#### ProducerAccount -- Inherits TenantBoundModel

| Field | Django Type | Precision | Null | Default | Description |
|-------|-------------|-----------|------|---------|-------------|
| `id` | UUIDField PK | -- | No | uuid4 | -- |
| `tenant` | ForeignKey(Tenant) PROTECT | -- | No | -- | Owning tenant |
| `producer_cuit_encrypted` | CharField | max_length=500 | No | -- | AES-256-GCM (extension for PII compliance) |
| `producer_cuit_hash` | CharField | max_length=64 | No | -- | HMAC-SHA256 blind index (extension for searchability) |
| `branch` | ForeignKey(Branch) PROTECT | -- | No | -- | Per-plant scope |
| `grain_type` | ForeignKey(GrainType) PROTECT | -- | No | -- | One account per grain type |
| `campaign` | ForeignKey(CampanaConfig) PROTECT | -- | No | -- | Campaign year scope |
| `grain_balance_kg` | DecimalField | (17,3) | No | 0.000 | Running grain balance |
| `ars_balance` | DecimalField | (17,3) | No | 0.000 | ARS monetary balance |
| `usd_balance` | DecimalField | (17,3) | No | 0.000 | USD monetary balance |
| `is_active` | BooleanField | -- | No | True | -- |
| `created_at` | DateTimeField | -- | No | auto_now_add | ADR-034 |
| `updated_at` | DateTimeField | -- | No | auto_now | ADR-034 |
| `created_by` | ForeignKey(AppUser) PROTECT | -- | No | -- | ADR-034 |

**Derived property**: `producer_cuit` -- decrypts `producer_cuit_encrypted`
on access. Never stored in plaintext.

**Constraints**:
- UniqueConstraint: `(tenant, producer_cuit_hash, branch, grain_type, campaign)`
  -- one account per (producer, plant, grain, campaign). Uses hash instead of
  plaintext for the uniqueness dimension.
- Index: `(tenant_id, producer_cuit_hash)` -- blind index lookup
- Index: `(tenant_id, campaign_id, grain_type_id)` -- campaign/grain queries
- Index: `(tenant_id, branch_id, is_active)` -- branch listing

#### AccountMovement -- Inherits TenantBoundModel (IMMUTABLE)

| Field | Django Type | Precision | Null | Default | Description |
|-------|-------------|-----------|------|---------|-------------|
| `id` | UUIDField PK | -- | No | uuid4 | -- |
| `tenant` | ForeignKey(Tenant) PROTECT | -- | No | -- | -- |
| `producer_account` | ForeignKey(ProducerAccount) PROTECT | -- | No | -- | Target account |
| `movement_type` | CharField choices | -- | No | -- | One of 8 types |
| `romaneo` | ForeignKey(Romaneo) SET_NULL | -- | Yes | -- | Source romaneo (CEG_DEPOSIT only) |
| `quantity_kg` | DecimalField | (17,3) | Yes | -- | Grain delta (positive=in, negative=out) |
| `ars_amount` | DecimalField | (17,3) | Yes | -- | ARS delta (positive=credit, negative=debit) |
| `usd_amount` | DecimalField | (17,3) | Yes | -- | USD delta |
| `movement_at` | DateTimeField | -- | No | auto_now_add | Immutable timestamp |
| `reference_document` | CharField | max_length=100 | Yes | -- | External doc reference |
| `notes` | TextField | -- | Yes | -- | Operator notes |
| `created_by` | ForeignKey(AppUser) PROTECT | -- | No | -- | Operator (ADR-034) |

**NOTE on `liquidacion` FK**: Data Model Section 6.2 defines a
`liquidacion` ForeignKey(LiquidacionPrimaria) SET_NULL on AccountMovement.
LiquidacionPrimaria does NOT exist in the codebase yet (it is defined in
Data Model Section 8.2 but belongs to `apps/facturacion`). Spec-13
**defers** this FK -- it will be added by the spec that implements
LiquidacionPrimaria. The `LPG_SALE` and `FIJACION` movement types exist
in the choices enum but their automated triggers and liquidacion FK are
deferred.

**Immutability enforcement**:
- `save()`: raise ValueError if `self.pk` exists in DB
- `delete()`: raise ValueError always
- API: return HTTP 405 for PATCH/DELETE/PUT

**Constraints**:
- Index: `(tenant_id, producer_account_id, movement_at)` -- ledger queries
- Index: `(tenant_id, movement_type, movement_at)` -- filtered movement queries

### Service Layer

#### AccountService

```python
def get_or_create_account(
    tenant_id: uuid.UUID,
    producer_cuit: str,
    branch_id: uuid.UUID,
    grain_type_id: uuid.UUID,
    campaign_id: uuid.UUID,
    created_by: AppUser,
) -> tuple[ProducerAccount, bool]:
    """
    Find or create a ProducerAccount for the given composite key.

    Uses blind index (producer_cuit_hash) for lookup.
    Creates new account with zero balances if not found.
    Returns (account, created) tuple.
    """
```

#### CEGDepositService

```python
def create_ceg_deposit(
    romaneo: Romaneo,
    operator: AppUser,
) -> AccountMovement:
    """
    Create a CEG_DEPOSIT movement from a CONFORME romaneo.

    Steps:
    1. get_or_create_account for romaneo's composite key
    2. Create AccountMovement(CEG_DEPOSIT, quantity_kg=romaneo.peso_neto_conforme_kg)
    3. Update ProducerAccount.grain_balance_kg += quantity_kg
    4. Return the new movement

    Must run in same transaction as the romaneo confirmation
    and GrainMovement DEPOSIT (spec-12).
    """
```

#### PosicionConsolidadaService

```python
def compute_posicion_consolidada(
    tenant_id: uuid.UUID,
    producer_cuit_hash: str,
    campaign_id: uuid.UUID,
) -> dict:
    """
    Compute consolidated position across all branches.

    SQL aggregation over ProducerAccount:
    - total_grain_balance_kg = SUM(grain_balance_kg) grouped by grain_type
    - total_ars_balance = SUM(ars_balance)
    - total_usd_balance = SUM(usd_balance)
    - branch_breakdown: per-branch, per-grain-type rows

    Returns dict matching REST API Design Section 9.5 response schema.
    No stored entity -- computed on demand (ADR-013).
    """
```

#### StatementService

```python
def generate_statement(
    account_id: uuid.UUID,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    """
    Generate account statement for a producer account.

    Returns:
    - opening_balance: {grain_kg, ars, usd} at date_from
    - movements: chronological list of AccountMovement records
    - closing_balance: {grain_kg, ars, usd} at date_to

    Opening balance = sum of all movements before date_from.
    Closing balance = opening + sum of movements in range.
    """
```

#### ManualMovementService

```python
def create_manual_movement(
    account_id: uuid.UUID,
    movement_type: str,  # SERVICE_CHARGE | RETIRO | RETENTION_DEDUCTION
    ars_amount: Decimal,
    operator: AppUser,
    reference_document: str,
    notes: str = "",
) -> AccountMovement:
    """
    Create an operator-initiated account movement.

    Validates:
    - movement_type is one of the allowed manual types
    - ars_amount is negative for debit types
    - account belongs to requesting tenant
    Updates ProducerAccount.ars_balance atomically.
    """
```

### Integration Points

#### Romaneo CONFORME -> CEG_DEPOSIT (FR-003)

The spec-12 `RomaneoViewSet.confirmar` action already creates a
GrainMovement DEPOSIT. Spec-13 extends this action to also call
`CEGDepositService.create_ceg_deposit()` in the same transaction.

```python
# In romaneo viewset confirmar action (pseudo-code):
with transaction.atomic():
    romaneo.status = "CONFORME"
    romaneo.save()
    # spec-12: grain deposit
    grain_deposit_service.create_deposit(romaneo)
    # spec-13: account credit
    ceg_deposit_service.create_ceg_deposit(romaneo, operator=request.user)
```

#### FijacionRecord and LiquidacionPrimaria (DEFERRED)

Data Model Section 6.3 defines `FijacionRecord` with a mandatory FK to
`LiquidacionPrimaria`. Since LiquidacionPrimaria does not exist in the
codebase yet, `FijacionRecord` is **deferred** to the spec that implements
LiquidacionPrimaria (Form 1116-C). The REST API endpoints at
`/api/v1/cuentas/fijaciones/` (Section 9.6-9.7) are also deferred.

Similarly, the `AccountMovement.liquidacion` FK (Data Model Section 6.2)
is deferred. The `LPG_SALE` and `FIJACION` movement types exist in the
choices enum for forward compatibility but have no automated triggers yet.

#### CanjeOperation (DEFERRED)

Data Model Section 8.4 defines `CanjeOperation` linking LiquidacionPrimaria
+ Comprobante. Both `CANJE_GRAIN_DEBIT` and `CANJE_INPUT_CREDIT` movement
types exist in the enum but their automated triggers via CanjeOperation
are deferred.

---

## Acceptance Criteria

### AC-01: ProducerAccount Auto-Creation (SRS-CC01)

- [ ] ProducerAccount is auto-created when the first romaneo for a
      (producer_cuit, branch, grain_type, campaign) reaches CONFORME
- [ ] Subsequent romaneos for the same combination reuse the existing account
- [ ] Account starts with zero balances (0.000 kg, 0.000 ARS, 0.000 USD)

### AC-02: CEG_DEPOSIT Movement (SRS-CC02)

- [ ] Romaneo CONFORME creates an AccountMovement with type CEG_DEPOSIT
- [ ] `quantity_kg = romaneo.peso_neto_conforme_kg`
- [ ] `ProducerAccount.grain_balance_kg` increments by the deposit amount
- [ ] `romaneo` FK links to the source romaneo
- [ ] Both GrainMovement DEPOSIT (spec-12) and AccountMovement CEG_DEPOSIT
      (spec-13) happen in the same atomic transaction

### AC-03: AccountMovement Immutability (ADR-008)

- [ ] AccountMovement.save() raises ValueError for existing records
- [ ] AccountMovement.delete() raises ValueError always
- [ ] API returns HTTP 405 for PATCH/DELETE/PUT on movements endpoint
- [ ] Running balances on ProducerAccount equal sum of all movements

### AC-04: Manual Movement Entry

- [ ] Operator can create SERVICE_CHARGE, RETIRO, RETENTION_DEDUCTION
      movements via API
- [ ] `ars_amount` must be negative for debit types
- [ ] Account balance updates atomically with movement creation
- [ ] Movements carry operator provenance (created_by)

### AC-05: Posicion Consolidada (ADR-013)

- [ ] API returns aggregated position across all branches for a given
      (producer_cuit, campaign)
- [ ] Response includes total balances and per-branch breakdown
- [ ] No stored entity -- pure SQL aggregation
- [ ] Blind index search for producer_cuit

### AC-06: Account Statement (SRS-CC03)

- [ ] Statement shows opening balance, movements, closing balance
- [ ] Kilos and pesos sub-ledgers presented separately
- [ ] Filterable by grain type and campaign
- [ ] Opening balance = sum of all movements before period start

### AC-07: Blind Index Search

- [ ] `producer_cuit` is stored encrypted (AES-256-GCM)
- [ ] Equality search uses HMAC-SHA256 blind index
- [ ] Plaintext CUIT returned in API responses (decrypted on read)
- [ ] Uniqueness constraint uses hash dimension

### AC-08: Tenant Isolation

- [ ] All models use TenantBoundManager
- [ ] Cross-tenant queries return empty results (fail-closed)
- [ ] Tests verify isolation for ProducerAccount and AccountMovement

### AC-09: Balance Consistency Command

- [ ] Management command `check_account_balance` detects balance drift
- [ ] Reports accounts where stored balance != sum of movements
- [ ] Non-destructive (read-only check)

### AC-10: Negative Balance Handling

- [ ] A RETIRO or SERVICE_CHARGE that makes ars_balance negative is allowed
      (producers can have debit balances -- this is normal commercial practice)
- [ ] A CEG_DEPOSIT that makes grain_balance_kg negative is rejected
      (grain cannot go negative)
- [ ] Validation is documented and explicit

---

## Coherence Notes

### Blueprint Deviations (Justified)

1. **producer_cuit encryption**: Data Model Section 6.1 defines `producer_cuit`
   as a plain CharField. Spec-13 adds `producer_cuit_encrypted` (AES-256-GCM)
   and `producer_cuit_hash` (HMAC-SHA256) per REST API Design Section 9.1
   ("AES-256-GCM encrypted at rest") and Section 9.2 ("uses HMAC-SHA256 blind
   index"). The encryption pattern follows the existing `barcode_encrypted` /
   `barcode_hash` implementation in `Product`.

2. **AccountMovement.liquidacion FK deferred**: Data Model Section 6.2 defines
   this FK to LiquidacionPrimaria. Since LiquidacionPrimaria does not exist
   in the codebase, this FK is deferred to avoid cross-module stub creation.
   The FK will be added by migration when LiquidacionPrimaria is implemented.

3. **FijacionRecord deferred**: Data Model Section 6.3 and REST API Sections
   9.6-9.7 define this entity and its endpoints. FijacionRecord has a
   mandatory FK to LiquidacionPrimaria and AccountMovement -- both need to
   exist before FijacionRecord can be created. Deferred to LPG implementation.

4. **Stored vs Derived balance**: SRS-CC01 says "balance is always derived;
   no stored-balance field exists". Data Model Section 6.1 defines stored
   fields `grain_balance_kg`, `ars_balance`, `usd_balance`. Spec-13 follows
   the **Data Model** (stored running balance) because: (a) the Data Model is
   the authoritative schema, (b) stored balance enables fast reads without
   recomputing from potentially millions of movements, (c) the
   `check_account_balance` management command validates consistency. This is
   the same pattern used by GrainLot.total_kg in spec-12.

### SRS Traceability Discrepancy

The SRS v1.0 traceability matrix (Section 8) maps SRS-CC01 through SRS-CC07
to "spec-011". However, the README spec catalog and dependency graph assign
Producer Accounts to **spec-13**. Spec-13 is the authoritative assignment.
The SRS mapping is a labeling artifact from an earlier spec numbering scheme
(same issue as spec-12 with SRS-AL mapping).

### Deferred SRS Requirements

| SRS | Description | Why Deferred |
|-----|-------------|-------------|
| SRS-CC04 | SISA Retention Calculation | Requires ARCA web service integration + external SISA lookup (Phase 2) |
| SRS-CC05 | WSLPG Electronic Settlement | Requires LiquidacionPrimaria (Form 1116-C) implementation |
| SRS-CC06 | Electronic Invoice Generation | Requires WSFEv1 integration for settlement invoicing |
| SRS-CC07 | Commission Calculation | Requires settlement flow (LiquidacionPrimaria) |

These requirements are structurally supported: the 8 movement types include
LPG_SALE, FIJACION, RETENTION_DEDUCTION, and CANJE_* which will be activated
by the settlement/LPG spec. No schema change needed to enable them.

---

## Dependencies

### Depends On

| Spec | What It Provides |
|------|------------------|
| spec-10 | GrainType (grain codes), CampanaConfig (campaign years) -- account scoping dimensions |
| spec-11 | Romaneo (CONFORME triggers CEG_DEPOSIT), peso_neto_conforme_kg (deposit amount), producer_cuit (account identity) |
| spec-12 | GrainMovement DEPOSIT happens in same transaction as CEG_DEPOSIT. StorageUnit/GrainLot context. The confirmar action is the shared integration point. |

### Blocks

| Spec | What It Needs |
|------|---------------|
| spec-14 | Agronomia adaptation may reference producer accounts for input invoicing |
| spec-15 | WSLPG integration (LiquidacionPrimaria) will add the deferred liquidacion FK and FijacionRecord |

---

## Agent Structure (4 agents)

| Agent | File | Type | Scope |
|-------|------|------|-------|
| A1 | `agents/A1-models.md` | python-expert | ProducerAccount, AccountMovement models, migration, RLS, app boilerplate |
| A2 | `agents/A2-services.md` | backend-architect | AccountService, CEGDepositService, PosicionConsolidadaService, StatementService, ManualMovementService, romaneo integration hook |
| A3 | `agents/A3-api.md` | backend-architect | Serializers, ViewSets, URL registration, blind index search, cursor pagination |
| A4 | `agents/A4-tests.md` | quality-engineer | Model tests, API tests, immutability, CEG_DEPOSIT integration, tenant isolation, blind index, balance consistency |

### Wave Structure

```
Wave 1: A1 (Models + Migration + RLS + App Boilerplate)
    |
    v
Wave 2: A2 (Services + Romaneo Hook)  -- depends on A1 models
    |
    v
Wave 3: A3 (API Layer)  -- depends on A1 models + A2 services
    |
    v
Wave 4: A4 (Tests)  -- depends on A1 + A2 + A3
```

### Gate Checkpoints

| Gate | After | Command | Criterion |
|------|-------|---------|-----------|
| G1 | Wave 1 | `DJANGO_SETTINGS_MODULE=gravitea.settings.test .venv/bin/python -c "from apps.cuentas.models import ProducerAccount, AccountMovement; print('OK')"` | Models importable |
| G2 | Wave 1 | `.venv/bin/python manage.py makemigrations --check --dry-run` | No missing migrations |
| G3 | Wave 2 | `DJANGO_SETTINGS_MODULE=gravitea.settings.test .venv/bin/python -c "from apps.cuentas.services.accounts import AccountService; print('OK')"` | Services importable |
| G4 | Wave 3 | `DJANGO_SETTINGS_MODULE=gravitea.settings.test .venv/bin/python -c "from apps.cuentas.urls import urlpatterns; print(len(urlpatterns))"` | URL count > 0 |
| G5 | Wave 4 | `.venv/bin/python -m pytest tests/cuentas/ -v --tb=short` | All tests pass |
