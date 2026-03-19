# Data Model Entity Inventory: Acopio de Granos v1.0

**Branch**: `003-acopio-data-model` | **Date**: 2026-03-16
**Phase**: 1 — Pre-implementation entity catalog
**Target document**: `Docs/Project Blueprint/Data Model & Domain Model.md` v1.0

This file catalogs ALL entities that will appear in the Data Model v1.0 document. It is the authoritative entity inventory for `/speckit.tasks` and implementation specs (09+).

---

## Entity Catalog by Module

### A. Core Infrastructure (PRESERVED from v0.3)

| Entity | Fields | Key Relationships | Document Section |
|--------|--------|-------------------|-----------------|
| `Tenant` | 8 | Root of all tenant-scoped data | §4.1 |
| `Branch` | 7 | Tenant → Branch (1:N) | §4.1 |
| `TenantFieldDefinition` | 8 | Tenant → TFD (1:N) | §4.1 |
| `TenantModuleConfig` | 5 | Tenant → TMC (1:N) | §4.1 |
| `BusinessTemplate` | 5 | No tenant FK (global) | §4.1 |
| `AppUser` | 9 | Tenant + Role → AppUser | §4.2 |
| `Role` | 5 | Tenant → Role (1:N) | §4.2 |
| `TenantBoundModel` | 5 | Abstract base for all tenant-scoped entities | §4.3 |

### B. Grain Domain — Reference Data (NEW)

| Entity | Fields | Key Relationships | Document Section |
|--------|--------|-------------------|-----------------|
| `GrainType` | 8 | Global (no tenant FK); referenced by many grain entities | §5.1 |
| `CampanaConfig` | 6 | Tenant-scoped; 1 active per tenant at a time | §5.1 |
| `ToleranceTable` | 7 | GrainType → ToleranceTable (1:N, versioned) — GLOBAL | §5.2 |
| `MermaTable` | 6 | GrainType → MermaTable (1:N, versioned) — GLOBAL | §5.2 |

### C. Grain Domain — Reception (NEW)

| Entity | Fields | Key Relationships | Document Section |
|--------|--------|-------------------|-----------------|
| `Romaneo` | 30+ | Hub: links to CPE, QualityAnalysis, MermaCalculation, StorageUnit, ProducerAccount | §5.3 |
| `QualityAnalysis` | 12 | Romaneo 1:1 (ON DELETE CASCADE) | §5.4 |
| `MermaCalculation` | 17 | Romaneo 1:1 (ON DELETE CASCADE); immutable | §5.5 |
| `CPE` | 7 | Romaneo 1:1 (ON DELETE CASCADE) | §5.7 |

### D. Grain Domain — Storage (NEW)

| Entity | Fields | Key Relationships | Document Section |
|--------|--------|-------------------|-----------------|
| `StorageUnit` | 7 | Branch → StorageUnit (1:N) | §5.6 |
| `GrainLot` | 8 | StorageUnit + GrainType + CampanaConfig → GrainLot | §5.6 |
| `GrainMovement` | 6 | GrainLot 1:N; append-only ledger | §5.6 |

### E. Grain Domain — Equipment (NEW)

| Entity | Fields | Key Relationships | Document Section |
|--------|--------|-------------------|-----------------|
| `WeighbridgeDevice` | 6 | Branch → WeighbridgeDevice (1:N) | §5.8 |
| `WeighbridgeCalibration` | 7 | WeighbridgeDevice → Calibrations (1:N) | §5.8 |

### F. Producer Accounts (NEW)

| Entity | Fields | Key Relationships | Document Section |
|--------|--------|-------------------|-----------------|
| `ProducerAccount` | 8 | Branch (per-plant); dual-ledger pattern | §6.1 |
| `AccountMovement` | 10 | ProducerAccount 1:N; append-only; 8 tx types | §6.2 |
| `FijacionRecord` | 7 | AccountMovement (CEG_DEPOSIT) + LiquidacionPrimaria | §6.3 |

### G. Agronomia / Discrete Inventory (ADAPTED from v0.3)

| Entity | Fields | Key Relationships | Document Section |
|--------|--------|-------------------|-----------------|
| `Product` | 14 | ADAPTED: +batch_number, lot_number, expiration_date, product_type | §7.1 |
| `ProductCategory` | 4 | Tenant → Category; self-referencing | §7.1 |
| `Supplier` | 6 | Tenant → Supplier | §7.1 |
| `StockMovement` | 12 | Product + Branch → StockMovement; append-only | §7.2 |

### H. Facturación (EXTENDED from v0.3)

| Entity | Fields | Key Relationships | Document Section |
|--------|--------|-------------------|-----------------|
| `Comprobante` | 20+ | PRESERVED; service invoices to producers | §8.1 |
| `AlicIva` | 4 | Comprobante → AlicIva | §8.1 |
| `Tributo` | 4 | Comprobante → Tributo | §8.1 |
| `CbteAsoc` | 3 | Comprobante → CbteAsoc | §8.1 |
| `ArcaCredential` | 6 | Tenant → ArcaCredential | §8.1 |
| `PuntoDeVenta` | 4 | Tenant → PuntoDeVenta | §8.1 |
| `CAEA` | 5 | Tenant → CAEA | §8.1 |
| `LiquidacionPrimaria` | 18 | NEW; grain settlement Form 1116-C; 5-state machine | §8.2 |
| `CanjeOperation` | 8 | NEW; LPG + Comprobante dual FK; canje workflow | §8.4 |

### I. Sync (PRESERVED from v0.3)

| Entity | Fields | Key Relationships | Document Section |
|--------|--------|-------------------|-----------------|
| `SyncSession` | 8 | PRESERVED | §9 |
| `PendingOperation` | 7 | PRESERVED | §9 |

---

## Entity Count Summary

| Module | New | Adapted | Preserved | Total |
|--------|-----|---------|-----------|-------|
| Core Infrastructure | 0 | 0 | 8 | 8 |
| Grain Domain (Reference) | 4 | 0 | 0 | 4 |
| Grain Domain (Reception) | 4 | 0 | 0 | 4 |
| Grain Domain (Storage) | 3 | 0 | 0 | 3 |
| Grain Domain (Equipment) | 2 | 0 | 0 | 2 |
| Producer Accounts | 3 | 0 | 0 | 3 |
| Agronomia | 0 | 1 | 3 | 4 |
| Facturación | 2 | 0 | 7 | 9 |
| Sync | 0 | 0 | 2 | 2 |
| **TOTAL** | **18** | **1** | **20** | **39** |

---

## Key Cross-Module Relationships

| Source Entity | Target Entity | FK Field | ON DELETE | Purpose |
|--------------|--------------|----------|-----------|---------|
| Romaneo | ProducerAccount | producer_account | PROTECT | Romaneo creates CEG_DEPOSIT AccountMovement |
| Romaneo | StorageUnit | storage_unit | PROTECT | Grain assigned to silo |
| Romaneo | GrainLot | grain_lot | PROTECT | Romaneo feeds a grain lot |
| CPE | Romaneo | romaneo | CASCADE | 1:1 lifecycle companion |
| QualityAnalysis | Romaneo | romaneo | CASCADE | 1:1 satellite |
| MermaCalculation | Romaneo | romaneo | CASCADE | 1:1 immutable record |
| GrainMovement | Romaneo | romaneo | PROTECT | Deposit movement |
| LiquidacionPrimaria | Romaneo | romaneo | PROTECT | Settlement of deposited grain |
| FijacionRecord | LiquidacionPrimaria | liquidacion | PROTECT | Price fixing record |
| CanjeOperation | LiquidacionPrimaria | lpg | PROTECT | Grain leg of canje |
| CanjeOperation | Comprobante | comprobante | PROTECT | Input leg of canje |
| AccountMovement | Romaneo | romaneo | PROTECT | CEG_DEPOSIT movement |
| AccountMovement | LiquidacionPrimaria | liquidacion | PROTECT | LPG_SALE movement |

---

## State Machines

### Romaneo (6 states)
PENDIENTE → EN_PROCESO → PESADO → ANALIZADO → CONFORME → CERRADO
- Immutable after CONFORME (same pattern as Comprobante AUTORIZADO)

### LiquidacionPrimaria (5 states)
DRAFT → RETENCION_CALCULADA → SISA_VERIFICADA → WSLPG_PRESENTADA → LIQUIDADA

### CPE (4 states)
ACTIVA → ARRIBO_CONFIRMADO → DESCARGADA → CONFIRMADA_DEFINITIVA
