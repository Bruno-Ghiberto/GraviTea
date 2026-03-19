# Quickstart: Data Model & Domain Model v1.0

**Document**: `Docs/Project Blueprint/Data Model & Domain Model.md` v1.0
**For**: Engineers reading the data model to implement a specific feature

---

## "I need to implement..." Navigation Guide

| Task | Go to |
|------|-------|
| Romaneo reception (weighing, grading, merma) | §5.3 (Romaneo), §5.4 (QualityAnalysis), §5.5 (MermaCalculation) |
| Silo/celda assignment and inventory | §5.6 (StorageUnit, GrainLot, GrainMovement) |
| CPE/CTG electronic waybill | §5.7 (CPE) |
| Weighbridge device + calibrations | §5.8 (WeighbridgeDevice, WeighbridgeCalibration) |
| Producer cuenta corriente | §6 (ProducerAccount, AccountMovement, FijacionRecord) |
| Price fixing (fijación) | §6.3 (FijacionRecord) |
| ARCA grain liquidation (Form 1116-C) | §8.2 (LiquidacionPrimaria), §8.3 (WSLPG field mapping) |
| Grain-for-input exchange (canje) | §8.4 (CanjeOperation) |
| Agronomia inputs (seeds, fertilizers) | §7 (Product, StockMovement) |
| Service invoicing to producers | §8.1 (Comprobante — preserved) |
| Offline sync + conflict resolution | §9 (SyncSession, PendingOperation) |
| Cross-module FK constraints | §10 (Cross-Module Links) |
| RLS policy for a new query | §11 (RLS Policies) |
| ML feature engineering | §12 (AI-Ready Data Architecture) |
| Global ERD overview | §3 |

---

## Key Formulas Quick Reference

### Merma Calculation (sequential — from §5.5)

```
%S = (Hi − Hf) / (100 − Hf) × 100   [Hf ≠ Humedad_base!]

Step 1: post_zarandeo  = neto_bruto    × (1 − zarandeo_pct/100)
Step 2: post_secado    = post_zarandeo × (1 − secado_pct/100)
Step 3: post_manipuleo = post_secado   × (1 − manipuleo_pct/100)
Step 4: peso_final     = post_manipuleo × (1 − volatil_pct/100)
```

| Grain | Hf (formula) | Humedad Base | manipuleo% | volátil% |
|-------|-------------|--------------|------------|----------|
| Trigo | 13.5% | 14.0% | 0.10% | 0.30% |
| Maiz | 13.5% | 14.5% | 0.25% | 0.30% |
| Soja | 13.0% | 13.5% | 0.25% | 0.50% |
| Girasol | 10.5% | 11.0% | 0.20% | 0.50% |
| Sorgo | 13.5% | 15.0% | 0.25% | 0.30% |

---

## Key Rules Quick Reference

| Rule | Source |
|------|--------|
| All weight/monetary fields: DECIMAL(17,3) | Constitution I + FR-019 |
| All percentage fields: DECIMAL(5,2) | FR-019 |
| No FLOAT or DOUBLE anywhere | Constitution I |
| Romaneo is immutable after CONFORME state | FR-002 |
| AccountMovement is append-only (ledger pattern) | FR-006 |
| MermaCalculation is immutable after creation | FR-013 |
| GrainType and ToleranceTable/MermaTable are GLOBAL (no tenant FK) | D-004, D-006 |
| 1 Form 1116-C = 1 grain type only (WSLPG constraint) | FR-010 |
| ProducerAccount is per-plant (not per-tenant aggregate) | FR-006 |
| Posición consolidada is a derived view, not stored | A-006 |
| Campaign format: "YYYY/YY" (7 chars, e.g., "2024/25") | FR-017 |

---

## Entity Inheritance

All grain domain entities inherit `TenantBoundModel`:

```python
# Base fields provided by TenantBoundModel:
id         UUID PK (auto)
tenant     FK(Tenant) ON DELETE PROTECT
created_at DateTimeField (auto_now_add)
updated_at DateTimeField (auto_now)
created_by FK(AppUser) ON DELETE PROTECT
```

Grain domain entities ADDITIONALLY include:
```python
device_id  CharField(max_length=50, null=True)  # offline provenance
```

Exceptions to TenantBoundModel: `GrainType`, `ToleranceTable`, `MermaTable` — these are GLOBAL reference tables with no tenant FK.

---

## Scenario: New Truck Arrival (End-to-End Data Flow)

```
1. Truck arrives → CREATE Romaneo (status=PENDIENTE, ts_entrada=now)
2. CPE confirmed → CREATE CPE (status=ACTIVA) 1:1 with Romaneo
                   UPDATE Romaneo status=EN_PROCESO, ts_pesada_bruta=now
3. Weigh truck  → SET Romaneo.peso_bruto_kg (from WeighbridgeDevice)
                  UPDATE Romaneo status=PESADO, ts_pesada_bruta recorded
4. Lab sample   → SET Romaneo ts_calado=now; ANALIZAR sample
5. Lab results  → CREATE QualityAnalysis (humedad, materias_extranas, ...)
                  UPDATE Romaneo status=ANALIZADO, ts_analisis=now
6. Grain unloads → UPDATE Romaneo storage_unit, grain_lot, ts_descarga=now
7. Calc merma   → CREATE MermaCalculation (immutable, all intermediate steps)
                  UPDATE Romaneo peso_neto_conforme_kg, status=CONFORME
8. Romaneo CONFORME → CREATE AccountMovement(type=CEG_DEPOSIT, grain_lot, kg_amount)
                      CREATE GrainMovement(type=DEPOSIT, romaneo, quantity_kg)
9. CPE final    → UPDATE CPE status=DESCARGADA, then CONFIRMADA_DEFINITIVA
                  UPDATE Romaneo status=CERRADO, ts_tara=now
```
