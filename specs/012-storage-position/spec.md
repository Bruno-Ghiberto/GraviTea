# Feature Specification: Storage & Position

**Feature Branch**: `012-storage-position`
**Created**: 2026-03-19
**Status**: Draft
**Input**: Implement physical storage infrastructure (silos, celdas, bins), grain lot position ledger, and grain movement immutable ledger for the acopio grain elevator vertical

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Plant Manager Registers Storage Infrastructure (Priority: P1)

As a plant manager, I need to register the physical storage units (vertical silos, horizontal cells, drying bins) at my facility so that the system knows where grain can be stored and how much capacity each unit has.

**Why this priority**: Without a storage unit catalogue, no grain can be assigned to a physical location. This is the foundational data that all other storage operations depend on.

**Independent Test**: Can be fully tested by creating, listing, updating, and deactivating storage units via the API. Delivers value by establishing the facility's physical layout in the system.

**Acceptance Scenarios**:

1. **Given** an authenticated plant manager, **When** they create a storage unit with name "Silo 1", type "Vertical Silo", capacity 500 tonnes, and assign it to their branch, **Then** the storage unit is saved and appears in the list with a unique identifier.
2. **Given** a storage unit that currently holds grain, **When** the manager attempts to delete it, **Then** the system rejects the deletion with a clear error explaining the unit has active stock.
3. **Given** a list of 50 storage units, **When** the manager filters by branch and active status, **Then** only matching units are returned, each showing its current occupancy as a percentage of capacity.
4. **Given** two storage units at the same branch, **When** the manager tries to create a third with the same name, **Then** the system rejects it with a uniqueness error.

---

### User Story 2 - Operator Assigns Grain to Silo After Reception (Priority: P1)

As a scale operator, after a romaneo (grain reception) reaches the confirmed state, I need to assign the received grain to a specific storage unit and have the system automatically record the deposit, so that our grain inventory stays accurate.

**Why this priority**: This is the core operational flow — every confirmed romaneo must result in grain being deposited into a silo. Without this, the grain ledger has no entries and stock tracking is impossible.

**Independent Test**: Can be tested by confirming a romaneo, selecting a storage unit, and verifying that a deposit movement is created with the correct weight. The grain lot balance should increase by the deposited amount.

**Acceptance Scenarios**:

1. **Given** a romaneo in confirmed status with a net weight of 28,500 kg of soybean (Grade 2, Campaign 2025/26), **When** the operator assigns it to "Silo 3", **Then** the system creates a grain lot for that combination (or finds the existing one), records a deposit movement for 28,500 kg linked to the romaneo, and increments the lot's running balance.
2. **Given** two romaneos of the same grain type, grade, campaign, deposited into the same silo, **When** both are processed, **Then** they contribute to the same grain lot and the lot balance equals the sum of both deposits.
3. **Given** an empty storage unit, **When** grain is deposited, **Then** the storage unit's current grain type is automatically set to match the deposited grain.
4. **Given** a romaneo in confirmed status, **When** the operator assigns it to a silo, **Then** the romaneo record is updated with references to both the storage unit and the grain lot for direct navigability.

---

### User Story 3 - System Suggests Optimal Silo for Incoming Grain (Priority: P2)

As a scale operator receiving a grain truck, I need the system to suggest which silo is best suited for the incoming grain, so that I can make fast decisions during peak harvest without degrading grain quality through improper mixing.

**Why this priority**: During harvest peak, operators make hundreds of silo assignment decisions daily. An automated suggestion reduces errors and preserves grain grade segregation, but operators can function with manual selection if this feature is not yet available.

**Independent Test**: Can be tested by requesting a suggestion for a specific grain type, grade, and campaign, and verifying the returned ranked list prioritises compatible and available silos.

**Acceptance Scenarios**:

1. **Given** incoming wheat (Grade 1, Campaign 2025/26, 30,000 kg), **When** the operator requests a silo suggestion, **Then** the system returns a ranked list where silos already holding wheat Grade 1 from the same campaign appear first, followed by empty silos with sufficient capacity.
2. **Given** a silo that already holds soybean, **When** wheat is incoming, **Then** that silo does not appear in the suggestion list (grain type incompatibility).
3. **Given** a silo with only 5,000 kg of remaining capacity, **When** 30,000 kg of grain is incoming, **Then** that silo is excluded from suggestions (insufficient capacity).
4. **Given** the system suggests "Silo 5", **When** the operator overrides and selects "Silo 8" instead, **Then** the override reason is captured and logged.

---

### User Story 4 - Operator Records Grain Dispatch (Priority: P2)

As a dispatch operator, I need to record grain leaving a storage unit for delivery or transfer, so that the grain inventory reflects the actual outflow and the lot balance decreases accordingly.

**Why this priority**: Dispatches are the second most frequent movement type after deposits. Without dispatch recording, stock balances become overstated and cannot be reconciled with physical inventory.

**Independent Test**: Can be tested by recording a dispatch against a lot with known balance and verifying the balance decreases by the dispatched amount.

**Acceptance Scenarios**:

1. **Given** a grain lot with 100,000 kg balance, **When** the operator records a dispatch of 35,000 kg with truck plate, destination, and transport document reference, **Then** a withdrawal movement is created and the lot balance drops to 65,000 kg.
2. **Given** a grain lot with 10,000 kg balance, **When** the operator attempts to dispatch 15,000 kg, **Then** the system rejects the dispatch with a clear error indicating insufficient stock.
3. **Given** a completed dispatch, **When** any user attempts to modify or delete the dispatch movement, **Then** the system rejects the operation because movements are immutable.

---

### User Story 5 - Manager Transfers Grain Between Silos (Priority: P2)

As a plant manager, I need to transfer grain from one storage unit to another within the same plant, so that I can optimise storage layout or consolidate lots for better quality management.

**Why this priority**: Internal transfers are routine operations during storage management. They must be atomic (both sides recorded together) to prevent phantom stock.

**Independent Test**: Can be tested by transferring a known quantity between two silos and verifying that the source balance decreases and the destination balance increases by the same amount.

**Acceptance Scenarios**:

1. **Given** Silo A with 50,000 kg of wheat and Silo B empty, **When** the manager transfers 20,000 kg from Silo A to Silo B, **Then** two movements are created atomically: a transfer-out of 20,000 kg on Silo A's lot and a transfer-in of 20,000 kg on Silo B's lot.
2. **Given** a transfer request, **When** the source lot has insufficient balance, **Then** the system rejects the entire transfer (neither side is recorded).
3. **Given** a completed transfer, **When** viewing the movement ledger, **Then** both transfer-out and transfer-in movements are visible with matching timestamps and cross-references.

---

### User Story 6 - Manager Views Real-Time Stock Report (Priority: P2)

As a plant manager, I need a real-time stock report showing current grain holdings per silo, per grain type, per campaign, and total warehouse capacity utilisation, so that I can make informed operational and commercial decisions.

**Why this priority**: Stock visibility is essential for commercial operations (sales planning), regulatory reporting (ARCA stock declarations), and operational management (capacity planning during harvest).

**Independent Test**: Can be tested by creating several deposits and dispatches, then requesting the stock report and verifying aggregated totals match the sum of all movements.

**Acceptance Scenarios**:

1. **Given** grain deposits across 10 silos spanning 3 grain types and 2 campaigns, **When** the manager requests the stock report, **Then** the report shows current stock per silo (with occupancy percentage), per grain type, per campaign, and total warehouse utilisation.
2. **Given** the stock report, **When** the manager filters by grain type "Soybean" and campaign "2025/26", **Then** only matching records appear.
3. **Given** a recent deposit has been processed, **When** the stock report is viewed immediately after, **Then** it reflects the deposit (real-time, no cache delay).

---

### User Story 7 - Manager Performs Physical Inventory Reconciliation (Priority: P3)

As a plant manager, I need to enter physical weight measurements per silo and have the system compare them against the ledger balance, generating a reconciliation report showing variances and allowing me to apply adjustments.

**Why this priority**: Periodic physical counts are a regulatory requirement and essential for auditing. However, they happen monthly or quarterly, not daily, so this has lower priority than core deposit/dispatch operations.

**Independent Test**: Can be tested by entering measured weights that differ from ledger balances, verifying variance calculations, and confirming that applying the reconciliation creates adjustment movements.

**Acceptance Scenarios**:

1. **Given** Silo 1 has a ledger balance of 100,000 kg but the physical measurement is 98,500 kg, **When** the manager submits the reconciliation, **Then** the system shows a deficit of 1,500 kg for Silo 1.
2. **Given** the reconciliation report shows variances, **When** the manager applies the adjustments, **Then** adjustment movements are created for each silo with the variance amount, carrying the operator's identity and mandatory notes.
3. **Given** an adjustment movement has been applied, **When** anyone attempts to edit or delete it, **Then** the system rejects the operation (immutable ledger).

---

### User Story 8 - Supervisor Closes a Campaign Year (Priority: P3)

As a supervisor, I need to close a completed campaign year, validating that all romaneos are in final state and carrying remaining stock forward to the next campaign as "stock de enlace", so that the books are clean for the new agricultural cycle.

**Why this priority**: Campaign close happens once per grain type per year. It is critical for accounting and regulatory compliance but is infrequent and can be performed manually if the automated workflow is not yet available.

**Independent Test**: Can be tested by closing a campaign with known lots and verifying that carry-forward movements are created for non-zero balances.

**Acceptance Scenarios**:

1. **Given** a campaign "2024/25" with all romaneos in final state and 3 lots with remaining balances, **When** the supervisor initiates campaign close, **Then** the system validates all romaneos, creates carry-forward movements to new "2025/26" lots, and marks the campaign as closed.
2. **Given** a campaign with one romaneo still in an intermediate state, **When** the supervisor attempts to close the campaign, **Then** the system rejects the close with a clear error listing the incomplete romaneos.
3. **Given** a campaign close is in progress, **When** a system error occurs mid-operation, **Then** the entire close is rolled back atomically (no partial carries).
4. **Given** a regular operator (non-supervisor), **When** they attempt to close a campaign, **Then** the system denies the action with an insufficient permissions error.

---

### Edge Cases

- What happens when two operators simultaneously deposit grain into the same silo for the same lot? The system must handle concurrent deposits by using database-level locking to ensure the lot balance is updated atomically and no deposit is lost.
- How does the system handle a storage unit that already holds grain type A when grain type B is assigned? The system must reject the deposit because grain types cannot be mixed in a single storage unit (grain type compatibility check).
- What happens when a storage unit's nominal capacity is reached? The derived occupancy field prevents over-assignment via the cell suggestion algorithm, but the system does not enforce a hard capacity cap at the movement level — the operator may override if physical conditions allow (e.g., mounding).
- How does the system distinguish between a producer's deposited grain (third-party custody) and the acopiador's own purchased grain? Each grain lot carries an own-grain flag that routes to different accounting codes: own grain = balance-sheet asset; third-party = off-balance-sheet custody.
- What happens when a campaign has physically co-mingled grain from two campaign years in the same silo? The system tracks them as separate logical lots linked to different campaigns, even though the physical grain is mixed. This complies with Argentine regulatory requirements which mandate logical segregation by campaign.
- What if the grain lot running balance drifts from the sum of movements due to a software bug or data corruption? A background consistency check command detects and reports drift without automatically correcting it. Corrections are made via explicit adjustment movements.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow tenant administrators to create, list, update, and deactivate physical storage units per branch, each with a name, unit type (vertical silo, horizontal cell, or drying bin), nominal capacity in tonnes, and optional IoT sensor identifier.
- **FR-002**: System MUST enforce that storage unit names are unique within a tenant's branch.
- **FR-003**: System MUST compute and display each storage unit's current occupancy (in kilograms) as a derived value calculated from the grain movement ledger on demand — not stored as a static field.
- **FR-004**: System MUST prevent deletion of storage units that have non-zero stock in any active campaign.
- **FR-005**: System MUST maintain grain lot position records identified by the combination of branch, grain type, campaign year, quality grade, and storage unit. Each lot tracks a running kilogram balance.
- **FR-006**: System MUST automatically reuse an existing grain lot when a new deposit matches the same combination of branch, grain type, campaign, grade, and storage unit, incrementing the lot's running balance.
- **FR-007**: System MUST auto-generate a human-readable lot code on first creation following the pattern BRANCH-GRAIN-CAMPAIGN-GRADE.
- **FR-008**: System MUST persist an `is_own_grain` classification flag on each grain lot (own grain = balance-sheet asset 1.3.XX; third-party custody = off-balance-sheet 8.1.XX per Argentine RG 3593). In spec-12, all deposits via the `confirmar-conforme` flow default to `is_own_grain=False` (third-party custody, the primary acopio use case). Exposing this flag as a user-selectable parameter at deposit time is deferred to spec-13 (Producer Accounts).
- **FR-009**: System MUST record all grain movements as immutable append-only ledger entries. Each entry includes the target lot, movement type (deposit, withdrawal, transfer in, transfer out, or adjustment), quantity in kilograms, timestamp, operator identity, and optional document references.
- **FR-010**: System MUST reject any attempt to modify or delete an existing grain movement record. Corrections are made by creating new counter-entries.
- **FR-011**: System MUST reject any movement that would result in a grain lot's balance dropping below zero, with a clear error message before the operation is committed.
- **FR-012**: System MUST create a deposit movement when a romaneo reaches the confirmed state, linking the movement to the source romaneo and incrementing the target lot's balance by the romaneo's confirmed net weight.
- **FR-013**: System MUST update the romaneo record with references to both the assigned storage unit and the resolved grain lot, providing direct navigability from any romaneo to its storage location.
- **FR-014**: System MUST suggest a ranked list of compatible storage units for incoming grain based on grain type compatibility, available capacity, grade segregation, and campaign match. The operator may override the suggestion with a captured reason.
- **FR-015**: System MUST allow recording grain dispatches (outflows) from a storage unit, creating a withdrawal movement with the dispatched quantity and optional transport/document references.
- **FR-016**: System MUST support internal grain transfers between storage units of the same branch, creating paired transfer-out and transfer-in movements atomically in a single transaction.
- **FR-017**: System MUST produce a real-time stock report showing current stock per storage unit, per grain type, per campaign, and total warehouse capacity utilisation percentage, filterable by branch, grain type, and campaign.
- **FR-018**: System MUST accept physical weight measurements per storage unit and compare them against the ledger balance, returning a per-unit variance report. For each non-zero variance, the system MUST create an immutable ADJUSTMENT grain movement carrying the operator identity and a mandatory explanatory note.
- **FR-019**: System MUST allow a supervisor-level user to close a completed campaign year. The system MUST validate that all romaneos in the campaign are in a final state (CONFORME or CERRADO), create carry-forward grain movements (TRANSFER_IN to new campaign lots) for all non-zero lot balances, and mark the campaign as closed. The entire operation MUST be atomic — if any step fails, all changes are rolled back. Non-supervisor users MUST be rejected with an insufficient permissions error.

### Key Entities

- **Storage Unit**: A physical grain storage location (silo, cell, or drying bin) at a specific plant. Has a name, type, nominal capacity, current grain type, active status, and an IoT sensor anchor for future environmental monitoring. Belongs to a branch. Carries provenance fields (who created it, when).
- **Grain Lot**: A logical grain position record tracking the kilogram balance for a specific combination of branch, grain type, campaign year, quality grade, and storage unit. Carries an own-grain vs third-party flag for accounting classification. Auto-generated lot code. Running balance updated on every movement.
- **Grain Movement**: An immutable ledger entry recording a change in grain quantity for a specific lot. Types: deposit (inflow from romaneo), withdrawal (outflow for dispatch), transfer in/out (inter-silo movement), and adjustment (reconciliation correction). Once created, cannot be modified or deleted. Carries operator identity and provenance for audit trail.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Operators can assign incoming grain to a storage unit and have the deposit recorded within 5 seconds of confirmation, with no manual data re-entry.
- **SC-002**: The stock report displays current holdings accurate to the most recent confirmed movement, with no stale data or cache-induced delays.
- **SC-003**: Storage unit list with occupancy data loads within 1 second for facilities with up to 200 storage units.
- **SC-004**: 100% of grain movements are traceable: every kilogram deposited can be traced back to its source romaneo, and every kilogram withdrawn can be traced to a dispatch or transfer record.
- **SC-005**: Zero data leakage between tenants — no tenant can view, query, or modify another tenant's storage units, grain lots, or movements under any circumstances.
- **SC-006**: The grain lot running balance equals the arithmetic sum of all its movements at all times. A background consistency check can verify this across the entire database and report any drift.
- **SC-007**: No grain movement record can be modified or deleted through any system interface. Corrections to errors are exclusively made through new counter-entry movements.
- **SC-008**: Campaign close completes atomically — either all carry-forward movements are created and the campaign is marked closed, or the operation is fully rolled back with no partial state.
- **SC-009**: Reconciliation adjustments are fully auditable: every adjustment carries the operator's identity, a mandatory explanatory note, and a link to the reconciliation session.
- **SC-010**: Cell suggestion reduces manual silo assignment errors by providing a ranked recommendation that accounts for grain type, grade, campaign, and available capacity — operators always have the option to override.
