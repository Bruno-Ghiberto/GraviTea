# Data Model: New ARCA Docs — Blueprint Knowledge Update

**Branch**: `009-new-arca-docs` | **Date**: 2026-03-18
**Scope**: One new entity documented in this spec. No existing entities are modified.
**Target document**: `Docs/Project Blueprint/Data Model & Domain Model.md`

---

## New Entity: CertificadoDepositoCereal

### Purpose

Represents the WSCDC grain deposit certificate issued by ARCA upon grain reception at the acopiador establishment. Created at romaneo reception time, concurrent with WSCPE CPE confirmation. Satisfies ARCA legal obligation for registered acopiadores (FR-005, FR-014).

### Module Assignment

`gravitea_acopio` — per constitution §III Modular Architecture (acopio module covers grain reception).

### Relationship

```text
Romaneo  1 ──────────────── 0..1  CertificadoDepositoCereal
         (romaneo_id FK, UNIQUE)
```

One romaneo reception triggers at most one WSCDC certificate. The certificate may be in `Pendiente` state if the ARCA call failed and is awaiting retry.

### Field Definitions

| Field | DB Type | Nullable | Constraints | Description |
|-------|---------|----------|-------------|-------------|
| `id` | UUID | No | PRIMARY KEY | Internal primary key |
| `tenant_id` | UUID | No | FK → Tenant, ON DELETE RESTRICT | Multi-tenant isolation (RLS enforced) |
| `romaneo_id` | UUID | No | FK → Romaneo, ON DELETE RESTRICT, UNIQUE | Reception record that triggered this certificate |
| `arca_nro_certificado` | VARCHAR(50) | Yes | | Certificate number returned by WSCDC (null until ARCA accepts) |
| `especie` | VARCHAR(10) | No | | Grain species code per ARCA catalog |
| `kg_bruto` | DECIMAL(17,3) | No | CHECK(kg_bruto > 0) | Gross kg received at establishment |
| `kg_neto` | DECIMAL(17,3) | No | CHECK(kg_neto > 0 AND kg_neto <= kg_bruto) | Net kg after merma/drying |
| `humedad_percent` | DECIMAL(5,2) | No | CHECK(humedad_percent >= 0 AND humedad_percent <= 100) | Humidity percentage at reception |
| `establecimiento_id` | VARCHAR(50) | No | | ARCA-registered establishment identifier |
| `fecha_ingreso` | DATE | No | | Date of grain reception at establishment |
| `estado` | VARCHAR(20) | No | CHECK IN ('Pendiente', 'Emitido', 'Anulado') | WSCDC certificate lifecycle state |
| `wscdc_response_raw` | JSONB | Yes | | Full WSCDC API response stored for audit |
| `created_at` | TIMESTAMPTZ | No | DEFAULT NOW() | Record creation timestamp |

> **Note on field names and types**: Field names reflect spec requirements. Exact XML field names from the WSCDC WSDL (obtained via RAG Task 5) may differ from column names — the mapping is the responsibility of the `gravitea_acopio` module's WSCDC client. `DECIMAL(17,3)` is used for weight fields per constitution financial precision standard.

### State Transitions

```text
[Initial] → Pendiente   (ARCA API call failed; retry pending)
Pendiente → Emitido     (ARCA accepted; arca_nro_certificado populated)
Emitido   → Anulado     (Cancelled by acopiador via WSCDC annulment method)
Pendiente → Anulado     (Cancelled before ARCA acceptance)
```

`Emitido` and `Anulado` are terminal states. No transition from `Emitido` back to `Pendiente`.

### PostgreSQL RLS Policy (design intent)

```sql
-- Enable RLS
ALTER TABLE gravitea_acopio_certificadodepositocereal ENABLE ROW LEVEL SECURITY;

-- Tenant isolation policy
CREATE POLICY tenant_isolation ON gravitea_acopio_certificadodepositocereal
  USING (tenant_id = current_setting('app.current_tenant')::UUID);
```

### Indexes (design intent)

| Index | Columns | Type | Purpose |
|-------|---------|------|---------|
| PK | id | UNIQUE | Primary key |
| UK | romaneo_id | UNIQUE | Enforce 1-per-romaneo constraint |
| IDX | (tenant_id, estado) | BTREE | Query pending certificates for retry jobs |
| IDX | (tenant_id, fecha_ingreso) | BTREE | Date-range queries in acopio dashboard |

### Append-Only Ledger Note

`CertificadoDepositoCereal` records are NOT deleted. Cancellation creates a state transition to `Anulado`, not a DELETE. This aligns with the constitution's append-only ledger pattern for `stock_movements` and `account_ledger`.

---

## Entity Relationship Summary

```text
Tenant ──< CertificadoDepositoCereal >── Romaneo
                    |
                    └── (FK) romaneo_id (UNIQUE, CASCADE RESTRICT)
```

No other existing entities are modified in this spec.
