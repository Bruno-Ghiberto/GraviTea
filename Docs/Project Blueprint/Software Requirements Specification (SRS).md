# Software Requirements Specification (SRS) — GraviTea Acopio ERP

**Version**: 2.0
**Date**: 2026-03-18
**Status**: Approved
**Author**: Product Team

> **Note**: This document is a complete rewrite of the prior SRS (2026-03-01), which was written
> for the general-purpose retail ERP vertical. All prior content has been superseded by this
> acopio (grain-storage) vertical specification.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Overall Description](#2-overall-description)
3. [Stakeholders and Users](#3-stakeholders-and-users)
4. [Phase 1 Functional Requirements](#4-phase-1-functional-requirements)
   - 4.1 [Reception Module (RE)](#41-reception-module-re)
   - 4.2 [Quality Analysis Module (CA)](#42-quality-analysis-module-ca)
   - 4.3 [Storage & Inventory Module (AL)](#43-storage--inventory-module-al)
   - 4.4 [Producer Accounts Module (CC)](#44-producer-accounts-module-cc)
5. [Phase 2 Functional Requirements (Stubs)](#5-phase-2-functional-requirements-stubs)
6. [Interface Requirements](#6-interface-requirements)
7. [Performance Requirements](#7-performance-requirements)
8. [Security Requirements](#8-security-requirements)
9. [Data Requirements](#9-data-requirements)
10. [Constraints and Assumptions](#10-constraints-and-assumptions)
11. [Traceability Matrix](#11-traceability-matrix)
12. [Appendix: Requirement Namespace Reference](#12-appendix-requirement-namespace-reference)

---

## 1. Introduction

### 1.1 Purpose

This Software Requirements Specification defines the functional and non-functional requirements
for **GraviTea Acopio ERP**, a multi-tenant grain-storage management platform targeting
Argentine grain storage intermediaries (acopiadores). The document serves as the contract
between product stakeholders and the engineering team, establishing what the system must
accomplish before implementation begins.

This SRS covers Phase 1 (MVP) requirements in full detail and provides deferred stubs for
Phase 2 (Advanced) modules. Phase 3 (Intelligence/AI-ML) requirements are documented in
`Docs/Project Blueprint/AI-ML Feature Roadmap.md`.

### 1.2 Scope

GraviTea Acopio ERP shall provide the following capabilities in Phase 1:

- **Grain reception**: Romaneo ticketing, weighbridge integration, truck-to-cell routing
- **Quality analysis**: Multi-parameter quality capture, merma calculation, grade assignment
- **Storage management**: Cell-based inventory ledger, campaign year tracking, stock reporting
- **Producer accounts**: Current account (cuenta corriente) per producer per grain per campaign

The system shall integrate with Argentina's ARCA fiscal authority services (WSAA, WSLPG,
WSCPE, WSFEv1) and physical weighbridge hardware (RS-232, Modbus RTU, ASCII stream).

### 1.3 Definitions and Acronyms

| Term | Definition |
|------|-----------|
| Acopiador | Grain storage intermediary who receives, stores, and commercialises grain on behalf of producers |
| Romaneo | Official grain-reception weighing ticket; primary traceability document |
| CTG | Carta de Porte Granaria — grain transport certificate issued via WSLPG |
| CPE | Carta de Porte Electrónica — electronic transport document managed via WSCPE |
| COE | Código de Operación Electrónica — unique identifier assigned by WSLPG for each settlement |
| CAE | Código de Autorización Electrónico — fiscal approval code for electronic invoices |
| CAEA | CAE Anticipado — pre-assigned fiscal code for offline invoicing periods |
| Merma | Grain weight loss (moisture evaporation, foreign-matter deduction) calculated per tolerance table |
| Campaña | Crop-year marketing season (e.g., 2024/2025 for wheat harvested late 2024 through mid-2025) |
| CUIG | Código Único de Identificación de Grano — ARCA numeric grain-type identifier |
| SISA | Sistema de Información Simplificado Agrario — ARCA producer registry; determines retention tiers |
| RLS | Row-Level Security — PostgreSQL feature enforcing tenant data isolation at database layer |
| ADR | Architecture Decision Record |

### 1.4 References

| Document | Location |
|----------|----------|
| Product Vision & Scope v1.0 | `Docs/Project Blueprint/Product Vision & Scope.md` |
| PRD v1.0 | `Docs/Project Blueprint/PRD.md` |
| High-Level Design v1.0 | `Docs/Project Blueprint/High-Level Design (HLD).md` |
| ARCA Grain Integration Guide | `Docs/Project Blueprint/ARCA Grain Integration Guide.md` |
| Architecture Decision Records | `Docs/Project Blueprint/Architecture Decision Records (ADR).md` |
| REST API Design | `Docs/Project Blueprint/REST API Design.md` |
| Roadmap | `Docs/Project Blueprint/Roadmap.md` |

---

## 2. Overall Description

### 2.1 Product Context

GraviTea Acopio ERP operates within the Argentine grain-logistics ecosystem. An acopiador
receives grain from producers, stores it in physical cells (celdas/silos), and later
delivers or commercialises it. Every step generates fiscal and regulatory obligations:
grain transport certificates (CTG/CPE via ARCA), electronic invoices (via WSFEv1/CAEA),
and statistical reports to ARCA.

The system is a cloud-hosted, offline-capable SaaS application. Each tenant corresponds to
one legal entity (CUIT). Tenant data is fully isolated via PostgreSQL Row-Level Security.

### 2.2 Product Functions Summary

```text
Reception → Quality Analysis → Storage Assignment
     ↓              ↓                  ↓
  Romaneo        Merma Calc        Cell Inventory
     ↓              ↓                  ↓
  CTG/CPE       Grade Report      Stock Report
     ↓
  Producer Account (Cuenta Corriente)
     ↓
  Settlement (WSLPG) → Electronic Invoice (WSFEv1/CAEA)
```

### 2.3 User Classes and Characteristics

| Class | Technical Level | Primary Tasks |
|-------|----------------|---------------|
| Balancero | Low — touch screen in weighbridge cabin | Record truck arrivals, print romaneos |
| Recibidor | Medium — office workstation | Assign reception parameters, approve romaneos |
| Calidad | Medium | Enter lab analysis results, confirm merma |
| Gestor Comercial | Medium | Review producer accounts, approve settlements |
| Administrador del Sistema | High | Configure tenants, manage users, monitor integrations |

### 2.4 Operating Environment

- **Platform**: Web browser (desktop-first; Chrome/Firefox ≥ 2 versions behind current)
- **Offline mode**: PWA with IndexedDB; sync resumes when connectivity restores
- **Server**: Cloud VPS; PostgreSQL 18.1; Redis 7.x cache; Django 5.2 + DRF backend
- **Hardware**: RS-232/USB serial weighbridges; Modbus RTU scales; TCP/IP bridges (KYASERV)
- **Fiscal network**: ARCA SOAP services via HTTPS over public internet

---

## 3. Stakeholders and Users

### 3.1 Primary Stakeholders

| Stakeholder | Interest |
|-------------|---------|
| Acopiador owner | Regulatory compliance, operational efficiency, financial reporting |
| Producers | Accurate account statements, transparency in deductions |
| ARCA (fiscal authority) | Correct CTG/CPE/invoice filings; SISA retention enforcement |
| GraviTea (vendor) | Subscription revenue; support-ticket volume reduction |

### 3.2 Out-of-Scope Parties

- Freight companies (view-only CPE status is sufficient)
- Banks (integration planned in Phase 2)
- Insurance providers (planned in Phase 3)

---

## 4. Phase 1 Functional Requirements

### 4.1 Reception Module (RE)

**Purpose**: Manage the end-to-end truck-reception workflow from arrival to cell assignment,
generating the official Romaneo document.

---

**SRS-RE01** — Truck Arrival Registration
*Priority*: Must Have | *Source*: PRD-F-001

The system **shall** allow a balancero to register a truck arrival by capturing:
- Truck plate (patente) — alphanumeric, 6–7 characters, Argentine format
- Driver name and DNI
- Producer CUIT (11 digits, validated check-digit algorithm)
- Grain type (CUIG code; validated against master list)
- Campaign year
- CTG or CPE document number (if applicable)

*Acceptance criteria*:
- Registration completes in ≤ 3 seconds after final field entry
- Invalid CUIT check-digit is rejected with a descriptive error message
- The record receives a system-assigned Romaneo number (sequential per tenant per day)

---

**SRS-RE02** — Gross Weight Capture
*Priority*: Must Have | *Source*: PRD-F-002

The system **shall** capture gross weight from the connected weighbridge by:
(a) Real-time polling when the scale driver is available, OR
(b) Manual entry when the weighbridge is offline

*Acceptance criteria*:
- Polled weight is read automatically within 5 seconds of truck stabilisation signal
- Manual entry requires a supervisor PIN override
- Weight values are stored in kilograms with two decimal precision

---

**SRS-RE03** — Tare Weight Capture
*Priority*: Must Have | *Source*: PRD-F-002

The system **shall** capture tare weight (empty truck) by either:
(a) Automatic re-weighing after unloading, OR
(b) Lookup of the registered tare for the known truck plate

*Acceptance criteria*:
- Tare lookup returns the most recent registered value for the plate
- Net weight (bruto − tara) is computed automatically and displayed before the operator confirms

---

**SRS-RE04** — Romaneo Generation
*Priority*: Must Have | *Source*: PRD-F-003

The system **shall** generate a Romaneo PDF upon operator confirmation. The Romaneo **shall**
include: tenant name and CUIT, romaneo number, date/time, producer name and CUIT, grain type,
campaign year, truck plate, gross weight, tare weight, net weight, quality summary, merma
percentages, adjusted net weight (peso neto ajustado), and operator signature field.

*Acceptance criteria*:
- PDF generation completes in ≤ 5 seconds
- PDF layout matches the national Romaneo format (ARCA Form 8116)
- The romaneo number is unique within the tenant and the calendar day

---

**SRS-RE05** — CTG Pre-Validation
*Priority*: Must Have | *Source*: PRD-F-004; ADR-019

The system **shall** validate the CTG number against WSLPG before assigning a reception.
Validation **shall** confirm: CTG exists, CTG state is "Activo", grain type matches the
CUIG in the CTG, and the producer CUIT matches the CTG originante.

*Acceptance criteria*:
- WSLPG call completes in ≤ 10 seconds; result is cached for 5 minutes
- Mismatched grain type blocks reception with a blocking error message
- A CTG in any state other than "Activo" blocks reception with the WSLPG-returned reason

---

**SRS-RE06** — CPE Arrival Registration
*Priority*: Must Have | *Source*: PRD-F-005; WSCPE `confirmarDescargaCPE` method

The system **shall** register the arrival of a CPE-governed shipment by calling
`confirmarDescargaCPE` on WSCPE with the confirmed weight and cell assignment, transitioning
the CPE state from Activa to Descargada.

*Acceptance criteria*:
- The WSCPE call is idempotent: re-submission of the same CPE + net weight returns success
  without creating a duplicate state transition
- Failure response from WSCPE is surfaced to the operator within 15 seconds with the
  WSCPE error code and human-readable description

---

**SRS-RE07** — Romaneo Void and Correction
*Priority*: Must Have | *Source*: PRD-F-006

The system **shall** allow a supervisor to void a romaneo within the same calendar day of
issue. Voiding **shall**: mark the record as ANULADO, preserve the original data, create an
audit log entry with the supervisor's CUIT and timestamp, and prevent further processing
of any CTG/CPE linked to the voided romaneo.

*Acceptance criteria*:
- Only users with the SUPERVISOR role can execute a void
- Voided romaneos remain visible in history with "ANULADO" watermark on printed output
- Void action is irreversible; no un-void function is provided

---

**SRS-RE08** — Multi-Grain Reception Restriction
*Priority*: Must Have | *Source*: ADR-019 (codGrano single-grain constraint)

The system **shall** enforce that each romaneo references exactly one grain type (CUIG).
A truck carrying two grain types shall require two separate romaneos.

*Acceptance criteria*:
- The UI presents only one grain-type field per romaneo
- The WSLPG integration enforces single-grain per settlement (see ADR-019)
- Any attempt to amend a romaneo's grain type after initial save is rejected

---

**SRS-RE09** — Offline Reception Queue
*Priority*: Must Have | *Source*: PRD-F-007

The system **shall** allow a balancero to register arrivals and capture weights when the
internet connection is unavailable. Offline-created romaneos **shall** be queued locally and
synchronised to the server when connectivity resumes.

*Acceptance criteria*:
- Offline mode activates automatically within 30 seconds of connectivity loss
- The queue displays count of pending romaneos with "pending sync" status
- CTG/CPE validation during offline mode is skipped; a warning is displayed that validation
  will occur upon sync and may cause rejection

---

**SRS-RE10** — Campaign Year Assignment
*Priority*: Must Have | *Source*: PRD-F-008

The system **shall** require that every romaneo is assigned to a campaign year. The active
campaign year **shall** be configurable per tenant. The system **shall** reject reception
of grain outside the configured active campaign window (configurable start/end date).

*Acceptance criteria*:
- The active campaign year is displayed prominently on the reception screen
- Attempt to create a romaneo dated before campaign start or after campaign end is blocked
  with a descriptive error
- Administrators can have two campaign years active simultaneously during harvest overlap

---

**SRS-RE11** — Balancero Handover Log
*Priority*: Should Have | *Source*: PRD-F-009

The system **shall** maintain a shift-handover log recording: opening balancero ID and
timestamp, closing balancero ID and timestamp, count of romaneos issued, and total gross
weight processed during the shift.

*Acceptance criteria*:
- Shift report is printable as a PDF
- The log is read-only; entries cannot be edited after shift close

---

**SRS-RE12** — Duplicate Truck Guard
*Priority*: Should Have | *Source*: PRD-F-010

The system **shall** warn the operator when a truck plate is presented that already has an
open (unconfirmed) romaneo within the last 4 hours for the same tenant.

*Acceptance criteria*:
- Warning is non-blocking: the operator can acknowledge and proceed
- The warning displays the existing romaneo number and its current status

---

### 4.2 Quality Analysis Module (CA)

**Purpose**: Capture grain-quality measurements from lab or inline instruments, compute
merma deductions, and assign a commercialisation grade.

---

**SRS-CA01** — Quality Parameter Entry
*Priority*: Must Have | *Source*: PRD-F-011

The system **shall** allow quality personnel to enter the following parameters per romaneo
(mandatory fields depend on grain type):

| Parameter | Unit | Grains Applied |
|-----------|------|---------------|
| Humidity (humedad) | % | All |
| Foreign matter (material extraño) | % | All |
| Broken grain (grano partido) | % | Soy, Sunflower, Corn |
| Damaged grain (grano dañado) | % | All |
| Protein content (proteína) | % | Wheat, Barley |
| Falling number (número de caída) | seconds | Wheat |
| Oil content (contenido graso) | % | Sunflower |
| Volatile acidity (acidez volátil) | % | Sunflower |
| Weight per hectolitre (peso hectolítrico) | kg/hL | Wheat, Corn, Barley |

*Acceptance criteria*:
- Entry form dynamically shows only applicable parameters for the selected grain type
- Values outside the valid physiological range (configurable per grain type) produce a
  warning requiring supervisor confirmation before save

---

**SRS-CA02** — Merma Calculation Engine
*Priority*: Must Have | *Source*: PRD-F-012

The system **shall** compute merma (weight deduction) for each quality parameter using the
official ARCA tolerance tables. The merma calculation **shall** produce:
- Parameter-level deduction percentage
- Total merma percentage (sum of individual deductions)
- Adjusted net weight (peso neto ajustado = net weight × (1 − total merma %))

*Acceptance criteria*:
- Merma tables are configurable per grain type and updated independently of application code
- Tolerance table version is stored with each romaneo for audit traceability
- Adjusted net weight is used as the basis for all downstream financial calculations

---

**SRS-CA03** — Grade Assignment
*Priority*: Must Have | *Source*: PRD-F-013

The system **shall** automatically assign a commercialisation grade (calidad/grado) based
on quality parameters and the applicable SAGPyA/Bolsa grain standard. Grade assignment
**shall** be reviewable and overridable by a qualified recibidor with a mandatory reason code.

*Acceptance criteria*:
- Grade override is logged with operator CUIT, original grade, new grade, and reason code
- Grade override count is reported in daily quality summary

---

**SRS-CA04** — Lab Results Import
*Priority*: Should Have | *Source*: PRD-F-014

The system **shall** support import of quality parameters from compatible laboratory
instruments via CSV file upload. The CSV format **shall** be documented in the online help.

*Acceptance criteria*:
- Upload validates grain type and romaneo number before import
- Partial import (some rows valid, some invalid) is rejected; all-or-nothing atomicity

---

**SRS-CA05** — Quality Dispute Workflow
*Priority*: Should Have | *Source*: PRD-F-015

The system **shall** allow a producer or their representative to flag a quality result for
review within 24 hours of romaneo confirmation. A dispute **shall**:
- Freeze the romaneo in a DISPUTADO state
- Notify the recibidor via in-app notification
- Allow a re-analysis result to be entered and accepted or rejected
- Automatically resolve after 48 hours with the original result if no re-analysis is entered

*Acceptance criteria*:
- Dispute creates an immutable audit trail of all state transitions
- The producer's in-app notification is visible on next login even if the app was offline

---

**SRS-CA06** — Quality History per Cell
*Priority*: Should Have | *Source*: PRD-F-016

The system **shall** maintain a quality history record per storage cell per campaign,
tracking the weighted-average quality parameters of all grain deposited in that cell.

*Acceptance criteria*:
- Cell quality history is viewable in the storage module
- Quality history updates are transactional with stock movements

---

**SRS-CA07** — Humidity Correction Table
*Priority*: Must Have | *Source*: PRD-F-017

The system **shall** apply the official humidity correction table to compute the weight
equivalent to the reference humidity (base humidity) for the grain type. This corrected
weight is reported separately from the merma-adjusted weight and is used for WSLPG
settlement purposes.

*Acceptance criteria*:
- Humidity correction tables are versioned and audit-logged when updated
- Corrected weight and its reference humidity percentage are printed on the Romaneo

---

**SRS-CA08** — Quality Report Export
*Priority*: Must Have | *Source*: PRD-F-018

The system **shall** allow export of quality reports in PDF and XLSX format, covering:
- Daily reception summary (grain type, total net weight, average parameters)
- Cell quality snapshot (weighted-average parameters per cell per campaign)
- Producer quality history (all romaneos for a producer in a campaign with quality data)

*Acceptance criteria*:
- Export completes in ≤ 10 seconds for date ranges up to 12 months
- XLSX export conforms to the column schema defined in `REST API Design.md §exports`

---

### 4.3 Storage & Inventory Module (AL)

**Purpose**: Maintain an immutable ledger of grain movements between cells, and provide
accurate stock reporting per tenant.

---

**SRS-AL01** — Cell Master Data
*Priority*: Must Have | *Source*: PRD-F-019

The system **shall** allow tenant administrators to define the physical cell catalogue:
cell identifier (alphanumeric), nominal capacity (tonnes), current grain type restriction
(if any), and physical location description.

*Acceptance criteria*:
- Cell identifiers are unique within a tenant
- A cell cannot be deleted if it has non-zero stock in any active campaign

---

**SRS-AL02** — Stock Movement Ledger
*Priority*: Must Have | *Source*: PRD-F-020

The system **shall** record all grain movements as immutable ledger entries. Each entry
**shall** contain: timestamp, movement type (entrada / salida / ajuste), cell identifier,
grain type, campaign year, adjusted net weight, source romaneo or dispatch number, and
operator CUIT.

*Acceptance criteria*:
- Ledger entries are append-only: no UPDATE or DELETE operations on movement records
- Running stock balance per cell per grain type per campaign is computed from the ledger
- A negative stock balance triggers a blocking error before the movement is committed

---

**SRS-AL03** — Automatic Cell Assignment
*Priority*: Should Have | *Source*: PRD-F-021

The system **shall** suggest a target cell for incoming grain based on:
- Grain type compatibility (cell currently holds same type or is empty)
- Available capacity (remaining capacity ≥ incoming adjusted net weight)
- Operator-defined cell preference order (configurable per tenant)

*Acceptance criteria*:
- Suggestion is displayed before the operator confirms; operator may override
- Override reason is logged

---

**SRS-AL04** — Dispatch (Egreso) Processing
*Priority*: Must Have | *Source*: PRD-F-022

The system **shall** allow recording a grain dispatch (egreso) from a cell, capturing:
dispatch number, destination, truck plate, gross/tare/net weights, departure timestamp,
CPE or CTG reference (if applicable), and operator CUIT.

*Acceptance criteria*:
- Dispatch reduces stock balance immediately upon confirmation
- A CPE is required for inter-provincial dispatches (configurable threshold)

---

**SRS-AL05** — Stock Report
*Priority*: Must Have | *Source*: PRD-F-023

The system **shall** produce a stock report viewable and exportable in PDF/XLSX, showing:
current stock per cell, current stock per grain type, current stock per campaign, and total
warehouse capacity utilisation percentage.

*Acceptance criteria*:
- Report reflects real-time stock (all confirmed movements included)
- Report can be filtered by grain type, campaign year, and cell group

---

**SRS-AL06** — Physical Inventory Reconciliation
*Priority*: Should Have | *Source*: PRD-F-024

The system **shall** support a periodic physical inventory count. The operator enters
measured weights per cell; the system computes variance against ledger balance and generates
a reconciliation report showing surplus or deficit per cell.

*Acceptance criteria*:
- Reconciliation report is exportable as PDF
- Applying the reconciliation creates adjustment ledger entries (movement type: ajuste)
  with the operator CUIT and a mandatory notes field

---

**SRS-AL07** — Campaign Year Close
*Priority*: Must Have | *Source*: PRD-F-025

The system **shall** provide a campaign-year-close workflow that:
- Validates that all open romaneos are in a final state (CONFIRMADO or ANULADO)
- Validates that all CPEs are in state Confirmada_Definitiva or Anulada
- Transfers any remaining stock balance to "carried forward" in the next campaign
- Archives the closed campaign (read-only, no further movements)

*Acceptance criteria*:
- Campaign close requires a supervisor-level user
- The close operation is atomic; partial closes are not permitted

---

**SRS-AL08** — ARCA WSLPG Settlement Trigger
*Priority*: Must Have | *Source*: PRD-F-026; ADR-019; ADR-027

The system **shall** initiate a WSLPG settlement (`liquidacionAutorizar`) for a romaneo when:
(a) The romaneo is fully confirmed, (b) quality data is entered, and (c) the producing party
has SISA Estado 1 or Estado 2 (SRS-IF03 blocking gate). Settlement **shall** be blocked for
producers with SISA Estado 3 or non-registered status until the operator explicitly overrides
with a supervisor confirmation.

*Acceptance criteria*:
- WSLPG call returns a COE within 30 seconds or surfaces the error code with description
- COE is stored against the romaneo and printed on the settlement document
- Settlement documents are immutable after COE assignment (no amendment without ARCA reversal)

---

#### Grain Deposit Certificate Requirements (via WSLPG)

> Grain deposit certificates are managed via WSLPG sub-methods (`cgAutorizarReq`,
> `cgConsultarXCoe`, etc.), not to be confused with WSCDC (Web Service Constatación de
> Comprobantes), which handles invoice verification.

**GDC-REQ-01** — Certificate Issuance on Reception Confirmation
*Priority*: Must Have | *Source*: PRD-F-026; ADR-019; WSLPG `cgAutorizarReq`

The system **shall** invoke WSLPG `cgAutorizarReq` upon romaneo reception confirmation to
issue a grain deposit certificate, concurrent with WSCPE `confirmarDescargaCPE`.

*Acceptance criteria*:
- The `cgAutorizarReq` call is initiated in the same transaction boundary as the WSCPE
  `confirmarDescargaCPE` call (SRS-RE06)
- On success, the certificate COE is stored before the romaneo transitions to CONFIRMADO
- On failure, the romaneo still transitions to CONFIRMADO; the certificate is retried
  asynchronously (see GDC-REQ-03)

---

**GDC-REQ-02** — Certificate COE Persistence
*Priority*: Must Have | *Source*: PRD-F-026; ADR-019

The system **shall** persist the grain deposit certificate COE returned by WSLPG in
`CertificadoDepositoCereal.arca_nro_certificado`.

*Acceptance criteria*:
- The COE is stored as a non-nullable field once successfully obtained
- The COE is printed on the romaneo receipt and is queryable via the reception search API
- A romaneo with a pending (not yet obtained) certificate COE is visually distinguished in
  the UI from one with a confirmed certificate

---

**GDC-REQ-03** — Certificate Error Non-Blocking Policy
*Priority*: Must Have | *Source*: PRD-F-026; ADR-027

WSLPG grain certificate errors **shall not** block romaneo reception record creation; failed
certificates transition to `Pendiente` state for retry.

*Acceptance criteria*:
- If `cgAutorizarReq` fails or times out, the `CertificadoDepositoCereal` record is created
  with `estado = Pendiente` and the WSLPG error code is stored for operator review
- A background retry mechanism attempts re-issuance up to 3 times with exponential backoff
  (30s, 120s, 600s)
- After 3 failed retries, the certificate status transitions to `Error` and an alert is
  surfaced to the supervisor dashboard

---

#### WS Padrón Requirements

**PADRON-REQ-01** — Producer Tax Registration Query
*Priority*: Must Have | *Source*: PRD-F-030; ARCA WS Padrón A4

The system **shall** query WS Padrón A4 `getPersona(CUIT)` at romaneo time to determine
producer tax registration status.

*Acceptance criteria*:
- The WS Padrón query is executed during romaneo creation (SRS-RE01), before the first
  weighing event
- The response includes the producer's IVA condition (Responsable Inscripto, Monotributista,
  Exento, No Inscripto) and their Ganancias registration status
- If the WS Padrón service is unreachable, the system falls back to the last cached
  registration status; if no cached status exists, the romaneo proceeds with a warning flag

---

**PADRON-REQ-02** — Tax Status Drives Retention Percentages
*Priority*: Must Have | *Source*: PRD-F-030; ADR-027

Producer tax registration status (IVA / Monotributo / Non-registered) **shall** be used to
determine applicable IVA and Ganancias retention percentages in WSLPG liquidación.

*Acceptance criteria*:
- The retention percentages applied at settlement (SRS-CC04) are derived from the
  combination of SISA estado and WS Padrón tax condition
- Monotributista and IVA-exempt producers are excluded from IVA and Ganancias retention
  regimes (see SISA retention tier table in SRS-CC04)
- The applied tax condition is recorded in the settlement record for audit traceability

---

**PADRON-REQ-03** — Padrón Response Caching
*Priority*: Must Have | *Source*: PRD-F-030

WS Padrón responses **shall** be cached for 24 hours per CUIT to minimize ARCA API calls.

*Acceptance criteria*:
- Cache key is `padron:{cuit}` with a 24-hour TTL in Redis
- A manual "refresh padrón" action is available to operators to force a fresh query before
  the cache expires
- Cache invalidation occurs automatically when a SISA estado change is detected during
  settlement (SRS-CC04)

---

### 4.4 Producer Accounts Module (CC)

**Purpose**: Maintain a current account (cuenta corriente) per producer per grain type per
campaign, recording all debits (mermas, commissions) and credits (grain receipts, sales).

---

**SRS-CC01** — Account Structure
*Priority*: Must Have | *Source*: PRD-F-027

The system **shall** maintain one current account per combination of:
(producer CUIT × grain type × campaign year × tenant).

*Acceptance criteria*:
- Accounts are created automatically when the first romaneo for a producer/grain/campaign
  is confirmed
- Account balance is computed from ledger entries; no stored-balance field exists
  (balance is always derived to prevent inconsistency)

---

**SRS-CC02** — Debit and Credit Entries
*Priority*: Must Have | *Source*: PRD-F-028

The system **shall** record the following entry types:

| Entry Type | Direction | Source Event |
|-----------|-----------|-------------|
| Recepción de grano | Credit (kg) | Romaneo confirmation |
| Merma de calidad | Debit (kg) | Quality analysis finalisation |
| Comisión de acopio | Debit (ARS) | Settlement approval |
| Gastos de secado | Debit (ARS) | Manual entry by gestor |
| Venta / liquidación | Debit (kg + ARS) | WSLPG settlement confirmation |
| Ajuste | Debit or Credit | Manual entry, supervisor only |

*Acceptance criteria*:
- All entries are immutable after save; corrections require a counter-entry plus reason
- All monetary amounts are stored in Argentine Pesos (ARS) with two decimal precision

---

**SRS-CC03** — Account Statement
*Priority*: Must Have | *Source*: PRD-F-029

The system **shall** generate a current-account statement for a producer, filterable by
grain type and campaign year. The statement **shall** show: opening balance, each entry in
chronological order, and closing balance (in kg and ARS separately).

*Acceptance criteria*:
- Statement is exportable as PDF
- Statement can be emailed to the producer's registered email address directly from the UI

---

**SRS-CC04** — SISA Retention Calculation
*Priority*: Must Have | *Source*: PRD-F-030; ADR-027

The system **shall** calculate withholding tax (retención) at the time of settlement based
on the producer's current SISA estado. The retention tiers below match ARCA Guide §6.4
(SC-007):

| SISA Estado | Riesgo | IVA Retention (RG 2300) | Ganancias Retention (RG 4325) |
|-------------|--------|-------------------------|-------------------------------|
| **Estado 1** | RIESGO BAJO | **5%** of taxable IVA base | **0%** |
| **Estado 2** | RIESGO MEDIO | **8%** of taxable IVA base | **2%** |
| **Estado 3** | RIESGO ALTO | **10.5%** of taxable IVA base | **15%** |
| Non-registered / Suspended | — | **16%** of taxable IVA base | **30%** |
| Monotributista / IVA-exempt | — | 0% (regime not applicable) | 0% (excluded) |

*Acceptance criteria*:
- SISA estado is fetched from ARCA at settlement time (cached max 1 hour)
- WS Padrón tax condition (PADRON-REQ-01) is cross-referenced to identify Monotributista
  and IVA-exempt producers, who are excluded from both retention regimes
- Retention amounts are printed on the settlement document and recorded in the producer account
- Estado 3 and non-registered/suspended producers trigger a blocking warning (ADR-027)
  requiring supervisor override

---

**SRS-CC05** — WSLPG Electronic Settlement
*Priority*: Must Have | *Source*: PRD-F-031; ADR-019

The system **shall** submit a WSLPG settlement for each sale event. The `liquidacionAutorizar`
request **shall** include all mandatory fields as defined in the ARCA WSLPG WSDL:
nroOrdenDeEntrega, cuitVendedor, cuitCompradorPrimario, codGrano (single grain), campañia,
pesoNeto, humidity, protein (where applicable), precio, and moneda.

*Acceptance criteria*:
- Response COE is stored and printed within 5 seconds of WSLPG confirmation
- WSLPG error codes 500–599 (business rule violations) are presented to the operator with
  the ARCA-provided error message; codes 400–499 trigger an automatic retry up to 3 times

---

**SRS-CC06** — Electronic Invoice Generation
*Priority*: Must Have | *Source*: PRD-F-032; ADR-026

The system **shall** generate a Type-A electronic invoice (Factura A) via WSFEv1 for each
WSLPG settlement involving an IVA-registered buyer. For offline periods, the system **shall**
use CAEA billing mode (pre-assigned code, quincena obtained before offline period starts).

*Acceptance criteria*:
- CAE is returned by WSFEv1 within 10 seconds; printed on invoice with QR code (see ADR-025)
- CAEA invoices are queued and reported to ARCA within the allowed reporting window
- Invoices are stored as immutable records; no delete or edit after CAE/CAEA assignment

---

**SRS-CC07** — Commission Calculation
*Priority*: Should Have | *Source*: PRD-F-033

The system **shall** calculate acopio commission (comisión) as a configurable percentage of
the settlement value. Commission rates **shall** be configurable per grain type and per
producer (with producer-level rates overriding type-level defaults).

*Acceptance criteria*:
- Commission is calculated and displayed for operator review before settlement confirmation
- Commission entries in the producer account reference the settlement number

---

## 5. Phase 2 Functional Requirements (Stubs)

These requirements are deferred to Phase 2. They are listed here to ensure architectural
decisions in Phase 1 do not preclude their future implementation.

### 5.1 Liquidation Module (LQ)

**SRS-LQ01** *(Deferred — Phase 2)*: The system shall support multi-buyer grain liquidation,
distributing a single cell's stock across multiple buyers in a single operation.

**SRS-LQ02** *(Deferred — Phase 2)*: The system shall support forward-price contracts linked
to MATBA-ROFEX market prices.

**SRS-LQ03** *(Deferred — Phase 2)*: The system shall generate a Liquidación Secundaria
document compliant with ARCA requirements for triangulated sales.

### 5.2 Invoicing Enhancements (FA)

**SRS-FA01** *(Deferred — Phase 2)*: The system shall generate Nota de Crédito/Débito
(credit/debit notes) for invoice adjustments via WSFEv1.

**SRS-FA02** *(Deferred — Phase 2)*: The system shall support invoice generation for
export (Factura E) with Aduana integration.

**SRS-FA03** *(Deferred — Phase 2)*: The system shall support CAEA batch reconciliation
reporting to ARCA after each offline quincena.

### 5.3 Agronomy Services (AG)

**SRS-AG01** *(Deferred — Phase 2)*: The system shall capture field-level agronomic data
(lote, hectáreas sembradas, rindes históricos) linked to producer CUIT.

**SRS-AG02** *(Deferred — Phase 2)*: The system shall integrate with SENASA's RENSPA
registry for traceability of grain origin.

### 5.4 Cash Management (CJ)

**SRS-CJ01** *(Deferred — Phase 2)*: The system shall maintain a cash/bank ledger for
acopiador operational expenses and receipts.

**SRS-CJ02** *(Deferred — Phase 2)*: The system shall generate a daily cash-position report
for treasury management.

---

## 6. Interface Requirements

### 6.1 ARCA SOAP Service Interfaces

**SRS-IF01** — WSAA Authentication Interface
The system **shall** authenticate with ARCA services using WSAA via the `LoginCMS` SOAP
operation. The TRA (Ticket de Requerimiento de Acceso) **shall** be signed with the tenant's
private key and include the target service name. Token+Sign (TA) responses **shall** be cached
in Redis with an 11-hour TTL (WSAA issues 12-hour tokens; 1-hour safety margin). A
distributed lock **shall** prevent concurrent token refresh for the same tenant+service pair.

| Attribute | Value |
|-----------|-------|
| Production endpoint | `https://wsaa.afip.gov.ar/ws/services/LoginCms` |
| Homologation endpoint | `https://wsaahomo.afip.gov.ar/ws/services/LoginCms` |
| Token lifetime | 12 hours (ARCA-issued) |
| Cache TTL | 11 hours (Redis) |
| TRA expiry window | ±12 hours from creation |

---

**SRS-IF02** — WSLPG Grain Settlement and Certificate Interface
The system **shall** integrate with WSLPG to issue CTGs, submit settlements, and manage
grain deposit certificates (via WSLPG sub-methods).

| Operation | Method | Purpose |
|-----------|--------|---------|
| CTG validation | `consultarCTGActivo` | Confirm CTG state and grain match |
| Settlement | `liquidacionAutorizar` | Submit settlement, receive COE |
| COE consultation | `consultarLiquidacion` | Retrieve settlement status |
| Grain certificate issuance | `cgAutorizarReq` | Issue grain deposit certificate (GDC-REQ-01) |
| Grain certificate query | `cgConsultarXCoe` | Query grain certificate status by COE |

| Attribute | Value |
|-----------|-------|
| Production endpoint | `https://fwshomo.afip.gov.ar/wslpg/wslpg` (see ADR-019 note on URL scheme) |
| WSDL | `https://fwshomo.afip.gov.ar/wslpg/wslpg?WSDL` |
| Single-grain constraint | One codGrano per settlement (ADR-019) |

---

**SRS-IF03** — SISA Registry Interface
The system **shall** query the ARCA SISA service before each settlement to determine the
producer's retention tier. SISA responses **shall** be cached for 1 hour per producer CUIT.
Producers with Estado 3 or non-registered status **shall** trigger a blocking gate per
ADR-027.

---

**SRS-IF03b** — WS Padron A4 Tax Registration Interface
The system **shall** query WS Padron A4 via `getPersona(CUIT)` to determine producer tax
registration status (IVA condition, Ganancias registration). Responses **shall** be cached
for 24 hours per CUIT in Redis (PADRON-REQ-03). The tax condition drives retention regime
applicability: Monotributista and IVA-exempt producers are excluded from IVA and Ganancias
retention (see SRS-CC04).

| Attribute | Value |
|-----------|-------|
| Production endpoint | `https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA4` |
| Homologation endpoint | `https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA4` |
| WSAA service name | `ws_sr_padron_a4` |
| Cache TTL | 24 hours (Redis) |
| Key method | `getPersona(CUIT)` |

---

**SRS-IF04** — WSCPE Electronic Transport Certificate Interface
The system **shall** integrate with WSCPE for the full CPE lifecycle.

| State | Triggering Method | System Module |
|-------|------------------|--------------|
| Activa | (issued by sender) | — |
| Arribo | `informarArribo` | Reception (RE) |
| Descargada | `confirmarDescargaCPE` | Reception (RE) |
| Confirmada_Definitiva | `confirmarDefinitivamenteCPE` | Quality Analysis (CA) |
| Anulada | `anularCPE` | Reception (RE) / Quality (CA) |

> **Note**: This interface uses `confirmarDescargaCPE` (authoritative WSDL method name).
> Earlier GraviTea HLD documents used an incorrect variant of this name; all references
> have been corrected. See ARCA Grain Integration Guide §5 for the full method catalog.

---

**SRS-IF05** — WSFEv1 Electronic Invoicing Interface
The system **shall** integrate with WSFEv1 for online CAE issuance and with WSFECTP for
CAEA pre-assignment in offline periods. See SRS-CC06 and ADR-026 for details.

---

### 6.2 Hardware Interfaces

**SRS-HW01** — RS-232 Weighbridge
The system **shall** communicate with RS-232 weighbridges at 9600 bps, 8 data bits, no
parity, 1 stop bit (8N1). Maximum cable length is 15 metres. The system **shall** use the
weighbridge driver abstraction layer (HLD §4.3) to decouple hardware-specific protocols.

**SRS-HW02** — Modbus RTU Scale
The system **shall** support Modbus RTU scales (e.g., Sipel Orion) using function codes:
- 03h (Read Holding Registers): reads gross (register 0), tare (register 2), net (register 4)
- 06h (Write Single Register): sets tare
- 10h (Write Multiple Registers): batch configuration

**SRS-HW03** — ASCII Stream Scale
The system **shall** support ASCII stream scales (e.g., GaMa A12) that transmit continuous
weight data delimited by STX/ETX or CR/LF.

**SRS-HW04** — KYASERV TCP/IP Bridge
The system **shall** support the KYASERV protocol for scales connected via TCP/IP bridge,
enabling network-connected weighbridges without serial cable runs.

**SRS-HW05** — Hardware Failure Graceful Degradation
When a weighbridge connection fails, the system **shall** automatically switch to manual
weight entry mode after a 10-second timeout, displaying a visible hardware-fault indicator
to the operator.

---

### 6.3 REST API (Internal)

**SRS-IF10** — The system **shall** expose a versioned REST API (prefix `/api/v1/`) for all
frontend interactions. The API design is specified in `REST API Design.md`.

**SRS-IF11** — All API endpoints **shall** require a valid JWT Bearer token in the
Authorization header. Token format and claims are specified in HLD §3.2 and ADR-020.

**SRS-IF12** — The API **shall** return structured error responses conforming to RFC 7807
(Problem Details for HTTP APIs) with a `tenant_id` field omitted from error bodies to
prevent information leakage.

---

## 7. Performance Requirements

**SRS-PF01** — Romaneo Save Latency
The system **shall** save a completed romaneo (including merma calculation and stock update)
within 3 seconds under normal load (up to 50 concurrent users per tenant).

**SRS-PF02** — ARCA Service Timeout Budget
External ARCA service calls **shall** be subject to a 30-second timeout. On timeout, the
operation **shall** be retried once; if the retry also times out, the error is surfaced to
the operator with guidance to retry manually.

**SRS-PF03** — Report Generation
PDF and XLSX reports covering up to 12 months of data **shall** complete in ≤ 10 seconds.

**SRS-PF04** — Offline Sync Resume
After connectivity is restored, the offline queue **shall** begin synchronisation within
30 seconds and complete a queue of up to 200 pending romaneos within 5 minutes.

**SRS-PF05** — Concurrent Tenant Isolation
The system **shall** support 100 tenants operating concurrently with no cross-tenant
performance degradation. Row-Level Security **shall** enforce isolation at the database tier
without application-layer filtering.

---

## 8. Security Requirements

**SRS-SE01** — Multi-Tenant Isolation
All database queries **shall** be executed within an active PostgreSQL RLS context. The
application **shall** never issue a query that bypasses RLS by setting `row_security = off`.
Cross-tenant data access **shall** be impossible by construction (ADR-020).

**SRS-SE02** — JWT Algorithm Enforcement
The authentication service **shall** accept only RS256-signed JWTs. The `alg` header
**shall** be validated against a server-side whitelist before signature verification.
The `none` algorithm **shall** be rejected (see gravitea-auth skill).

**SRS-SE03** — ARCA Certificate Protection
Each tenant's ARCA private key **shall** be encrypted at rest using AES-256-GCM with a
key-encryption key stored in the secrets management service (not in the database). Private
keys **shall** never be logged or included in error messages.

**SRS-SE04** — Audit Logging
The system **shall** maintain an immutable audit log of all state-changing operations
(romaneo create/void, quality entry, stock movement, settlement, invoice). Audit entries
**shall** include: timestamp, operator CUIT, tenant ID, operation type, affected record ID,
and before/after values for the mutated fields.

**SRS-SE05** — Input Validation
All user inputs arriving at the API boundary **shall** be validated for type, length, and
domain constraints before processing. SQL injection, XSS, and command injection defences
**shall** be applied at the framework level (Django ORM, DRF serialisers).

**SRS-SE06** — ARCA Secret Rotation
The system **shall** support zero-downtime rotation of ARCA certificates without requiring
application restart. New certificates **shall** take effect within one cache-refresh cycle
(≤ 12 hours for the WSAA token TTL).

---

## 9. Data Requirements

**SRS-DA01** — Retention
Operational data (romaneos, movements, invoices, audit logs) **shall** be retained for a
minimum of 10 years to satisfy Argentine fiscal records legislation (Res. Gral. ARCA 1415).

**SRS-DA02** — Backup
The database **shall** be backed up daily with point-in-time recovery (PITR) capability.
Backup retention **shall** be 35 days rolling. Backup integrity **shall** be verified weekly
via automated restore test.

**SRS-DA03** — Data Sovereignty
All tenant data **shall** be stored in servers physically located in the Argentine Republic
or in jurisdictions approved by the tenant in writing, in compliance with Argentine Personal
Data Protection Law 25.326.

**SRS-DA04** — PII Encryption
Producer name, DNI, and contact information **shall** be encrypted at rest using
AES-256-GCM (blind index for searchability). The encryption schema is specified in the
gravitea-encryption skill.

---

## 10. Constraints and Assumptions

### 10.1 Regulatory Constraints

- The system is subject to Argentine tax authority regulations administered by ARCA
  (formerly AFIP). ARCA may update WSDL schemas, tolerance tables, and SISA logic without
  prior notice; the system architecture **shall** support updates without code changes where
  possible (configurable tables).
- WSLPG enforces a single-grain-type constraint per settlement (ADR-019). The system design
  **shall not** attempt multi-grain settlements.
- CAEA codes must be obtained before the offline quincena begins; if not obtained in time,
  the system **shall** fall back to online-CAE-only mode for that period (ADR-026).

### 10.2 Technical Constraints

- The backend language and framework are Python 3.14 / Django 5.2 / DRF (Phase 1 and 2).
  Rust extension modules via PyO3 are approved for performance-critical paths (Phase 2+).
- The database is PostgreSQL 18.1. No other database engine is supported.
- The ARCA integration **shall** use SOAP over HTTPS. REST alternatives do not exist for
  WSAA, WSLPG, and WSCPE at this time.

### 10.3 Assumptions

1. Each tenant has a valid ARCA digital certificate (`.p12` or `.pem` format) at onboarding.
2. Producers have a registered CUIT in the Argentine fiscal registry.
3. Internet connectivity is available for at least 4 hours per day to support sync and ARCA calls.
4. Weighbridge hardware is located on the same local network as the browser client.

---

## 11. Traceability Matrix

This matrix traces each Phase 1 SRS requirement to its PRD source, implementation spec,
API endpoint, and test marker.

| SRS ID | PRD Source | Impl Spec | API Endpoint | Pytest Marker |
|--------|-----------|-----------|-------------|---------------|
| SRS-RE01 | PRD-F-001 | spec-009 | `POST /api/v1/romaneos/` | `@pytest.mark.reception` |
| SRS-RE02 | PRD-F-002 | spec-009 | `POST /api/v1/romaneos/{id}/gross-weight` | `@pytest.mark.reception` |
| SRS-RE03 | PRD-F-002 | spec-009 | `POST /api/v1/romaneos/{id}/tare-weight` | `@pytest.mark.reception` |
| SRS-RE04 | PRD-F-003 | spec-009 | `GET /api/v1/romaneos/{id}/pdf` | `@pytest.mark.reception` |
| SRS-RE05 | PRD-F-004 | spec-009 | `GET /api/v1/ctg/{ctg}/validate` | `@pytest.mark.arca` |
| SRS-RE06 | PRD-F-005 | spec-009 | `POST /api/v1/cpe/{cpe}/arribo` | `@pytest.mark.arca` |
| SRS-RE07 | PRD-F-006 | spec-009 | `POST /api/v1/romaneos/{id}/void` | `@pytest.mark.reception` |
| SRS-RE08 | ADR-019 | spec-009 | — (enforced at model layer) | `@pytest.mark.unit` |
| SRS-RE09 | PRD-F-007 | spec-012 | `POST /api/v1/sync/push` | `@pytest.mark.sync` |
| SRS-RE10 | PRD-F-008 | spec-009 | — (enforced at service layer) | `@pytest.mark.unit` |
| SRS-RE11 | PRD-F-009 | spec-009 | `GET /api/v1/shifts/{id}/report` | `@pytest.mark.reception` |
| SRS-RE12 | PRD-F-010 | spec-009 | — (enforced at service layer) | `@pytest.mark.unit` |
| SRS-CA01 | PRD-F-011 | spec-010 | `POST /api/v1/romaneos/{id}/quality` | `@pytest.mark.quality` |
| SRS-CA02 | PRD-F-012 | spec-010 | — (computed in service layer) | `@pytest.mark.unit` |
| SRS-CA03 | PRD-F-013 | spec-010 | `PATCH /api/v1/romaneos/{id}/quality/grade` | `@pytest.mark.quality` |
| SRS-CA04 | PRD-F-014 | spec-010 | `POST /api/v1/romaneos/{id}/quality/import` | `@pytest.mark.quality` |
| SRS-CA05 | PRD-F-015 | spec-010 | `POST /api/v1/romaneos/{id}/quality/dispute` | `@pytest.mark.quality` |
| SRS-CA06 | PRD-F-016 | spec-010 | `GET /api/v1/cells/{id}/quality-history` | `@pytest.mark.storage` |
| SRS-CA07 | PRD-F-017 | spec-010 | — (computed in service layer) | `@pytest.mark.unit` |
| SRS-CA08 | PRD-F-018 | spec-010 | `GET /api/v1/reports/quality` | `@pytest.mark.quality` |
| SRS-AL01 | PRD-F-019 | spec-011 | `POST /api/v1/cells/` | `@pytest.mark.storage` |
| SRS-AL02 | PRD-F-020 | spec-011 | `POST /api/v1/movements/` | `@pytest.mark.storage` |
| SRS-AL03 | PRD-F-021 | spec-011 | `GET /api/v1/cells/suggest` | `@pytest.mark.storage` |
| SRS-AL04 | PRD-F-022 | spec-011 | `POST /api/v1/dispatches/` | `@pytest.mark.storage` |
| SRS-AL05 | PRD-F-023 | spec-011 | `GET /api/v1/reports/stock` | `@pytest.mark.storage` |
| SRS-AL06 | PRD-F-024 | spec-011 | `POST /api/v1/reconciliation/` | `@pytest.mark.storage` |
| SRS-AL07 | PRD-F-025 | spec-011 | `POST /api/v1/campaigns/{id}/close` | `@pytest.mark.storage` |
| SRS-AL08 | PRD-F-026 | spec-011 | `POST /api/v1/wslpg/settle` | `@pytest.mark.arca` |
| GDC-REQ-01 | PRD-F-026 | spec-009 | — (invoked on romaneo confirmation) | `@pytest.mark.arca` |
| GDC-REQ-02 | PRD-F-026 | spec-009 | — (persisted in CertificadoDepositoCereal) | `@pytest.mark.arca` |
| GDC-REQ-03 | PRD-F-026 | spec-009 | — (async retry on failure) | `@pytest.mark.arca` |
| PADRON-REQ-01 | PRD-F-030 | spec-009 | `GET /api/v1/padron/{cuit}` | `@pytest.mark.arca` |
| PADRON-REQ-02 | PRD-F-030 | spec-009 | — (drives retention in SRS-CC04) | `@pytest.mark.arca` |
| PADRON-REQ-03 | PRD-F-030 | spec-009 | — (Redis cache, 24h TTL) | `@pytest.mark.arca` |
| SRS-CC01 | PRD-F-027 | spec-011 | — (auto-created on first romaneo) | `@pytest.mark.accounts` |
| SRS-CC02 | PRD-F-028 | spec-011 | `POST /api/v1/accounts/{id}/entries` | `@pytest.mark.accounts` |
| SRS-CC03 | PRD-F-029 | spec-011 | `GET /api/v1/accounts/{id}/statement` | `@pytest.mark.accounts` |
| SRS-CC04 | PRD-F-030 | spec-011 | — (computed at settlement) | `@pytest.mark.arca` |
| SRS-CC05 | PRD-F-031 | spec-011 | `POST /api/v1/wslpg/settle` | `@pytest.mark.arca` |
| SRS-CC06 | PRD-F-032 | spec-011 | `POST /api/v1/invoices/` | `@pytest.mark.arca` |
| SRS-CC07 | PRD-F-033 | spec-011 | — (computed at settlement) | `@pytest.mark.accounts` |

---

## 12. Appendix: Requirement Namespace Reference

Each requirement ID uses a two-letter module prefix (PP) followed by a two-digit sequential
number (NN). The prefix identifies the functional module owning the requirement.

| Prefix | Module | Phase | Description |
|--------|--------|-------|-------------|
| RE | Reception | 1 | Truck arrival, weighbridge, Romaneo, CTG/CPE |
| CA | Quality Analysis | 1 | Quality parameters, merma, grade assignment |
| AL | Storage / Inventory | 1 | Cell management, movements ledger, dispatch |
| GDC | Grain Deposit Certificates | 1 | WSLPG `cgAutorizarReq`, certificate COE, retry policy |
| PADRON | WS Padrón | 1 | Producer tax registration lookup, cache policy |
| CC | Producer Accounts | 1 | Cuenta corriente, retention, settlement, invoice |
| LQ | Liquidation | 2 | Multi-buyer liquidation, forward contracts |
| FA | Invoicing Enhancements | 2 | Notas de crédito/débito, export invoices, CAEA reconciliation |
| AG | Agronomy Services | 2 | Field data, SENASA RENSPA integration |
| CJ | Cash Management | 2 | Cash ledger, treasury reports |
| HW | Hardware Interfaces | 1/2 | RS-232, Modbus RTU, ASCII stream, KYASERV |
| IF | System Interfaces | 1 | ARCA SOAP, REST API |
| SE | Security | 1 | Tenant isolation, JWT, encryption, audit |
| PF | Performance | 1 | Latency, throughput, offline sync |
| DA | Data | 1 | Retention, backup, sovereignty, PII |

---

*GraviTea Acopio ERP — Software Requirements Specification v2.0*
*© 2026 GraviTea Team. Internal use only.*
