# Data Model: Electronic Invoicing Backend (Facturacion)

**Feature**: 008-facturacion-backend
**Date**: 2026-02-10
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

---

## Entity Relationship Diagram

```
Tenant (core)
├── ARCACredential (1:2 max — one per environment)
├── PuntoDeVenta (1:N)
│   └── Comprobante (1:N per PtoVta+CbteTipo)
│       ├── AlicIva (1:N)
│       ├── Tributo (1:N)
│       └── CbteAsoc (1:N)
└── CAEA (1:N per quincena)
```

---

## Entity Definitions

### ARCACredential

**Purpose**: ARCA authentication credentials per tenant, per environment.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUIDField | PK, default=uuid4 | Primary key |
| `tenant` | ForeignKey(Tenant) | ON DELETE CASCADE | Parent tenant |
| `tenant_id` | UUIDField | inherited from TenantBoundModel | Tenant isolation |
| `cuit_holder` | CharField(11) | NOT NULL | Certificate holder CUIT (11 digits, no hyphens) |
| `cuit_represented` | CharField(11) | NULL, blank | Represented company CUIT (delegation model) |
| `certificate_pem` | TextField | NOT NULL | X.509 certificate in PEM format |
| `private_key_pem` | EncryptedTextField | NOT NULL | RSA private key (AES-256-GCM encrypted) |
| `is_production` | BooleanField | default=False | True=production, False=homologacion |
| `is_active` | BooleanField | default=True | Soft-disable without deletion |
| `certificate_expires_at` | DateTimeField | NULL | Certificate expiration (for system check warnings) |
| `last_unique_id` | BigIntegerField | default=0 | Last TRA uniqueId for replay protection |
| `created_at` | DateTimeField | auto_now_add | Record creation |
| `updated_at` | DateTimeField | auto_now | Last modification |

**Inherits**: `TenantBoundModel`

**Constraints**:
- `UniqueConstraint(fields=["tenant_id", "is_production"], name="uq_arca_credential_tenant_env")` — One credential per (tenant, environment)
- Max 2 credentials per tenant (one testing, one production) — enforced at serializer level

**Indexes**:
- `tenant_id` (inherited, B-tree)
- `(tenant_id, is_production)` (unique)

**System Checks**:
- `arca.W001`: Warning if `certificate_expires_at` is within 30 days

---

### PuntoDeVenta

**Purpose**: Registered point of sale for electronic invoicing.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUIDField | PK, default=uuid4 | Primary key |
| `tenant` | ForeignKey(Tenant) | ON DELETE CASCADE | Parent tenant |
| `tenant_id` | UUIDField | inherited | Tenant isolation |
| `numero` | PositiveIntegerField | NOT NULL, 1-99999 | PtoVta number |
| `tipo` | CharField(20) | choices, default="electronic" | Type: electronic/manual |
| `description` | CharField(100) | blank | Human-readable label |
| `is_active` | BooleanField | default=True | Active flag |
| `fecha_alta` | DateField | NULL | ARCA registration date |
| `created_at` | DateTimeField | auto_now_add | Record creation |
| `updated_at` | DateTimeField | auto_now | Last modification |

**Inherits**: `TenantBoundModel`

**Constraints**:
- `UniqueConstraint(fields=["tenant_id", "numero"], name="uq_punto_venta_tenant")` — Unique PtoVta per tenant
- `CheckConstraint(check=Q(numero__gte=1, numero__lte=99999), name="ck_punto_venta_range")`

**Indexes**:
- `tenant_id` (inherited)
- `(tenant_id, numero)` (unique)

**Notes**: `select_for_update()` is applied on this model during CbteNro assignment to serialize concurrent requests.

---

### Comprobante

**Purpose**: Immutable fiscal document ledger entry. Central entity.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUIDField | PK, default=uuid4 | Primary key |
| `tenant` | ForeignKey(Tenant) | ON DELETE RESTRICT | Parent tenant |
| `tenant_id` | UUIDField | inherited | Tenant isolation |
| `punto_venta` | ForeignKey(PuntoDeVenta) | ON DELETE RESTRICT | Associated PtoVta |
| `cbte_tipo` | PositiveSmallIntegerField | NOT NULL | CbteTipo code (1,2,3,6,7,8,11,12,13,51,52,53) |
| `cbte_nro` | PositiveBigIntegerField | NOT NULL | Sequential per PtoVta+CbteTipo |
| `concepto` | PositiveSmallIntegerField | NOT NULL, default=1 | 1=Products, 2=Services, 3=Both |
| `doc_tipo` | PositiveSmallIntegerField | NOT NULL | Buyer document type (DocTipo) |
| `doc_nro` | CharField(20) | NOT NULL | Buyer document number |
| `cbte_fch` | DateField | NOT NULL | Invoice date |
| `fch_serv_desde` | DateField | NULL | Service start date (Concepto 2,3) |
| `fch_serv_hasta` | DateField | NULL | Service end date (Concepto 2,3) |
| `fch_vto_pago` | DateField | NULL | Payment due date (Concepto 2,3) |
| `imp_total` | DecimalField(17,3) | NOT NULL | Total amount |
| `imp_neto` | DecimalField(17,3) | NOT NULL | Net taxable amount |
| `imp_iva` | DecimalField(17,3) | default=0 | Total IVA |
| `imp_trib` | DecimalField(17,3) | default=0 | Other taxes |
| `imp_op_ex` | DecimalField(17,3) | default=0 | IVA-exempt amount |
| `imp_tot_conc` | DecimalField(17,3) | default=0 | Non-taxable amount |
| `mon_id` | CharField(3) | default="PES" | Currency code (PES=ARS) |
| `mon_cotiz` | DecimalField(10,6) | default=1 | Exchange rate |
| `emitter_cuit` | CharField(11) | NOT NULL | Emitter CUIT |
| `emitter_condicion_iva` | PositiveSmallIntegerField | NOT NULL | Emitter CondicionIVA |
| `receptor_condicion_iva` | PositiveSmallIntegerField | NOT NULL | Buyer CondicionIVA |
| `cae` | CharField(14) | NULL, db_index | 14-digit CAE from ARCA |
| `cae_fch_vto` | DateField | NULL | CAE expiration date |
| `caea` | ForeignKey(CAEA) | NULL, ON DELETE RESTRICT | CAEA reference (offline mode) |
| `status` | CharField(12) | NOT NULL, choices | DRAFT/VALIDANDO/AUTORIZADO/OBSERVADO/RECHAZADO |
| `arca_response` | JSONField | NULL | Full ARCA response snapshot |
| `arca_errors` | JSONField | NULL | ARCA error/observation details |
| `created_at` | DateTimeField | auto_now_add | Record creation |

**Inherits**: `TenantBoundModel`

**Status Enum**:
```
DRAFT → VALIDANDO → AUTORIZADO (terminal, immutable)
                  → OBSERVADO  (terminal, immutable, CAE granted with warnings)
                  → RECHAZADO  (allows retry with same CbteNro)
```

**Constraints**:
- `UniqueConstraint(fields=["tenant_id", "punto_venta", "cbte_tipo", "cbte_nro"], name="uq_comprobante_fiscal")` — Fiscal uniqueness
- All FK references use `ON DELETE RESTRICT` — never cascade-delete fiscal records

**Indexes**:
- `(tenant_id, punto_venta, cbte_tipo, cbte_nro)` (unique)
- `(tenant_id, status)` (B-tree, for filtered queries)
- `(tenant_id, cbte_fch)` (B-tree, for date range queries)
- `cae` (B-tree, for lookup by CAE)
- `created_at` (B-tree, for cursor pagination ordering)

**Immutability Rules**:
- `save()` override: Raises `ValueError` if existing record has status in (AUTORIZADO, OBSERVADO)
- `delete()` override: Always raises `ValueError` — comprobantes are never deleted
- Corrections via Nota de Credito only

---

### AlicIva

**Purpose**: IVA rate breakdown entry for a comprobante.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUIDField | PK, default=uuid4 | Primary key |
| `comprobante` | ForeignKey(Comprobante) | ON DELETE RESTRICT | Parent comprobante |
| `iva_id` | PositiveSmallIntegerField | NOT NULL | ARCA IVA code (3,4,5,6,8,9) |
| `base_imp` | DecimalField(17,3) | NOT NULL | Taxable base amount |
| `importe` | DecimalField(17,3) | NOT NULL | IVA amount |

**No tenant_id**: Inherits tenant scope from Comprobante (cascade isolation via FK).

**IVA Code Reference**:

| Code | Rate | Description |
|------|------|-------------|
| 3 | 0% | Exento |
| 4 | 10.5% | Reducido |
| 5 | 21% | General |
| 6 | 27% | Incrementado |
| 8 | 5% | Reducido menor |
| 9 | 2.5% | Reducido minimo |

**Validation Rules**:
- Types A/B/M: AlicIva is MANDATORY (at least one entry)
- Type C: AlicIva must be EMPTY (IVA omitted entirely)
- Sum of `importe` must equal parent `imp_iva`
- Sum of `base_imp` must equal parent `imp_neto`

---

### Tributo

**Purpose**: Other tax/tribute entry for a comprobante (e.g., Ingresos Brutos).

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUIDField | PK, default=uuid4 | Primary key |
| `comprobante` | ForeignKey(Comprobante) | ON DELETE RESTRICT | Parent comprobante |
| `tributo_id` | PositiveSmallIntegerField | NOT NULL | ARCA tribute type code |
| `desc` | CharField(100) | NOT NULL | Tax description |
| `base_imp` | DecimalField(17,3) | NOT NULL | Taxable base |
| `alic` | DecimalField(5,2) | NOT NULL | Tax rate (%) |
| `importe` | DecimalField(17,3) | NOT NULL | Tax amount |

**No tenant_id**: Inherits tenant scope from Comprobante.

**Validation Rules**:
- If parent `imp_trib` = 0: No Tributo entries allowed, `<Tributos>` XML element omitted entirely
- Sum of `importe` must equal parent `imp_trib`

---

### CbteAsoc

**Purpose**: Associated comprobante reference for Nota de Credito/Debito.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUIDField | PK, default=uuid4 | Primary key |
| `comprobante` | ForeignKey(Comprobante) | ON DELETE RESTRICT | Parent NC/ND |
| `tipo` | PositiveSmallIntegerField | NOT NULL | Associated CbteTipo |
| `pto_vta` | PositiveIntegerField | NOT NULL | Associated PtoVta |
| `nro` | PositiveBigIntegerField | NOT NULL | Associated CbteNro |
| `cuit` | CharField(11) | NULL, blank | Associated emitter CUIT (optional) |

**No tenant_id**: Inherits tenant scope from Comprobante.

**Validation Rules**:
- Type compatibility: A→A, B→B, C→C (cross-type references rejected by ARCA with error 202)
- Referenced comprobante should exist in local DB (soft validation — ARCA is the authority)

---

### CAEA

**Purpose**: Pre-authorized offline code for biweekly periods.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUIDField | PK, default=uuid4 | Primary key |
| `tenant` | ForeignKey(Tenant) | ON DELETE RESTRICT | Parent tenant |
| `tenant_id` | UUIDField | inherited | Tenant isolation |
| `punto_venta` | ForeignKey(PuntoDeVenta) | ON DELETE RESTRICT | Associated PtoVta |
| `caea_code` | CharField(14) | NOT NULL, unique | 14-digit CAEA from ARCA |
| `periodo` | CharField(6) | NOT NULL | Period YYYYMM |
| `orden` | PositiveSmallIntegerField | NOT NULL | 1=first quincena, 2=second |
| `fch_vig_desde` | DateField | NOT NULL | Validity start |
| `fch_vig_hasta` | DateField | NOT NULL | Validity end |
| `fch_tope_inf` | DateField | NOT NULL | Reporting deadline |
| `status` | CharField(20) | NOT NULL, choices | ACTIVE/REPORTED/REPORTED_NO_MOVEMENT/EXPIRED |
| `created_at` | DateTimeField | auto_now_add | Record creation |

**Inherits**: `TenantBoundModel`

**Status Transitions**:
```
ACTIVE → REPORTED             (batch FECAEARegInformativo succeeded)
ACTIVE → REPORTED_NO_MOVEMENT (FECAEASinMovimientoInformar called)
ACTIVE → EXPIRED              (deadline passed without reporting)
```

**Constraints**:
- `UniqueConstraint(fields=["tenant_id", "punto_venta", "periodo", "orden"], name="uq_caea_period")`

---

## RLS Policies

All tables with `tenant_id` column receive row-level security policies:

```sql
-- Pattern for each facturacion table
ALTER TABLE facturacion_{table} ENABLE ROW LEVEL SECURITY;
ALTER TABLE facturacion_{table} FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_{table}
    ON facturacion_{table}
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

**Tables requiring RLS**:
- `facturacion_arcacredential`
- `facturacion_puntodeventa`
- `facturacion_comprobante`
- `facturacion_caea`

**Tables NOT requiring separate RLS** (cascade isolation via FK to Comprobante):
- `facturacion_aliciva`
- `facturacion_tributo`
- `facturacion_cbteasoc`

**Constitution II justification**: These child tables lack `tenant_id` by design — they are only accessible through their parent Comprobante, which enforces RLS. All queries to these tables join through `comprobante_id` FK, inheriting the tenant isolation of the parent. This is a deliberate architectural choice to avoid redundant tenant_id columns on line-item tables, consistent with the cascade isolation pattern.

---

## Migration Strategy

Single initial migration (`0001_initial.py`) containing:
1. All model creation (CreateModel operations)
2. All constraints (UniqueConstraint, CheckConstraint)
3. All indexes
4. RLS policies via `RunSQL` with reverse SQL for rollback

Follow-up migrations for schema changes follow Django's standard `makemigrations` flow.
