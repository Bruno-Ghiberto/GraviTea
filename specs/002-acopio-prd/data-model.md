# Data Model: Acopio PRD

**Feature**: `002-acopio-prd`
**Date**: 2026-03-16
**Purpose**: Entity definitions for `Docs/Project Blueprint/PRD.md` §4 Module Specifications.
These entities are DESCRIBED by the PRD — they are not implemented in this feature branch.
Implementation specs (spec-03 Data Model, spec-09+) will derive Django models from these.

---

## Overview

The PRD describes 6 core entities and 6 supporting entities. All entities inherit
`TenantBoundModel` (tenant_id + branch_id isolation, PostgreSQL RLS). Financial fields
use `DECIMAL(17, 3)` exclusively. Ledger entities (Romaneo, Cuenta Corriente) are
append-only (no UPDATE/DELETE on committed records).

```
Romaneo ──────────── CPE (Carta de Porte Electrónica)
    │                     1:1 bijection
    ├── MermaCalculation  (1:1 per romaneo)
    ├── SiloAssignment    (M:1 to Silo/Celda)
    └── CuentaCorrienteEntry (via CEG issuance)

CuentaCorriente ────── LiquidacionPrimaria (via fijación or direct sale)
    │                       │
    │                       └── RetencioesCalculadas (retention breakdown)
    └── CanjeLeg          (grain debit + input offset)

Silo ──────────────── GrainLot (composite key: plant + grain + campaign + producer)
```

---

## Core Entity 1: Romaneo (Weighing Ticket)

**Description**: The atomic grain reception transaction. Created when a truck arrives
at the plant. Drives all downstream operations (quality, storage, account, CPE).

**Module**: RECEPCIÓN

| Field | Type | Required | Source | Notes |
|-------|------|----------|--------|-------|
| id | UUID | ✅ | System | PK |
| tenant_id | UUID FK → Tenant | ✅ | Auth context | RLS partition key |
| branch_id | UUID FK → Branch | ✅ | Auth context | Physical plant |
| campaign_year | String(7) | ✅ | Config | Format "YYYY/YY" e.g. "2025/26" |
| grain_code | String(3) | ✅ | Driver/CPE | ARCA grain type code |
| cpe_number | String(20) | ✅ | ARCA WSCPE | Carta de Porte Electrónica number |
| ctg_number | String(12) | ✅ | ARCA WSCPE | 12-digit traceability code |
| truck_plate | String(10) | ✅ | Driver | Argentine license plate |
| driver_name | String(100) | ✅ | Driver | |
| producer_cuit | String(11) | ✅ | CPE | 11-digit; stored encrypted (AES-256-GCM) |
| remitente_cuit | String(11) | ✅ | CPE | Origin party CUIT |
| peso_bruto_kg | DECIMAL(17,3) | ✅ | Primary scale | Set on EN_PROCESO → PESADO |
| tara_kg | DECIMAL(17,3) | ✅ | Secondary scale / stored / manual | Set on PESADO |
| peso_neto_kg | DECIMAL(17,3) | ✅ | Calculated | `peso_bruto_kg − tara_kg` |
| merma_id | UUID FK → MermaCalculation | ✅ on ANALIZADO | CALIDAD module | |
| peso_neto_conforme_kg | DECIMAL(17,3) | ✅ on ANALIZADO | From merma | After all deductions |
| silo_assignment_id | UUID FK → SiloAssignment | ✅ on CONFORME | Operator | |
| state | Enum | ✅ | System | PENDIENTE/EN_PROCESO/PESADO/ANALIZADO/CONFORME/CERRADO |
| romaneo_datetime | DateTimeField | ✅ | System | Timestamp of romaneo creation |
| cerrado_datetime | DateTimeField | ❌ | System | Set on CERRADO |
| cpe_queue_status | Enum | ✅ | System | PENDING/SENT/CONFIRMED (for offline store-and-forward) |

**State Machine**:
```
PENDIENTE → EN_PROCESO → PESADO → ANALIZADO → CONFORME → CERRADO
              (confirmarArriboCPE queued)                 (descargadoDestinoCPE +
                                                           confirmacionDefinitivaCPEAutomotor queued)
```

**Invariants**:
- peso_neto_kg = peso_bruto_kg − tara_kg (system enforces; never manual)
- peso_neto_conforme_kg ≤ peso_neto_kg (merma only reduces)
- peso_neto_conforme_kg > 0 (reject if ≤ 0 — NFR-EDGE-07)
- State transitions are sequential and irreversible (CERRADO is terminal)
- 1 CPE = 1 Romaneo (bijection enforced by ARCA + application)

---

## Core Entity 2: MermaCalculation

**Description**: Sequential grain loss calculation per romaneo. All four steps stored
individually for audit trail. Implements CAC Circular 10/86 + Resolución JNG N° 22027/81.

**Module**: CALIDAD

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID | ✅ | PK |
| romaneo_id | UUID FK → Romaneo | ✅ | 1:1 |
| grain_code | String(3) | ✅ | Copy from romaneo |
| humidity_incoming_pct | DECIMAL(5,2) | ✅ | Hi — lab measurement |
| humidity_base_pct | DECIMAL(5,2) | ✅ | Hf — from grain type config |
| grade_or_rebaja | String(20) | ✅ | "Grado 1/2/3" for cereals; "Rebaja X%" for oleaginosas |
| zarandeo_pct | DECIMAL(5,3) | ✅ | % deduction step 1 |
| zarandeo_kg | DECIMAL(17,3) | ✅ | Calculated |
| peso_after_zarandeo_kg | DECIMAL(17,3) | ✅ | Calculated |
| secado_pct | DECIMAL(5,3) | ✅ | `(Hi − Hf) / (100 − Hf)` |
| secado_kg | DECIMAL(17,3) | ✅ | Calculated |
| peso_after_secado_kg | DECIMAL(17,3) | ✅ | Calculated |
| manipuleo_pct | DECIMAL(5,3) | ✅ | Fixed per grain: trigo=0.10%, maíz/soja=0.25%, girasol=0.20% |
| manipuleo_kg | DECIMAL(17,3) | ✅ | Calculated |
| peso_after_manipuleo_kg | DECIMAL(17,3) | ✅ | Calculated |
| volatil_pct | DECIMAL(5,3) | ✅ | Fixed per grain type: cereales=0.30%, oleaginosas=0.50% |
| volatil_kg | DECIMAL(17,3) | ✅ | Calculated |
| peso_neto_conforme_kg | DECIMAL(17,3) | ✅ | Final result |
| tolerance_table_version | String | ✅ | Configurable table identifier used (for audit) |
| created_at | DateTimeField | ✅ | System |

**Formula** (verified against CAC 10/86):
```
peso_neto_conforme = peso_neto × (1−%Z) × (1−%S) × (1−%M) × (1−%V)
```

**Invariants**:
- All four steps computed in order; no step may be skipped
- Final result must be > 0 (NFR-EDGE-07)
- Immutable once romaneo reaches ANALIZADO (append-only; corrections via new entry)

---

## Core Entity 3: ProducerCuentaCorriente

**Description**: Per-plant dual ledger for a producer. The source of truth for grain
holdings and monetary position. Append-only (ledger pattern).

**Module**: CUENTAS CORRIENTES

### Grain Sub-Ledger Entry

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID | ✅ | PK |
| tenant_id | UUID FK | ✅ | RLS partition |
| branch_id | UUID FK | ✅ | Physical plant |
| producer_cuit_encrypted | EncryptedField | ✅ | AES-256-GCM |
| producer_cuit_blind_idx | HMAC | ✅ | For CUIT lookup |
| grain_code | String(3) | ✅ | Grain type |
| campaign_year | String(7) | ✅ | e.g. "2025/26" |
| transaction_type | Enum | ✅ | CEG_DEPOSIT / LPG_SALE / FIJACION / RETIRO / SERVICE_CHARGE / CANJE_DEBIT |
| kg_delta | DECIMAL(17,3) | ✅ | + for deposits; − for sales/withdrawals |
| document_reference | String | ✅ | CEG number / LPG number / etc. |
| romaneo_id | UUID FK → Romaneo | ❌ | For CEG entries |
| transaction_datetime | DateTimeField | ✅ | |
| notes | Text | ❌ | |

### Monetary Sub-Ledger Entry

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID | ✅ | PK |
| tenant_id / branch_id | UUID FK | ✅ | RLS |
| producer_cuit_encrypted | EncryptedField | ✅ | |
| producer_cuit_blind_idx | HMAC | ✅ | |
| currency | Enum | ✅ | ARS / USD |
| amount_delta | DECIMAL(17,3) | ✅ | + = credit; − = debit |
| transaction_type | Enum | ✅ | LPG_PROCEEDS / FIJACION_PROCEEDS / SERVICE_CHARGE / RETENTION / CANJE_OFFSET |
| document_reference | String | ✅ | |
| transaction_datetime | DateTimeField | ✅ | |

**Posición consolidada** (derived, not stored):
```
SELECT branch_id, SUM(kg_delta) AS kg_balance, campaign_year, grain_code
FROM grain_ledger
WHERE tenant_id = :tenant_id AND producer_cuit = :cuit
GROUP BY branch_id, grain_code, campaign_year
```
Cross-plant aggregation = SUM across all branch_ids of same tenant for same CUIT.

---

## Core Entity 4: LiquidacionPrimaria (Settlement Document)

**Description**: Form 1116-C (Primaria) or 1116-B (Secundaria). Fiscal settlement
document filed via WSLPG. Triggered by immediate sale or fijación event.

**Module**: LIQUIDACIONES

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID | ✅ | PK |
| tenant_id / branch_id | UUID FK | ✅ | RLS |
| form_type | Enum | ✅ | PRIMARIA_1116C / SECUNDARIA_1116B |
| producer_cuit_encrypted | EncryptedField | ✅ | |
| grain_code | String(3) | ✅ | |
| campaign_year | String(7) | ✅ | |
| kg_quantity | DECIMAL(17,3) | ✅ | Net peso neto conforme |
| price_per_ton | DECIMAL(17,3) | ✅ | Pizarra price at fixing date or sale date |
| gross_amount | DECIMAL(17,3) | ✅ | kg × price_per_ton / 1000 |
| sisa_estado | Enum | ✅ | ESTADO_1 / ESTADO_2 / ESTADO_3 / NON_REGISTERED |
| iva_retention_pct | DECIMAL(5,2) | ✅ | 5/8/10.5/16 per SISA estado (RG 2300) |
| iva_retention_amount | DECIMAL(17,3) | ✅ | |
| ganancias_retention_pct | DECIMAL(5,2) | ✅ | 0/2/15/30 per SISA estado (RG 4325) |
| ganancias_retention_amount | DECIMAL(17,3) | ✅ | |
| iibb_retention_pct | DECIMAL(5,2) | ✅ | Per-province; configurable |
| iibb_retention_amount | DECIMAL(17,3) | ✅ | |
| service_charges_total | DECIMAL(17,3) | ✅ | Sum of secada + zarandeo + almacenaje + paritaria |
| net_payable | DECIMAL(17,3) | ✅ | gross − all retentions − service_charges |
| state | Enum | ✅ | DRAFT / RETENCION_CALCULADA / SISA_VERIFICADA / WSLPG_PRESENTADA / LIQUIDADA |
| sisa_query_datetime | DateTimeField | ❌ | Timestamp of SISA status query (blocking gate) |
| wslpg_response | JSONB | ❌ | ARCA WSLPG filing response |
| ceg_id | UUID FK | ✅ | Source grain deposit |
| fijacion_record_id | UUID FK | ❌ | If triggered by fijación event |
| created_at | DateTimeField | ✅ | |

**State Machine**:
```
DRAFT → RETENCION_CALCULADA → SISA_VERIFICADA → WSLPG_PRESENTADA → LIQUIDADA
                                    ↑ BLOCKED if SISA fails
```

**Invariants**:
- WSLPG_PRESENTADA and LIQUIDADA are immutable (fiscal ledger)
- net_payable = gross_amount − iva_retention − ganancias_retention − iibb_retention − service_charges
- SISA_VERIFICADA is a mandatory gate (cannot skip to WSLPG_PRESENTADA without it)

---

## Core Entity 5: Silo / Celda (Storage Unit)

**Description**: Physical or logical storage unit at an acopio plant.

**Module**: ALMACENAMIENTO

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID | ✅ | PK |
| tenant_id / branch_id | UUID FK | ✅ | RLS |
| identifier | String(20) | ✅ | Human label: "Silo 1", "Celda A", "Silo Húmedo" |
| storage_type | Enum | ✅ | VERTICAL_SILO / HORIZONTAL_CELL / WET_BIN |
| capacity_tons | DECIMAL(17,3) | ✅ | Max capacity |
| state | Enum | ✅ | ACTIVE / MAINTENANCE / FULL / EMPTY |

**GrainLot** (grain position within a Silo):

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| silo_id | UUID FK | ✅ | |
| grain_code | String(3) | ✅ | Grain type |
| campaign_year | String(7) | ✅ | Logical campaign segregation |
| producer_cuit | String(11) | ❌ | Per-producer tracking (when segregated) |
| current_kg | DECIMAL(17,3) | ✅ | Running balance; updated by romaneo + movements |
| quality_grade | String(10) | ❌ | Quality/grade of grain in this lot |
| last_updated | DateTimeField | ✅ | |

**Composite key for grain position**: `(branch_id, grain_code, campaign_year)` — mirrors AFIP (RG 3593).

---

## Core Entity 6: CPE (Carta de Porte Electrónica)

**Description**: Electronic waybill tracking grain transport. 1 CPE = 1 truck = 1 Romaneo.
Managed by ARCA WSCPE web service.

**Module**: RECEPCIÓN (integration layer)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID | ✅ | PK |
| tenant_id / branch_id | UUID FK | ✅ | RLS |
| romaneo_id | UUID FK → Romaneo | ✅ | Bijection |
| cpe_number | String(20) | ✅ | ARCA-assigned |
| ctg_number | String(12) | ✅ | ARCA-assigned |
| state | Enum | ✅ | BORRADOR/ACTIVA/ACTIVA_CON_CONTINGENCIA/ARRIBO/DESCARGADA/CONFIRMADA_DEFINITIVA/ANULADA/RECHAZADA |
| valid_until | DateTimeField | ✅ | Now + 5 days for Automotor (120h) |
| arca_response | JSONB | ❌ | Raw WSCPE response per state change |
| pending_queue | JSONB | ❌ | Offline queue: method + payload |
| created_at | DateTimeField | ✅ | |

---

## Supporting Entity 7: CampañaConfig (Campaign Year Config)

| Field | Type | Notes |
|-------|------|-------|
| tenant_id / branch_id | UUID FK | RLS |
| campaign_year | String(7) | "2025/26" |
| grain_code | String(3) | Grain type |
| is_active | Boolean | Current receiving campaign for this grain |
| carry_stock_report_generated | Boolean | Flag: carry-stock report produced at transition |

---

## Supporting Entity 8: FijacionRecord (Price-Fixing Event)

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| tenant_id / branch_id | UUID FK | RLS |
| producer_cuit_encrypted | EncryptedField | |
| grain_code / campaign_year | String | |
| kg_fixed | DECIMAL(17,3) | Grain quantity being fixed |
| pizarra_price | DECIMAL(17,3) | Current market price at fixing moment |
| fixed_at | DateTimeField | When fijación was recorded |
| requested_by | String | Producer reference |
| ceg_id | UUID FK | Source deposit |
| lpg_id | UUID FK | Generated settlement |

---

## Supporting Entity 9: CanjeOperation (Grain-for-Input Exchange)

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| tenant_id / branch_id | UUID FK | RLS |
| producer_cuit_encrypted | EncryptedField | |
| grain_code / campaign_year | String | Grain being exchanged |
| kg_exchanged | DECIMAL(17,3) | Grain quantity |
| pizarra_price | DECIMAL(17,3) | Grain valuation price |
| grain_value_ars | DECIMAL(17,3) | kg × price |
| input_invoice_amount_ars | DECIMAL(17,3) | Input sale invoice amount |
| net_balance_ars | DECIMAL(17,3) | grain_value − input_invoice (residual) |
| lpg_id | UUID FK | Grain purchase LPG |
| invoice_id | UUID FK → Comprobante | Input sale invoice (ARCA) |
| canje_type | Enum | TOTAL / PARCIAL |
| created_at | DateTimeField | |

---

## Supporting Entity 10: InsumoCatalog (Agronomía Product)

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| tenant_id | UUID FK | RLS |
| name | String(200) | Product name |
| category | Enum | SEED / FERTILIZER / AGROQUIMICO / REPUESTO / FUEL |
| unit | Enum | KG / LITER / UNIT |
| current_price | DECIMAL(17,3) | ARS per unit |
| stock_quantity | DECIMAL(17,3) | Discrete units (not continuous kg) |
| lot_number | String | Lot traceability |
| expiry_date | Date | Mandatory for agroquímicos and fertilizers |

---

## Supporting Entity 11: WeighbridgeCalibration

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| tenant_id / branch_id | UUID FK | RLS |
| scale_identifier | String(20) | "Primary Scale", "Secondary Scale" |
| last_calibration_date | Date | |
| certificate_number | String(50) | |
| next_due_date | Date | System alerts when approaching |
| calibrating_authority | String(100) | INTA/SENASA/INPM accredited entity |

---

## Entity Relationship Summary

```
Tenant
 └── Branch (Plant)
      ├── Romaneo ─── CPE (1:1)
      │    └── MermaCalculation (1:1)
      ├── SiloAssignment ─── Silo/Celda
      │                       └── GrainLot (grain position)
      ├── ProducerCuentaCorriente
      │    ├── GrainLedgerEntry (per romaneo → CEG)
      │    └── MonetaryLedgerEntry (per LPG/service/canje)
      ├── LiquidacionPrimaria ─── FijacionRecord
      ├── CanjeOperation ─── InsumoCatalog
      ├── CampañaConfig
      └── WeighbridgeCalibration
```
