# Quickstart: Acopio PRD

**Feature**: `002-acopio-prd`
**Date**: 2026-03-16
**Purpose**: Reading guide for `Docs/Project Blueprint/PRD.md` v1.0 — helps each
persona find their content, explains key concepts, and shows how PRD sections
connect to downstream specs.

---

## What This Document Is

`Docs/Project Blueprint/PRD.md` v1.0 is the **Product Requirements Document** for
GRAVITEA's acopio de granos vertical. It specifies WHAT the system does and HOW MUCH
in functional detail.

- **Not a sales document** — see `Product Vision & Scope.md` for market, personas, and pricing
- **Not a data model** — see spec-03 for PostgreSQL schema
- **Not an implementation guide** — see spec-09+ for code

---

## Navigation by Persona

### Balancero / Recibidor (Scale Operator)
**Start**: §4.1 RECEPCIÓN → §7 Hardware Integration → §5.1 Operational Flow

Key questions answered:
- What data do I capture during a romaneo? → §4.1 Data Capture table
- How does offline operation work? → §8.1 Online/Offline Matrix
- How does the weighbridge integrate? → §7 Hardware Integration
- What state is the romaneo in? → §4.1 State Machine

---

### Laboratorista (Lab Analyst)
**Start**: §4.2 CALIDAD → §5.1 Operational Flow (step 7-9)

Key questions answered:
- What quality parameters do I capture per grain type? → §4.2 Feature List
- What is the merma formula? → §4.2 Merma Calculation section
- How do cereals and oleaginosas differ in grading? → §4.2 Two Grading Systems note
- How do I provide the audit trail if a producer disputes? → §4.2 Audit Trail note

---

### Administrador / Contable (Admin / Accountant)
**Start**: §4.5 LIQUIDACIONES → §6 Regulatory Compliance → §4.4 CUENTAS CORRIENTES

Key questions answered:
- What retentions do I apply and at what rates? → §6.4 Retention Calculation Reference
- How does SISA status affect settlement? → §6.3 SISA Compliance + §4.5 Blocking Gate
- How do I file Form 1116-C? → §4.5 LIQUIDACIONES + §6.2 WSLPG
- What is SICORE and when do I file it? → §6.2 WSLPG Filing

---

### Dueño / Gerente (Owner / Manager)
**Start**: §9 Phased Delivery → §4.4 CUENTAS CORRIENTES (posición consolidada) → §4.1 Throughput

Key questions answered:
- What is in Phase 1 MVP? → §9 Phase 1 scope + exit criteria
- How do I see my grain position from mobile? → §4.4 Posición consolidada
- What throughput metrics are tracked? → §8.2 Performance NFRs (trucks/hour)
- When can I expect each module? → §9 Phase schedule

---

### Contador Rural (Rural Accountant)
**Start**: §4.5 LIQUIDACIONES → §6 Regulatory Compliance → §8 NFRs

Key questions answered:
- How are retentions calculated per client? → §6.4 Retention tables
- Can I verify retention calculations for compliance? → §4.5 SISA blocking gate
- What fiscal exports are available? → §4.5 SICORE magnetic file
- How does the offline architecture affect data integrity? → §8 NFRs

---

## Key Concepts

### Romaneo (Weighing Ticket)
The atomic transaction in acopio. Every truck arrival creates one romaneo. It drives:
- Quality grading (CALIDAD reads romaneo)
- Storage assignment (ALMACENAMIENTO reads romaneo)
- Producer account credit (CUENTAS CORRIENTES reads romaneo → CEG issued)
- CPE closure (RECEPCIÓN calls WSCPE)

### Merma (Grain Loss)
The % deduction from gross weight applied in mandatory sequential order:
1. Zarandeo (sieving impurities)
2. Secado (drying to base humidity)
3. Manipuleo (handling loss)
4. Volátil (residual moisture)

The **peso neto conforme** (certified net weight) is the final weight after all four steps.
This is the weight used for settlement, account credit, and fiscal documents.

### CPE / CTG (Electronic Waybill)
Mandatory for every grain truck movement. Issued before departure by origin.
The acopio confirms arrival and then closes it definitively at the end of the romaneo.
Without CPE confirmation, the CTG validity expires in 5 days.

### "A Fijar" (Price to Be Fixed)
Grain deposited without a price. The producer can "fix" the price later.
During storage, this grain is in the account at zero monetary value.
When the producer calls to fix: administrador records the pizarra price → LPG issued.

### SISA (Sistema de Información Simplificado Agrícola)
ARCA's producer compliance scoring system. Producers are classified Estado 1/2/3 or
non-registered. Each Estado maps to different IVA and Ganancias retention rates.
The system must query SISA before issuing any settlement — this is a **blocking gate**.

### Posición Consolidada
A cross-plant view of a producer's account. The per-plant ledger is the source of truth.
The posición consolidada sums all per-plant balances for the same producer CUIT across
all plants of the same tenant. Only visible to Dueño/Gerente role.

---

## PRD Section Map (§1–§10)

| Section | Content | Primary Audience |
|---------|---------|-----------------|
| §1 Metadata | Version, status, implementation progress reference | All |
| §2 Introduction + Glossary | Purpose, domain terms | New team members, AI agents |
| §3 Functional Decomposition | Module map, dependency graph, impl status table | Engineers |
| §4.1 RECEPCIÓN | Romaneo lifecycle, weighbridge, CPE | Balancero, Engineers |
| §4.2 CALIDAD | Quality grading, merma formula, audit trail | Laboratorista, Engineers |
| §4.3 ALMACENAMIENTO | Silo management, grain position, campaign | Engineers |
| §4.4 CUENTAS CORRIENTES | Dual ledger, CEG/LPG, "a fijar", posición | Dueño, Administrador |
| §4.5 LIQUIDACIONES | Form 1116-C/B, retention tables, SISA gate | Administrador, Contador |
| §4.6 FACTURACIÓN | Service invoicing (reuses branch 001 ARCA) | Administrador |
| §4.7 AGRONOMÍA | Input catalog, discrete inventory | Administrador |
| §4.8 CANJE | Grain-for-input exchange, LPG + invoice | Administrador |
| §5 Operational Workflows | Romaneo flow (11 steps), fijación flow, campaign | Engineers, AI agents |
| §6 Regulatory Compliance | CPE/CTG, WSLPG, SISA, retention tables | Administrador, Contador |
| §7 Hardware Integration | Weighbridge RS-232/TCP, dual-scale | Engineers, Infrastructure |
| §8 NFRs | Offline matrix, performance, security, edge cases | Engineers, QA |
| §9 Phased Delivery | 4 phases with entry/exit criteria | Dueño, Engineers |
| §10 Implementation Foundation | Existing infrastructure (branches 001-025) | Engineers |

---

## Common Entry Points for AI Agents

When using the PRD to implement a module, start here:

```text
Implementing RECEPCIÓN:
  Read §4.1 (state machine + data fields)
  Read §5.1 (romaneo operational flow — 11 steps)
  Read §6.1 (CPE/CTG integration — WSCPE methods)
  Read §7 (weighbridge interface)
  Read §8.1 (offline matrix for RECEPCIÓN operations)

Implementing CALIDAD:
  Read §4.2 (two grading systems + merma formula)
  Read research.md §4.2 for fixed merma values

Implementing CUENTAS CORRIENTES:
  Read §4.4 (dual ledger + fijación mechanics)
  Read §5.2 (fijación workflow)
  Read data-model.md entities 3, 8 (ProducerCuentaCorriente, FijacionRecord)

Implementing LIQUIDACIONES:
  Read §4.5 (retention tables + SISA blocking gate)
  Read §6.2-§6.4 (WSLPG + SISA + retention reference tables)
  Read data-model.md entity 4 (LiquidacionPrimaria state machine)
```

---

## How to Validate the PRD Is Complete

Run these quick checks after writing:

```bash
# SC-008: Zero retail language
grep -i "cajero\|cashier\|ferretería\|PyMEs minoristas\|punto de venta" \
  "Docs/Project Blueprint/PRD.md"
# Expected: 0 results

# SC-003: All regulatory citations have RG + year
grep -i "RG [0-9]" "Docs/Project Blueprint/PRD.md" | wc -l
# Expected: ≥ 10 lines

# SC-007: Feature branch history preserved
grep "001-sal-invo-inve-backend" "Docs/Project Blueprint/PRD.md"
# Expected: present (from §10)

# SC-006: Mermaid diagrams present
grep -c '```mermaid' "Docs/Project Blueprint/PRD.md"
# Expected: ≥ 5

# SC-002: User stories (15 minimum)
grep -c "Given\|Dado que" "Docs/Project Blueprint/PRD.md"
# Expected: ≥ 15
```

---

## Downstream Dependencies

This PRD unblocks the following specifications:

| Spec | Dependency |
|------|-----------|
| spec-03 Data Model | Entity definitions from §4 Module Specifications |
| spec-04 ADRs | Architecture decisions from §3, §5-§8 |
| spec-07 Roadmap | Phase allocation from §9 |
| spec-08a ARCA Grain Guide | CPE/CTG + WSLPG specs from §6 |
| spec-08b AI/ML Roadmap | Phase 4 AI features from §9 |
| spec-08c SRS | Hardware interface specs from §7 (weighbridge) |
| spec-09+ Implementation | All module specs from §4 |
