# Data Model: Producer Accounts (Spec-13)

**Generated**: 2026-03-19
**Source**: Data Model v1.0 §6, 13-specify.md entity definitions, spec.md requirements

---

## Entity Overview

```
  Branch (pre-existing)          GrainType (spec-10)     CampanaConfig (spec-10)
       │                                │                        │
       │ FK                             │ FK                     │ FK
       ▼                                ▼                        ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                           ProducerAccount                                     │
│ id (UUID PK)                                                                  │
│ tenant (FK→Tenant, PROTECT)                                                   │
│ branch (FK→Branch, PROTECT)                                                   │
│ grain_type (FK→GrainType, PROTECT)                                           │
│ campaign (FK→CampanaConfig, PROTECT)                                         │
│ producer_cuit_encrypted (EncryptedCharField) ← AES-256-GCM ciphertext        │
│ producer_cuit_hash (BlindIndexField)         ← HMAC-SHA256 for search        │
│ grain_balance_kg (DECIMAL(17,3))             ← running grain balance          │
│ ars_balance (DECIMAL(17,3))                  ← running ARS balance            │
│ usd_balance (DECIMAL(17,3))                  ← running USD balance            │
│ is_active (BooleanField, default=True)                                        │
│ created_at, updated_at, created_by                                            │
│ [UniqueConstraint: (tenant, producer_cuit_hash, branch, grain_type, campaign)]│
└──────────────────────┬───────────────────────────────────────────────────────┘
                       │ 1:N
                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                          AccountMovement                              IMMUTABLE│
│ id (UUID PK)                                                                  │
│ tenant (FK→Tenant, PROTECT)                                                   │
│ producer_account (FK→ProducerAccount, PROTECT)                               │
│ movement_type (CharField choices — 9 types)                                   │
│ quantity_kg (DECIMAL(17,3), default=0)  ← grain delta                        │
│ ars_amount (DECIMAL(17,3), default=0)   ← ARS delta                          │
│ usd_amount (DECIMAL(17,3), default=0)   ← USD delta                          │
│ romaneo (FK→Romaneo, SET_NULL, null)    ← CEG_DEPOSIT source traceability    │
│ reference_document (CharField(200), blank)                                    │
│ notes (TextField, blank)                                                      │
│ movement_at (DateTimeField, auto_now_add) ← immutable timestamp              │
│ created_by (FK→AppUser, PROTECT)                                              │
│ [NO updated_at — immutable]                                                   │
└──────────────────────────────────────────────────────────────────────────────┘

  Romaneo (spec-11, MODIFIED — no new fields, just FK reference from AccountMovement)
```

---

## Entity: ProducerAccount

**Table**: `cuentas_produceraccount`
**Inherits**: `TenantBoundModel`
**Manager**: `TenantBoundManager` (fail-closed) + `AllObjectsManager`

### Fields

| Field | Django Type | DB Type | Null | Default | Notes |
|-------|-------------|---------|------|---------|-------|
| `id` | UUIDField PK | uuid | No | uuid4 | Immutable |
| `tenant` | FK(Tenant, PROTECT) | uuid | No | — | TenantBound |
| `branch` | FK(Branch, PROTECT) | uuid | No | — | Physical acopio plant |
| `grain_type` | FK(GrainType, PROTECT) | uuid | No | — | Grain dimension |
| `campaign` | FK(CampanaConfig, PROTECT) | uuid | No | — | Campaign dimension |
| `producer_cuit_encrypted` | EncryptedCharField(max_length=500) | text | No | — | AES-256-GCM ciphertext; auto-decrypt on load; RegexValidator(r'^\d{2}-\d{8}-\d$') enforces XX-XXXXXXXX-X format |
| `producer_cuit_hash` | BlindIndexField(max_length=64) | varchar(64) | No | — | HMAC-SHA256 of plaintext CUIT; auto-computed on save |
| `grain_balance_kg` | DecimalField(17,3) | numeric(17,3) | No | 0.000 | Running grain balance; updated atomically |
| `ars_balance` | DecimalField(17,3) | numeric(17,3) | No | 0.000 | Running ARS monetary balance (can be negative) |
| `usd_balance` | DecimalField(17,3) | numeric(17,3) | No | 0.000 | Running USD monetary balance (can be negative) |
| `is_active` | BooleanField | boolean | No | True | Soft-delete flag |
| `created_at` | DateTimeField(auto_now_add) | timestamptz | No | — | ADR-034 |
| `updated_at` | DateTimeField(auto_now) | timestamptz | No | — | ADR-034 |
| `created_by` | FK(AppUser, PROTECT) | uuid | No | — | ADR-034 |

**Property** (not stored): `producer_cuit` → returns `self.producer_cuit_encrypted`
(EncryptedCharField transparently decrypts on access).

### Constraints

```python
class Meta:
    db_table = "cuentas_produceraccount"
    constraints = [
        models.UniqueConstraint(
            fields=["tenant", "producer_cuit_hash", "branch", "grain_type", "campaign"],
            name="unique_producer_account_per_dimension",
        ),
        models.CheckConstraint(
            check=models.Q(grain_balance_kg__gte=0),
            name="grain_balance_kg_non_negative",
        ),
    ]
    indexes = [
        models.Index(fields=["tenant", "producer_cuit_hash"]),
        models.Index(fields=["tenant", "branch", "campaign"]),
    ]
```

**Business Rules**:
- `grain_balance_kg` is non-negative (CHECK constraint). Monetary balances can go negative.
- `producer_cuit_hash` is auto-computed in `save()` from plaintext if not set.
- Composite uniqueness ensures one account per (producer × branch × grain × campaign).

---

## Entity: AccountMovement

**Table**: `cuentas_accountmovement`
**Inherits**: `TenantBoundModel`
**Manager**: `TenantBoundManager` (fail-closed)
**IMMUTABLE**: `save()` raises `ValueError` if not `_state.adding`; `delete()` raises `ValueError`

### Movement Types

| Code | Label | Grain Δ | ARS Δ | USD Δ | Triggered By |
|------|-------|---------|-------|-------|-------------|
| `CEG_DEPOSIT` | Grain Deposit (CEG) | + (kg deposited) | — | — | Romaneo CONFORME |
| `LPG_SALE` | Grain Sale (LPG) | − (kg sold) | + (proceeds) | — | LiquidacionPrimaria (deferred) |
| `FIJACION` | Price Fixation | — | + (fixed price) | — | LiquidacionPrimaria (deferred) |
| `RETIRO` | Cash Withdrawal | — | − (withdrawal) | − (optional) | Manual entry |
| `SERVICE_CHARGE` | Service Charge | — | − (charge) | — | Manual entry |
| `CANJE_GRAIN_DEBIT` | Canje Grain Debit | − (grain exchanged) | — | — | Canje (deferred) |
| `CANJE_INPUT_CREDIT` | Canje Input Credit | — | + (input credit) | — | Canje (deferred) |
| `RETENTION_DEDUCTION` | Tax Retention | — | − (retention) | — | Manual entry |
| `ADJUSTMENT` | Adjustment (Supervisor) | ± | ± | ± | Manual entry (supervisor only) |

### Fields

| Field | Django Type | DB Type | Null | Default | Notes |
|-------|-------------|---------|------|---------|-------|
| `id` | UUIDField PK | uuid | No | uuid4 | Immutable |
| `tenant` | FK(Tenant, PROTECT) | uuid | No | — | TenantBound |
| `producer_account` | FK(ProducerAccount, PROTECT) | uuid | No | — | Parent account |
| `movement_type` | CharField(choices) | varchar(30) | No | — | One of 9 types |
| `quantity_kg` | DecimalField(17,3) | numeric(17,3) | No | 0.000 | Grain delta; positive=credit, negative=debit |
| `ars_amount` | DecimalField(17,3) | numeric(17,3) | No | 0.000 | ARS delta |
| `usd_amount` | DecimalField(17,3) | numeric(17,3) | No | 0.000 | USD delta |
| `romaneo` | FK(Romaneo, SET_NULL) | uuid | Yes | NULL | Source for CEG_DEPOSIT |
| `reference_document` | CharField(200) | varchar(200) | Yes | "" | Ref doc number for manual entries |
| `notes` | TextField | text | Yes | "" | Free text notes |
| `movement_at` | DateTimeField(auto_now_add) | timestamptz | No | — | Immutable timestamp |
| `created_by` | FK(AppUser, PROTECT) | uuid | No | — | Operator provenance |

**Note**: No `updated_at` — model is immutable, there are no updates.

### Constraints

```python
class Meta:
    db_table = "cuentas_accountmovement"
    indexes = [
        models.Index(fields=["producer_account", "-movement_at"]),
        models.Index(fields=["tenant", "movement_type"]),
    ]
    ordering = ["-movement_at"]
```

**Immutability enforcement**:
```python
def save(self, *args, **kwargs):
    if not self._state.adding:
        raise ValueError("AccountMovement is immutable and cannot be modified.")
    super().save(*args, **kwargs)

def delete(self, *args, **kwargs):
    raise ValueError("AccountMovement is immutable and cannot be deleted.")
```

---

## Modified Entity: Romaneo (spec-11)

No new fields added to Romaneo. AccountMovement has a nullable FK to Romaneo
(`SET_NULL`) for CEG_DEPOSIT traceability. If the romaneo is later administratively
deleted (unlikely), the movement record remains with `romaneo = NULL`.

---

## Derived View: PosicionConsolidada (never stored)

**Not a model.** Computed on demand via SQL aggregation:

```sql
SELECT
    producer_cuit_hash,
    grain_type_id,
    campaign_id,
    SUM(grain_balance_kg) AS total_grain_kg,
    SUM(ars_balance) AS total_ars,
    SUM(usd_balance) AS total_usd,
    JSON_AGG(JSON_BUILD_OBJECT(
        'branch_id', branch_id,
        'grain_balance_kg', grain_balance_kg,
        'ars_balance', ars_balance,
        'usd_balance', usd_balance
    )) AS branch_breakdown
FROM cuentas_produceraccount
WHERE tenant_id = %s
  AND producer_cuit_hash = %s
  AND campaign_id = %s
  AND is_active = true
GROUP BY producer_cuit_hash, grain_type_id, campaign_id;
```

Returned in API response as a structured object. Never persisted. (ADR-013: derived views)

---

## RLS Policies

```sql
-- backend/database/sql/cuentas_rls.sql
ALTER TABLE cuentas_produceraccount ENABLE ROW LEVEL SECURITY;
ALTER TABLE cuentas_produceraccount FORCE ROW LEVEL SECURITY;

CREATE POLICY produceraccount_tenant_isolation ON cuentas_produceraccount
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

ALTER TABLE cuentas_accountmovement ENABLE ROW LEVEL SECURITY;
ALTER TABLE cuentas_accountmovement FORCE ROW LEVEL SECURITY;

CREATE POLICY accountmovement_tenant_isolation ON cuentas_accountmovement
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());
```

---

## State Transitions

### AccountMovement Creation Flow

```
Romaneo CONFORME
    │
    ├─ is_own_grain=True → SKIP (no account, no movement)
    │
    └─ is_own_grain=False
           │
           ├─ transaction.atomic()
           │       │
           │       ├─ romaneo.save(CONFORME)
           │       ├─ create_deposit_from_romaneo()  [spec-12 grain lot]
           │       └─ create_ceg_deposit()
           │               │
           │               ├─ ProducerAccount.get_or_create() [select_for_update]
           │               ├─ AccountMovement.create(CEG_DEPOSIT)
           │               └─ account.grain_balance_kg += kg; account.save()
           │
           └─ Response(CONFORME romaneo data)
```

### Manual Movement Flow

```
API POST /accounts/{id}/movements/
    │
    ├─ Validate movement_type in MANUAL_TYPES
    ├─ Validate ADJUSTMENT → requires supervisor permission
    ├─ Validate sign convention (debit types must be negative for ARS/grain)
    │
    └─ transaction.atomic()
            ├─ AccountMovement.create()
            └─ ProducerAccount.update(balance fields) via update_fields
```
