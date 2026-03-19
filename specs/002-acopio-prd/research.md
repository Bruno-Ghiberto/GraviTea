# Research: Acopio PRD Domain Facts

**Feature**: `002-acopio-prd`
**Date**: 2026-03-16
**Purpose**: Consolidated domain knowledge for writing PRD v1.0. Use in Phase W1-W6.
**Protocol**: All facts RAG-verified against Qdrant `acopio_research` collection.
Do NOT read full PDFs — use this file and targeted RAG queries as needed.

---

## §2 — Glossary Terms

**Canonical acopio terminology** (use these exact Spanish terms in PRD, translate on first use):

| Spanish Term | English Translation | Notes |
|-------------|-------------------|-------|
| Romaneo | Weighing ticket | Atomic transaction; links CPE + quality + weight |
| Merma | Measurable grain loss | Sequential deduction: zarandeo → secado → manipuleo → volátil |
| Acopiador | Grain collection and storage operator | Independent non-cooperative |
| Balancero / Recibidor | Scale operator / Receiving clerk | Romaneo creator |
| Laboratorista | Lab analyst | Quality grading role |
| Boleta de Romaneo | Reception document | Includes quality grade + merma breakdown |
| CEG | Certificado de Existencia de Granos | Grain deposit certificate — issued on romaneo closure |
| LPG | Liquidación Primaria de Granos | Form 1116-C settlement document |
| CPE | Carta de Porte Electrónica | Electronic waybill — mandatory per WSCPE |
| CTG | Código de Trazabilidad de Granos | 12-digit truck grain traceability code assigned by ARCA |
| SISA | Registro Sistémico Actividad Agropecuaria | ARCA compliance tier database (RG 5689/2025) |
| WSLPG | Web Service Liquidaciones Primarias de Granos | ARCA e-filing for Form 1116-C/B |
| WSCPE | Web Service Carta de Porte Electrónica | ARCA CPE lifecycle management |
| Pizarra | Market board price | Published price per ton/quintal for a grain type at a given moment |
| Fijación | Price-crystallization event | Producer requests fixing at current pizarra; triggers LPG |
| Cuenta corriente | Producer current account | Per-plant dual ledger: kg grain + ARS/USD monetary |
| Posición consolidada | Cross-plant consolidated position | Derived view: sum per-plant ledgers for same producer CUIT across tenant |
| Canje | Grain-for-input barter exchange | Grain debit + input invoice; LPG + Factura generated |
| Zarandeo | Sieving / grain cleaning | First merma deduction step |
| Secado | Drying | Second merma deduction step |
| Manipuleo | Handling | Third merma deduction step |
| Volátil | Volatile moisture | Fourth (final) merma deduction step |
| Paritaria | Inbound handling fee | Charged per ton on arrival; covers labor + energy |
| Almacenaje | Storage fee | Charged per ton-month or quintal |
| Campaña | Campaign / crop year | Split-year format: "2025/26"; logical grain segregation unit |
| Cubicaje | Volumetric grain estimation | Estimate grain quantity from silo geometry without physical measurement |

---

## §4.1 — RECEPCIÓN (Romaneo)

### Complete 11-Step Romaneo Workflow [RAG: Research 2.1]

1. Truck arrives at plant — driver presents CPE/CTG documents
2. CPE/CTG arrival registration — `confirmarArriboCPE` (WSCPE online; store-and-forward if offline)
3. Gross weight capture — truck drives onto primary scale; balance operator captures peso bruto
4. Lab sample collection — laboratorista takes grain sample from truck cargo
5. Tara capture — truck drives off (unloaded); secondary scale captures tara weight
6. Peso neto calculation — `peso neto = peso bruto − tara` (calculated by system)
7. Quality sample analysis — CALIDAD module grades sample; assigns Grado or rebaja
8. Merma calculation — sequential per CAC 10/86 (zarandeo → secado → manipuleo → volátil)
9. Peso neto conforme assignment — after all merma deductions
10. Boleta de romaneo generation + silo assignment — ALMACENAMIENTO receives grain lot
11. Producer account credit (CUENTAS CORRIENTES — CEG issued) + CPE closure (`descargadoDestinoCPE` + `confirmacionDefinitivaCPEAutomotor`)

### Romaneo State Machine [RAG: Research 2.1]

```
PENDIENTE → EN_PROCESO → PESADO → ANALIZADO → CONFORME → CERRADO
```
- PENDIENTE: CPE registered, truck not yet on scale
- EN_PROCESO: confirmarArriboCPE sent; peso bruto captured
- PESADO: tara captured; peso neto calculated
- ANALIZADO: quality grade + merma calculated
- CONFORME: boleta de romaneo generated; validated by operator
- CERRADO: CEG issued; CPE definitively closed; silo stock updated

### Romaneo Data Fields [RAG: Research 8.3]

| Field | Type | Source |
|-------|------|--------|
| CPE number | String | From ARCA WSCPE |
| CTG number | 12-digit | From ARCA WSCPE |
| Grain type | ARCA code | Driver declaration |
| Campaign year | String (e.g. "2025/26") | Romaneo config |
| Truck plate (patente) | String | Driver declaration |
| Driver name | String | Driver declaration |
| Producer CUIT | 11-digit | From CPE |
| Origin party (remitente) | String | From CPE |
| Peso bruto (kg) | DECIMAL(17,3) | Primary scale (weighbridge) |
| Tara (kg) | DECIMAL(17,3) | Secondary scale or stored/manual |
| Peso neto (kg) | DECIMAL(17,3) | Calculated: peso bruto − tara |
| Quality sample ID | String | CALIDAD module |
| Grado or rebaja % | String / Decimal | CALIDAD module output |
| Merma breakdown (4 steps) | DECIMAL(17,3) each | CALIDAD module |
| Peso neto conforme (kg) | DECIMAL(17,3) | After all merma deductions |
| Silo/celda assignment | FK | Operator selection → ALMACENAMIENTO |
| State | Enum | System |
| Romaneo date/time | DateTime | System timestamp |

---

## §4.2 — CALIDAD (Quality)

### Two Grading Systems [RAG: Research 2.1 + 2.2]

**Cereals (trigo, maíz, sorgo)**: Grado 1 / Grado 2 / Grado 3 / Fuera de Estándar
- Grado 1: bonificación (positive price adjustment)
- Grado 2: base (no adjustment)
- Grado 3: rebaja (negative price adjustment)
- Classification based on worst measured parameter

| Grado | Trigo pan | Maíz | Sorgo |
|-------|-----------|------|-------|
| Grado 1 | +1.5% bonif. | +1.0% bonif. | +1.0% bonif. |
| Grado 2 | Base | Base | Base |
| Grado 3 | −1.0% rebaja | −1.5% rebaja | −1.5% rebaja |

**Oleaginosas (soja, girasol)**: Tolerance-based progressive rebajas (NOT Grado 1/2/3)
- Each parameter has a tolerance base; exceedances trigger progressive % deductions
- Example (soja): materias extrañas > 1%: −1% per point up to 3%; −1.5% per point above 3%
- PRD must specify per-grain rebaja structure; do not unify with cereal Grado scale

### Merma Formula [RAG: Research 2.5, CAC 10/86 + Resolución JNG N° 22027/81]

**Regulatory basis**: Circular CAC 10/86 (Cámara Arbitral de Cereales de Rosario) AND
Artículo 5° de la Resolución JNG N° 22027/81 — both mandate the same sequential order.

**Formula** (multiplicative chain — each step on previous result, NOT on original weight):
```
Peso_final = Peso_bruto × (1 − %Z) × (1 − %S) × (1 − %M) × (1 − %V)
```

**Secado formula** (per Cámara Arbitral Hf table per grain type):
```
%S = (Hi − Hf) / (100 − Hf)
```
where Hi = incoming humidity, Hf = base humidity for commercialization

**Fixed values for Manipuleo (%M)**:
- Trigo: 0.10%
- Maíz, Soja: 0.25%
- Girasol: 0.20%

**Fixed values for Volátil (%V)**:
- Cereales (trigo, maíz, avena, cebada, centeno): 0.30%
- Oleaginosas (soja, girasol): 0.50%

**ERP data capture per step**: grain type, Hi, actual parameter values, tolerance table applied,
% merma per concept (zarandeo/secado/manipuleo/volátil), kg deducted per concept,
peso result after each step, final peso neto conforme.

**Dispute support**: All above data + Hf table used are stored and accessible on demand per
romaneo. Producer can request audit trail package for submission to Cámara Arbitral de
Cereales (CAC) — external escalation. No dispute lifecycle state machine in the ERP.

---

## §4.3 — ALMACENAMIENTO (Storage)

### Silo Assignment Logic [RAG: Research 2.1]

Operator assigns grain lot to silo/celda based on:
1. Grain type (no cross-contamination)
2. Quality/grade (stratification by quality is recommended best practice)
3. Humidity (high-humidity grain → wet bin / secadora first; then to storage silo)
4. Campaign year (cosecha vieja vs. cosecha nueva — logical segregation)
5. Producer (in some cases, per-producer segregation for contract obligations)
6. Available space in each silo/celda

### Composite Key for Grain Position [RAG: Research 2.6]

`(plant_id, grain_code, campaign_id)` — mirrors AFIP stock declaration structure (per RG 3593 requirement)
Physical co-mingling of same grain from different campaigns is possible in practice (limited capacity).
ERP must track logical campaign attribution even when grain is physically co-mingled.

### Campaign Year Format [RAG: Research 2.6]

- Split-year format: "2025/26" (aligns with Argentine agricultural marketing year)
- Carry-stock (stock de enlace): grain held from prior campaign tracked as "stocks iniciales"
- Campaign transition: admin defines new campaign code → system uses for all subsequent romaneos → generates carry-stock report → operator uses for AFIP manual declaration

---

## §4.4 — CUENTAS CORRIENTES (Producer Account)

### Dual Ledger Structure [RAG: Research 2.3]

Per-plant ledger (source of truth):
- **Grain sub-ledger**: kg balance per grain type × campaign × producer (append-only)
- **Monetary sub-ledger**: ARS or USD balance; linked to grain transactions

Posición consolidada: derived view aggregating per-plant ledgers for same producer CUIT
across all plants of the same tenant. Not stored — computed on demand.

### Transaction Type Catalog [RAG: Research 2.3]

| Transaction | Document | Sub-ledger Affected |
|------------|----------|-------------------|
| Grain deposit (romaneo closure) | CEG | Grain +kg |
| Grain sale (at delivery) | LPG (Form 1116-C) | Grain −kg; Monetary +ARS/USD net |
| Fijación (a fijar price crystallization) | LPG (Form 1116-C) | Grain −kg; Monetary +ARS/USD net |
| Physical withdrawal | Cert. Retiro | Grain −kg |
| Retention certificate | F.2005 / SIRE | Monetary −ARS (deducted at settlement) |
| Service charges (secada/zarandeo/almacenaje/paritaria) | Factura | Monetary −ARS |
| Canje input exchange | LPG + Factura insumos | Grain −kg; Monetary net (LPG − Factura) |

### "A Fijar" Mechanics [RAG: Research 2.3 + spec.md clarification Q2]

- Grain enters account at zero monetary value (kg credited, no pesos)
- Producer can fix the price at any time during the agreed period (days, weeks, or campaign)
- Reference price: Cámara Arbitral's pizarra for the requested grain type and date
- Fix event: producer contacts acopiador → administrador creates fijación record at current pizarra
- System generates LPG → monetary sub-ledger credited at fixed price × net kg
- A single CEG can generate **multiple partial LPGs** over time (partial fijaciones)

---

## §4.5 — LIQUIDACIONES (Settlement)

### Form Types [RAG: Research 5.1 (WSLPG)]

- **Form 1116-C** (Liquidación Primaria): acopiador pays producer for grain
- **Form 1116-B** (Liquidación Secundaria): acopiador sells grain to buyer

### SISA-Tier Retention Tables [RAG: Research 7.3 — authoritative]

**IVA Retention (RG 2300)**:

| SISA Estado | Rate | Refund |
|------------|------|--------|
| Estado 1 (Low risk — RIESGO BAJO) | 5% | Fully refunded by ARCA to producer ~45 days |
| Estado 2 (Medium risk — RIESGO MEDIO) | 8% | Partial refund |
| Estado 3 (High risk — RIESGO ALTO) | 10.5% | No automatic refund |
| Non-registered / Inhabilitado | 16% | No refund; other sanctions may apply |

*Note: Grain IVA base rate is 10.5% (reduced rate for agricultural grains).
Research 1.3 cites different values (5/7/8) — use Research 7.3 table confirmed
by spec.md user-verified clarification.*

**Ganancias Retention (RG 4325 — grain-specific, supersedes older RG 2118/2006)**:

| SISA Estado | Rate |
|------------|------|
| Estado 1 | 0% |
| Estado 2 | 2% |
| Estado 3 | 15% |
| Non-registered | 30% |

**IIBB**: Per-province rate, configurable by tenant admin. Not a federal table.

### SISA Blocking Gate [RAG: Research 7.3 + spec.md clarification Q2]

System queries producer CUIT against SISA API before each liquidación.
Result determines retention tier. Settlement BLOCKED if:
- SISA query fails (API unavailable)
- SISA status = Inhabilitado / Sin Operar
Override: operator can acknowledge with documented justification (audit-logged).
24-hour rule (RG 5689/2025): grain movements must be registered in SISA within 24 hours
— affects romaneo timestamp requirements.

---

## §5 — Operational Workflows

### "A Fijar" Fijación Flow [RAG: Research 2.3]

1. Producer contacts acopiador requesting to fix price
2. Administrador opens fijación screen — selects producer + grain type + campaign + kg quantity
3. System shows current pizarra price (Cámara Arbitral published price for that date)
4. Administrador confirms at displayed price
5. System generates LPG — Form 1116-C with grain quantity × fixed price
6. SISA query triggered → retention tier determined → retentions applied
7. Monetary sub-ledger credited: net settlement amount after retentions and service charges
8. CPE is NOT involved (fijación is post-reception accounting event)

---

## §6 — Regulatory Compliance

### CPE/CTG Full Lifecycle [RAG: Research 8.2 + 1.1]

```
Borrador (local draft) → Activa (CTG assigned) → Arribo → Descargada → Confirmada Definitiva
                                                          ↗ anularCPE
                                              → rechazoCPE
                                              ↔ informarContingencia (pauses TTL)
```

**WSCPE Method Catalog per Romaneo Step**:

| Romaneo Step | WSCPE Method | Notes |
|-------------|-------------|-------|
| Before dispatch (origin) | `autorizarCPEAutomotor` | Issued by sender; assigns CTG; validates SISA |
| EN_PROCESO (truck arrived) | `confirmarArriboCPE` | State-only change; no business data |
| CERRADO step 1 | `descargadoDestinoCPE` | Records physical unloading event |
| CERRADO step 2 | `confirmacionDefinitivaCPEAutomotor` | Sends final peso bruto + tara; ARCA computes net; closes CTG |
| Cancellation (pre-departure) | `anularCPE` | Only before truck leaves origin |
| Destination rejection | `rechazoCPE` | Quality issues or misrouting |
| Delay (mechanical, road, strike) | `informarContingencia` | Pauses 5-day TTL |

**Timing**: Automotor CPE valid for **5 days**; Ferroviaria CPE valid for 30 days.
**Offline handling**: `confirmarArriboCPE` and CERRADO closure methods queued in
store-and-forward queue. Submitted in order when connectivity restores.
Alert if CPE expires before confirmation restored (5-day window).

### WSLPG Filing [RAG: Research 5.1]

Regulatory basis: RG 3419/2012 (WSLPG), RG 3690/2014 (updates), RG 3691/2014 (Form 1116-B)
Automated actions:
- Retention calculation (SISA tier lookup)
- Form field population from romaneo + account data

User confirmation required:
- Final approval before WSLPG electronic submission

SICORE: magnetic file format for periodic retention reporting; generated after period closing.

---

## §7 — Hardware Integration

### Weighbridge Interface Facts [RAG: Research 3.1]

- **Primary standard**: RS-232 serial (dominant for Argentine grain scale indicators)
- **Alternative serial**: RS-485 in some installations (same application-level behavior)
- **No REST APIs**: No Argentine weighbridge manufacturer offers REST API as standard
- **TCP/IP bridge**: Converter modules (e.g., KYASERV RS-232→Ethernet; up to 4 scales)
  expose a network socket interface; same application behavior as direct RS-232
- **Stability detection**: Indicator emits "stable" flag; system captures weight only on stable signal
- **Dual scale**:
  - Primary scale: captures peso bruto (laden truck)
  - Secondary scale: captures tara (empty truck after unloading)
  - peso neto = peso bruto − tara (system calculates)
- **Alternative tara**: Fixed tara per truck plate (stored DB lookup) or manual entry fallback
- **Calibration**: INTA/SENASA/INPM standards; certificate required; track per-scale: last date, cert number, next due date; alert before expiry

---

## §8 — NFRs

### Online/Offline Classification

From spec.md FR-016 + constitution Principle VII:

| Operation | Classification | Reason |
|-----------|---------------|--------|
| Romaneo creation/weight capture | Offline | Core harvest operation |
| Quality grading / merma calculation | Offline | Core harvest operation |
| Silo assignment | Offline | Core harvest operation |
| Producer account credit (CEG) | Offline | Core harvest operation |
| CPE confirmarArriboCPE | Store-and-forward | ARCA required; retry when online |
| CPE descargadoDestinoCPE + confirmacionDefinitivaCPEAutomotor | Store-and-forward | ARCA required |
| Posición consolidada query (cross-plant) | Connectivity-required | Cross-tenant aggregation |
| Retention calculation | Offline | Local computation |
| SISA status query | Connectivity-required | Real-time ARCA API |
| WSLPG filing | Connectivity-required | ARCA web service |
| CAE/CAEA issuance (FACTURACIÓN) | Store-and-forward (CAEA mode) | ARCA required |
| Insumos catalog / inventory updates | Offline | Local data |
| Canje calculation + account entries | Offline | Local computation |

**Conflict resolution** (per Constitution VII):
- Romaneo (sales): `additive` — combine from all sources
- Silo stock (inventory): `last_write_wins` + audit trail
- Configuration / pizarra prices: `server_wins`
- Producer account: `additive` — each CEG/LPG is unique document

---

## §9 — Phased Delivery

### Phase Allocation [from Vision v1.0 + spec.md FR-018]

| Phase | Modules | Key Feature |
|-------|---------|------------|
| 1 | RECEPCIÓN + CALIDAD + ALMACENAMIENTO + CUENTAS CORRIENTES | Romaneo-to-Position loop |
| 2 | LIQUIDACIONES + FACTURACIÓN | Fiscal settlement loop |
| 3 | CANJE + AGRONOMÍA | Input exchange |
| 4 | AI Layer (cross-cutting) | Prediction + optimization |

**Phase 1 exit criteria**: "First real truck reception processed end-to-end on a pilot plant" —
truck arrives → romaneo completed → silo assigned → producer account credited → boleta generated.

---

## Decision Log

| Decision | Rationale | Alternatives Rejected |
|----------|-----------|----------------------|
| IVA rates: use Research 7.3 table (5/8/10.5/16%) | User-confirmed in spec.md clarification; Research 7.3 is the authoritative withholding calculation reference | Research 1.3 and 7.1 cite different table (5/7/8%) — likely different time period or base rate interpretation |
| CPE closure: two-step `descargadoDestinoCPE` + `confirmacionDefinitivaCPEAutomotor` | Confirmed by Research 8.2 WSCPE lifecycle; spec.md uses shorthand "confirmarDescargaCPE" | Single-step simplified naming per spec.md — too imprecise for engineering reference |
| Merma sequential: apply multiplicatively on previous result | CAC 10/86 + Resolución JNG N° 22027/81 both mandate this; formula is unambiguous | Independent deductions from original weight — explicitly wrong per both regulations |
| Campaign year as composite key (plant_id, grain_code, campaign_id) | Confirmed by Research 2.6; mirrors AFIP stock declaration structure (RG 3593) | Single campaign field on grain — loses plant + grain segregation needed for AFIP |
| Canje generates two parallel documents (LPG + Factura) | Research 2.3 confirms both document streams required; different tax treatments | Single combined document — not valid under ARCA and AFIP tax rules |
