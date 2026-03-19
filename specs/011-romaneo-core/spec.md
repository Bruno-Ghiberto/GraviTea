# Feature Specification: Romaneo Core

**Feature Branch**: `011-romaneo-core`
**Created**: 2026-03-19
**Status**: Draft
**Input**: Implement the romaneo (grain reception document) lifecycle -- the central transactional workflow of the acopio operation -- including quality analysis, sequential merma calculation, and a high-performance Rust computation engine.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Register a Grain Reception (Romaneo) (Priority: P1)

A plant operator creates a new romaneo when a truck arrives at the acopio. The operator records the truck's identification (chassis plate, trailer plate, driver name, driver DNI), links the reception to the corresponding Carta de Porte Electronica (CPE), and identifies the grain type, campaign, and producing party. The system assigns a sequential romaneo number automatically per branch location.

**Why this priority**: The romaneo is the foundational document of the entire acopio operation. Without it, no grain can be received, weighed, analysed, stored, or settled. Every downstream process -- storage assignment, producer account crediting, liquidation -- depends on a confirmed romaneo existing first.

**Independent Test**: Can be fully tested by creating a romaneo for a truck arrival and verifying all identification fields are captured, a unique romaneo number is generated, and the romaneo appears in the branch's reception list.

**Acceptance Scenarios**:

1. **Given** a truck arrives at the plant with a valid CPE, **When** the operator creates a new romaneo with truck, driver, grain type, campaign, and CPE number, **Then** the system creates the romaneo in PENDIENTE status with an auto-generated sequential number (format ROM-YYYY-NNNNN) and records the arrival timestamp.
2. **Given** a romaneo is created, **When** the operator views the romaneo list for the branch, **Then** the new romaneo appears sorted by arrival time (most recent first).
3. **Given** two branches of the same tenant, **When** romaneos are created at each branch, **Then** each branch maintains its own independent sequential numbering.
4. **Given** an operator at tenant A, **When** they list romaneos, **Then** they see only their tenant's romaneos and cannot access tenant B's romaneos by ID.

---

### User Story 2 - Capture Weights (Gross and Tare) (Priority: P1)

The operator captures the truck's gross weight (peso bruto) when the loaded truck is on the weighbridge, and the tare weight after the truck unloads. These two readings determine the physical net weight of grain delivered. The system records timestamps for each weighing event.

**Why this priority**: Weight capture is the physical measurement that determines how much grain was delivered. Without accurate gross and tare weights, the commercial net weight cannot be calculated, making settlement impossible.

**Independent Test**: Can be tested by recording a gross weight on an EN_PROCESO romaneo, verifying the transition to PESADO, then later recording a tare weight on a CONFORME romaneo and verifying peso_neto_bruto is correctly computed.

**Acceptance Scenarios**:

1. **Given** a romaneo in EN_PROCESO status, **When** the operator records the gross weight (e.g., 42,450.000 kg), **Then** the romaneo transitions to PESADO, the gross weight timestamp is recorded, and the peso_bruto_kg is stored with 3-decimal precision.
2. **Given** a romaneo in CONFORME status with peso_bruto = 42,450.000 kg, **When** the operator records the tare weight (e.g., 12,340.000 kg), **Then** peso_neto_bruto_kg is computed as 30,110.000 kg and the tare timestamp is recorded.
3. **Given** a romaneo in PENDIENTE status, **When** the operator attempts to record a gross weight, **Then** the system rejects the action because the romaneo has not yet confirmed arrival (must be EN_PROCESO first).

---

### User Story 3 - Record Quality Analysis (Priority: P1)

The laboratory analyst records the quality parameters from the grain sample (calado). Parameters include humidity percentage, foreign matter, damaged grains, broken grains, heat-damaged grains, foreign bodies, and grain-specific parameters (hectolitre weight for cereals, protein for wheat, green grains for soy). The system uses these parameters for merma calculation and grade assignment. Quality analysis creation is allowed when the romaneo is in EN_PROCESO or PESADO status.

**Why this priority**: Quality analysis determines the commercial deductions applied to the delivered grain. Incorrect or missing quality data leads to incorrect merma calculations, wrong producer payments, and potential regulatory violations.

**Independent Test**: Can be tested by creating a quality analysis record for an EN_PROCESO or PESADO romaneo with all required parameters and verifying the romaneo transitions to ANALIZADO with all parameter values stored at correct precision.

**Acceptance Scenarios**:

1. **Given** a romaneo in PESADO status, **When** the lab analyst records 9 quality parameters (humidity 15.2%, foreign matter 1.8%, damaged grains 2.1%, broken grains 3.5%, heat-damaged 0.3%, foreign bodies 0.1%, hectolitre weight 78.5 kg, protein 11.2%, green grains NULL), **Then** a QualityAnalysis record is created as a one-to-one satellite of the romaneo, the romaneo transitions to ANALIZADO, and the analysis timestamp is recorded.
2. **Given** a romaneo already has a quality analysis, **When** the analyst attempts to create a second quality analysis for the same romaneo, **Then** the system rejects the duplicate (one-to-one constraint enforced).
3. **Given** a romaneo in ANALIZADO status, **When** the analyst updates a quality parameter (e.g., correcting humidity from 15.2% to 15.4%), **Then** the system updates the existing quality analysis record.
4. **Given** a romaneo in CONFORME or CERRADO status, **When** the analyst attempts to update quality parameters, **Then** the system rejects the modification (immutability enforced).

---

### User Story 4 - Calculate Sequential Merma Deductions (Priority: P1)

When the operator confirms a romaneo (transition to CONFORME), the system calculates the sequential merma deductions following the Circular CAC 10/86 formula: zarandeo (screening) based on foreign matter percentage, secado (drying) based on moisture vs. regulatory final moisture, manipuleo (handling) as a fixed percentage applied only when drying occurs, and volatil (volatile loss) as a fixed percentage always applied. Each step operates on the result of the previous step, not the original weight. The calculation produces the final conforming weight (peso neto conforme) that is credited to the producer.

**Why this priority**: The merma calculation is the core business logic of the acopio. It directly determines the commercial weight credited to the producer and thus the financial settlement. An error of even 0.5% in the secado formula on a 30-tonne truck means approximately 150 kg of grain -- a significant financial impact for both the acopiador and producer.

**Independent Test**: Can be tested by confirming a romaneo with known quality parameters and verifying each intermediate merma value and the final peso_neto_conforme against hand-calculated reference values.

**Acceptance Scenarios**:

1. **Given** a romaneo in ANALIZADO status for trigo with quality analysis (Hi=15.2%, foreign matter=1.8%) and reference data (Hf=13.5%, zarandeo_deduction=1.0%, manipuleo=0.10%, volatil=0.30%), **When** the operator confirms the romaneo with grado_asignado=1, **Then** the system calculates merma sequentially: zarandeo deducts from net weight, secado deducts from post-zarandeo weight using formula (Hi-Hf)/(100-Hf)*100, manipuleo deducts from post-secado weight (applied because secado > 0), volatil deducts from post-manipuleo weight. All intermediate values and the final peso_neto_conforme are stored in an immutable MermaCalculation record.
2. **Given** a romaneo for soja with Hi=12.0% and Hf=12.5% (moisture below regulatory threshold), **When** the operator confirms, **Then** secado_pct = 0.00 and manipuleo is NOT applied (because no drying occurred). Only zarandeo and volatil deductions are applied.
3. **Given** a confirmed romaneo with a MermaCalculation record, **When** any user attempts to modify the MermaCalculation, **Then** the system rejects the update (fully immutable -- no edits, no deletes).
4. **Given** grain type trigo with hf_secado_pct=13.5% and humedad_base_pct=14.0%, **When** the merma engine calculates secado, **Then** it uses hf_secado_pct (13.5%), NOT humedad_base_pct (14.0%). Using the wrong value would cause approximately 168 kg error per 30-tonne truck.

---

### User Story 5 - Preview Merma Before Confirmation (Priority: P2)

Before confirming a romaneo (making it immutable), the operator can preview the projected merma deductions. This allows the operator (and optionally the producer) to review the deductions before they become final. The preview uses the same calculation engine but does not create any permanent record.

**Why this priority**: Previewing merma before confirmation reduces operator errors and potential disputes with producers. However, it is not required for the core reception workflow -- an operator can confirm directly without previewing.

**Independent Test**: Can be tested by requesting a merma preview on an ANALIZADO romaneo and verifying projected values are returned without any database record being created.

**Acceptance Scenarios**:

1. **Given** a romaneo in ANALIZADO status with a quality analysis, **When** the operator requests a merma preview, **Then** the system returns projected zarandeo, secado, manipuleo, volatil percentages and intermediate weights without creating a MermaCalculation record.
2. **Given** a romaneo in PESADO status without a quality analysis, **When** the operator requests a merma preview, **Then** the system rejects the request (quality data required for calculation).
3. **Given** a merma preview was generated, **When** the operator later confirms the romaneo, **Then** the final MermaCalculation may differ from the preview if quality analysis was updated between preview and confirmation.

---

### User Story 6 - Enforce Romaneo State Machine (Priority: P1)

The romaneo follows a strict linear lifecycle: PENDIENTE (created) -> EN_PROCESO (arrival confirmed) -> PESADO (gross weight captured) -> ANALIZADO (quality analysis complete) -> CONFORME (merma calculated, confirmed by operator) -> CERRADO (tare captured, CPE closed). No state can be skipped. Once a romaneo reaches CONFORME status, it becomes immutable -- no field changes are permitted except the final transition to CERRADO.

**Why this priority**: The state machine ensures data integrity and regulatory compliance. Each state guarantees that prerequisite data has been captured before proceeding. The immutability gate at CONFORME prevents retroactive changes to commercial weights, protecting both the acopiador and producer.

**Independent Test**: Can be tested by attempting all valid and invalid state transitions and verifying that only the correct linear sequence is accepted while out-of-order transitions are rejected.

**Acceptance Scenarios**:

1. **Given** a romaneo in PENDIENTE status, **When** the operator triggers each valid transition in sequence (confirmar-arribo -> peso-bruto -> analizar -> confirmar -> tara -> cerrar), **Then** the romaneo progresses through all 6 states in order, with each transition setting its corresponding timestamp.
2. **Given** a romaneo in PENDIENTE status, **When** the operator attempts to skip to PESADO (bypassing EN_PROCESO), **Then** the system rejects the transition with an error indicating the current status and the attempted invalid transition.
3. **Given** a romaneo in CONFORME status, **When** any user attempts to modify any field (e.g., changing grain_type or peso_bruto_kg), **Then** the system rejects the modification. Only the transition to CERRADO and tare capture are permitted.
4. **Given** a romaneo in CERRADO status, **When** any user attempts any modification, **Then** the system rejects it. CERRADO is the terminal state.

---

### User Story 7 - Assign Quality Grade with Bonificacion/Rebaja (Priority: P2)

When confirming a romaneo, the operator assigns a quality grade. For cereals (trigo, maiz, sorgo), grades 1/2/3 are assigned based on quality parameter thresholds, with bonificacion (bonus) for grade 1 and rebaja (penalty) for grade 3. For oleaginosas (soja, girasol), no grades apply; instead, progressive rebaja percentages are applied per percentage point above tolerance thresholds. The tolerance table version active at the romaneo's arrival time is used (not the current version).

**Why this priority**: Grading determines the price adjustment applied to the grain delivery. While important for accurate settlement, it builds on the merma calculation and quality analysis which are higher priority.

**Independent Test**: Can be tested by confirming romaneos for different grain types and verifying correct grade assignment and bonificacion/rebaja percentages against known tolerance table values.

**Acceptance Scenarios**:

1. **Given** a trigo romaneo in ANALIZADO status with all quality parameters within grade 1 thresholds, **When** the operator confirms with grado_asignado=1, **Then** bonificacion_rebaja_pct is set to +1.5% and the exact ToleranceTable version active at ts_entrada is stored.
2. **Given** a soja romaneo, **When** the operator confirms, **Then** grado_asignado is set to 0 (oleaginosa convention) and bonificacion_rebaja_pct reflects the progressive rebaja.
3. **Given** a romaneo confirmed on Monday using tolerance table version V1, **When** the tolerance table is updated to V2 on Tuesday, **Then** the romaneo still references V1. The grade does not retroactively change.

---

### User Story 8 - Close Romaneo and Trigger CPE Confirmation (Priority: P2)

After a romaneo is confirmed (CONFORME) and tare weight is captured, the operator closes the romaneo (CERRADO). Closing enqueues two asynchronous ARCA WSCPE operations: confirmarDescargaCPE and confirmacionDefinitivaCPEAutomotor. The romaneo state advances immediately regardless of whether ARCA is reachable (store-and-forward queue pattern).

**Why this priority**: Closing completes the reception workflow and initiates the regulatory notification. However, the core business value (accurate weight and merma) is already captured at CONFORME. Closing is an operational/regulatory step.

**Independent Test**: Can be tested by closing a CONFORME romaneo with tare captured and verifying the transition to CERRADO succeeds with async acknowledgment.

**Acceptance Scenarios**:

1. **Given** a romaneo in CONFORME status with tara_kg captured, **When** the operator closes the romaneo, **Then** the romaneo transitions to CERRADO and the system acknowledges asynchronously (CPE confirmation enqueued).
2. **Given** a romaneo in CONFORME status WITHOUT tara_kg, **When** the operator attempts to close, **Then** the system rejects the closure (tare weight is a prerequisite for closing).

---

### Edge Cases

- What happens when a truck has no trailer (single-unit vehicle)? The trailer plate field is nullable; the system accepts romaneos without a trailer plate.
- What happens when the weighbridge sends an invalid or zero weight? The system validates that gross and tare weights are positive non-zero values and rejects invalid readings.
- What happens when gross weight is less than tare (physically impossible)? The system validates that gross weight exceeds tare and rejects the tare capture if the invariant is violated.
- What happens when humidity is exactly equal to the regulatory threshold (Hi == Hf)? Secado deduction is 0.00 (no drying). Manipuleo is NOT applied since no drying occurred.
- What happens when all quality parameters are zero? The system accepts zero values as valid measurements. Only volatil deduction is applied (zarandeo and secado are zero, manipuleo not applied).
- What happens when the same CPE number is used for two romaneos? The system enforces uniqueness of CPE number within a tenant scope to prevent duplicate receptions.
- What happens when a romaneo is created offline and synced later? The server assigns a permanent sequential romaneo number at sync time, replacing the temporary client-generated placeholder. The tolerance table version is based on arrival timestamp (local creation time), not sync time.
- What happens when a merma lookup table has no matching band for the given foreign matter percentage? The system uses the closest applicable band or returns a clear error rather than silently defaulting to zero deduction.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow creation of a romaneo (grain reception document) capturing truck identification, driver details, CPE number, grain type, campaign, branch, and producer CUIT, initializing the romaneo in PENDIENTE status.
- **FR-002**: System MUST auto-generate a unique sequential romaneo number per branch in the format ROM-YYYY-NNNNN upon romaneo creation.
- **FR-003**: System MUST enforce a strict linear 6-state lifecycle: PENDIENTE -> EN_PROCESO -> PESADO -> ANALIZADO -> CONFORME -> CERRADO, rejecting any out-of-sequence state transitions.
- **FR-004**: System MUST capture gross weight (peso_bruto_kg) with 3-decimal-place precision during the EN_PROCESO -> PESADO transition and record the weighing timestamp.
- **FR-005**: System MUST capture tare weight (tara_kg) with 3-decimal-place precision while in CONFORME status and automatically compute peso_neto_bruto_kg as the difference between gross and tare.
- **FR-006**: System MUST support creation of a one-to-one quality analysis satellite record for a romaneo, capturing 6 common parameters (humidity, foreign matter, damaged grains, broken grains, heat-damaged grains, foreign bodies) and 3 grain-specific parameters (hectolitre weight for cereals, protein for wheat, green grains for soy), all with 2-decimal-place precision.
- **FR-007**: System MUST calculate sequential merma deductions following the Circular CAC 10/86 formula in strict order: zarandeo (from lookup table), secado (from moisture vs. regulatory Hf), manipuleo (fixed, only when secado > 0), volatil (fixed, always applied). Each step operates on the previous step's result.
- **FR-008**: System MUST use the regulatory final moisture value (hf_secado_pct) for the secado formula, NOT the commercial base moisture (humedad_base_pct). These are distinct values with different business meanings.
- **FR-009**: System MUST store all merma calculation inputs, intermediate values, and final weight in an immutable one-to-one record created at the CONFORME transition. This record cannot be updated or deleted.
- **FR-010**: System MUST enforce immutability on romaneo fields once status reaches CONFORME. Only the state transition to CERRADO and tare capture are permitted after CONFORME.
- **FR-011**: System MUST support a non-persisting merma preview that returns projected deductions without creating a permanent record, available when a quality analysis exists.
- **FR-012**: System MUST pin the exact tolerance table and merma table versions active at the romaneo's arrival timestamp, preventing retroactive grade changes from later table updates.
- **FR-013**: System MUST assign grades for cereals (1/2/3 based on tolerance thresholds) and set grade to 0 for oleaginosas by convention, with corresponding bonificacion/rebaja percentages.
- **FR-014**: System MUST enforce complete tenant isolation -- romaneos, quality analyses, and merma calculations are only accessible to the owning tenant.
- **FR-015**: System MUST provide a high-performance merma calculation engine with results identical between the primary engine and a reference implementation, ensuring no precision loss in decimal arithmetic.
- **FR-016**: System MUST record timestamps for each state transition event: arrival, gross weight, sampling, analysis, unloading, and tare.
- **FR-017**: System MUST return asynchronous acknowledgment for state transitions that trigger ARCA WSCPE operations (arrival confirmation and closure), allowing the romaneo to advance regardless of ARCA connectivity.

### Key Entities

- **Romaneo**: The grain reception document. Contains identification, timestamps, vehicle data, weights, CPE/origin references, storage assignment, and operator/quality outcome fields. Central entity linking quality analysis, merma calculation, and downstream processes (storage, producer accounts, settlement). Follows a 6-state lifecycle with an immutability gate.
- **QualityAnalysis**: One-to-one satellite of Romaneo capturing laboratory quality parameters from the grain sample. Parameters drive the merma calculation and grade assignment. One per romaneo, no duplicates. Includes common parameters (humidity, foreign matter, damaged grains, broken grains, heat-damaged grains, foreign bodies) and grain-specific parameters (hectolitre weight, protein, green grains).
- **MermaCalculation**: One-to-one immutable satellite of Romaneo storing the complete sequential merma formula result -- all inputs (net weight, humidity, regulatory moisture, foreign matter), intermediate values (post-zarandeo, post-secado, post-manipuleo weights), and final conforming weight. Created once at confirmation, never modified. Enables full audit reconstruction of how the commercial weight was determined.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Operators can complete the full romaneo lifecycle (create -> confirm arrival -> weigh -> analyse -> confirm -> tare -> close) for a grain delivery in under 5 minutes of system interaction time, with the merma calculation completing near-instantaneously at confirmation.
- **SC-002**: The merma calculation engine produces correct results for all standard grain types (trigo, maiz, soja, girasol, sorgo, cebada), verified against hand-calculated reference values with zero deviation in final conforming weight for at least 10 test vectors per grain type.
- **SC-003**: Saving a completed romaneo (including merma calculation) completes within 3 seconds under normal load (up to 50 concurrent users per tenant).
- **SC-004**: 100% of state machine enforcement tests pass -- no romaneo can skip a state, and no confirmed romaneo can be retroactively modified.
- **SC-005**: Tenant isolation is absolute -- no romaneo, quality analysis, or merma calculation from one tenant is accessible to another tenant under any access pattern.
- **SC-006**: The merma calculation engine and its reference implementation produce identical results for the same inputs across at least 10 cross-validation test vectors, with no precision discrepancy.
- **SC-007**: The system correctly distinguishes between regulatory final moisture and commercial base moisture for the secado formula. A dedicated validation confirms the approximately 168 kg error magnitude on a 30-tonne trigo truck when the wrong field is used.
- **SC-008**: Minimum 40 automated tests covering model creation, state transitions (valid and invalid), immutability enforcement, merma calculation correctness (multiple grain types), quality analysis lifecycle, tenant isolation, and romaneo number generation, with 90%+ line coverage on new code.
