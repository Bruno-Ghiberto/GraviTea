# Feature Specification: Grain Reference Data

**Feature Branch**: `010-grain-reference`
**Created**: 2026-03-18
**Status**: Draft
**Input**: Implement the grain reference data layer for the acopio (grain elevator) module -- foundational reference tables that all downstream grain operations depend on.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse Official Grain Types (Priority: P1)

As an acopio plant operator, I need to see the complete list of grain types recognized by ARCA (Argentina's tax authority) so I can select the correct grain when registering a new truck arrival (romaneo). Each grain must display its official ARCA species code, Spanish name, and base moisture percentage so I can quickly identify the right entry.

**Why this priority**: Every grain operation -- weighing, quality analysis, loss calculations, and government filings -- starts by selecting a grain type. Without this reference data, no downstream workflow can function. This is the foundational building block for the entire acopio module.

**Independent Test**: Can be fully tested by querying the grain types endpoint after seed data is loaded. Delivers immediate value as a browsable reference catalog for plant operators.

**Acceptance Scenarios**:

1. **Given** the system has been initialized with seed data, **When** an authenticated user requests the grain type list, **Then** at least 7 grain types are returned including Trigo pan (ARCA code 15), Maiz (19), Soja (23), Girasol (2), Sorgo (22), Cebada forrajera (11), and Cebada cervecera (17).
2. **Given** the grain type list is displayed, **When** the user filters by active status, **Then** only currently active grain types are shown and deprecated types are excluded.
3. **Given** the grain type list is displayed, **When** the user views a specific grain type, **Then** they see its internal code, ARCA species code, Spanish name, base moisture percentage, drying-formula moisture (Hf), fixed manipuleo deduction, fixed volatil deduction, and grading system type.

---

### User Story 2 - Manage Campaign Years (Priority: P1)

As an acopio administrator, I need to configure agricultural campaign years (campanas) for my organization so that all grain operations -- receipts, stock positions, and government filings -- are correctly assigned to the right marketing year. Each grain family has a different campaign start month (wheat/barley in December, corn/sorghum/sunflower in March, soybean in April), and only one campaign can be active at a time per organization.

**Why this priority**: Campaign year is a required field on romaneos, stock movements, and WSLPG government filings. Without campaign configuration, operators cannot process any grain transactions. Tied with P1 because it's the second mandatory reference entity.

**Independent Test**: Can be fully tested by creating, activating, and deactivating campaigns for a tenant. Delivers value as the time-boundary configuration that gates all grain operations.

**Acceptance Scenarios**:

1. **Given** an authenticated administrator, **When** they create a new campaign with code "2025/26" and valid date range, **Then** the campaign is created for their organization only and is not visible to other organizations.
2. **Given** a tenant has campaign "2024/25" active, **When** the administrator activates campaign "2025/26", **Then** the system enforces that only one campaign is active at a time -- the previous campaign is not automatically deactivated; the administrator must deactivate it first or the activation fails.
3. **Given** a campaign code "2025/26", **When** the system needs to submit data to ARCA's WSLPG service, **Then** the campaign code is convertible to WSLPG format "2526".
4. **Given** two different organizations, **When** each queries their campaigns, **Then** each sees only their own campaigns with complete data isolation between tenants.

---

### User Story 3 - Look Up Quality Tolerance Thresholds (Priority: P2)

As a grain quality analyst at the acopio plant, I need to look up the official tolerance thresholds for each grain type and quality parameter (moisture, foreign matter, damaged grains, etc.) so I can determine whether a received grain lot meets, exceeds, or falls below commercial grade standards. These tolerances are set by government resolutions (SAGPyA/SENASA) and vary by grain type and grade level.

**Why this priority**: Tolerance tables drive the bonification/rebaja (premium/discount) calculations applied to every grain lot. Without them, the quality grading workflow (spec-11) cannot determine price adjustments. P2 because the data is consumed by downstream specs rather than directly by plant operators.

**Independent Test**: Can be fully tested by querying tolerance entries for a specific grain type and verifying correct values against official government resolution tables.

**Acceptance Scenarios**:

1. **Given** seed data is loaded, **When** a user queries tolerance thresholds for Trigo pan (wheat), **Then** they receive tolerance entries for moisture, foreign matter, hectoliter weight, and other parameters organized by grade level (Grado 1, 2, 3).
2. **Given** tolerance tables support temporal versioning, **When** a new government resolution changes tolerance values, **Then** the old version is closed (end date set) and a new version is created, preserving the historical record for auditing.
3. **Given** tolerance data is loaded, **When** querying only currently active tolerances (no end date), **Then** exactly one active version per grain-parameter-grade combination is returned.

---

### User Story 4 - Look Up Grain Loss (Merma) Deduction Bands (Priority: P2)

As a grain operations manager, I need to look up the zarandeo (screening/sifting) deduction bands for each grain type so the system can calculate how much grain weight is deducted based on the foreign matter content of a received lot. These bands are regulatory tables that define progressive deduction percentages based on the foreign matter percentage range.

**Why this priority**: Merma deductions are applied to every grain receipt. The zarandeo bands are the reference data consumed by the merma calculation engine (spec-11, Rust implementation). Without these bands, grain loss calculations produce incorrect results. P2 because this data feeds into the calculation engine rather than being used directly by operators.

**Independent Test**: Can be fully tested by querying merma bands for a grain type and verifying that progressive deduction ranges cover the full foreign matter spectrum without gaps.

**Acceptance Scenarios**:

1. **Given** seed data is loaded, **When** a user queries merma bands for Trigo pan, **Then** multiple rows are returned representing progressive foreign matter ranges (e.g., 0-1% = 0% deduction, 1-2% = 1% deduction, 2-3% = 2% deduction, 3%+ = 3% + arbitration).
2. **Given** merma bands for a grain type, **When** reviewing the ranges, **Then** there are no gaps between the upper bound of one range and the lower bound of the next, and the final range has no upper bound (open-ended for extreme cases).
3. **Given** merma bands support temporal versioning, **When** regulatory changes update the deduction schedule, **Then** the old version is preserved and a new version becomes active, maintaining audit history.

---

### User Story 5 - Initialize Reference Data from Official Sources (Priority: P1)

As a system administrator performing initial deployment or data refresh, I need to load all official grain reference data (grain types, tolerance thresholds, and merma bands) from authoritative sources (ARCA species codes, Camara Arbitral de Cereales tables, SAGPyA/SENASA resolutions) in a single operation. The load must be safe to run multiple times without creating duplicate records.

**Why this priority**: Without seed data, the system has no grain types, no tolerance tables, and no merma bands -- making every other user story non-functional. This is the bootstrap operation that brings the system to life. P1 because it's the prerequisite for all other stories.

**Independent Test**: Can be fully tested by running the seed operation on an empty system, verifying record counts, then running it again and confirming no duplicates are created.

**Acceptance Scenarios**:

1. **Given** an empty system, **When** the administrator runs the seed data operation, **Then** at least 7 grain types, tolerance entries for 5 primary grains, and merma bands for 5 primary grains are loaded.
2. **Given** seed data has already been loaded, **When** the administrator runs the seed operation again, **Then** no duplicate records are created -- existing records are updated if values changed, and the operation completes successfully.
3. **Given** the seed operation supports a preview mode, **When** the administrator runs it in preview mode, **Then** the system reports what would be created/updated without making any changes.
4. **Given** seed data is loaded, **When** checking the Soja grain type, **Then** the drying-formula moisture (Hf) is 12.5% (not 13.5%) and the base moisture is 13.5% -- these two values must be distinct, as using the wrong one produces approximately 168 kg error per 30-tonne truck.

---

### Edge Cases

- What happens when an administrator attempts to create a campaign with an invalid code format (e.g., "2025-26" instead of "2025/26")? System rejects with a clear validation message.
- What happens when a campaign code has non-consecutive years (e.g., "2025/27")? System rejects the inconsistency.
- What happens when two grain types are loaded with the same ARCA species code? System enforces uniqueness and rejects the duplicate.
- What happens when querying tolerance tables for a grain type that has no entries? System returns an empty result set, not an error.
- What happens when the Cebada cervecera (malting barley) grain type has no manipuleo deduction (it's 0%)? System stores 0.00 as a valid value, not null.
- How does the system handle grain types with grading system "TOLERANCE" (soja, girasol) vs "GRADO" (trigo, maiz, sorgo)? The grading_system field distinguishes them, allowing downstream quality workflows to apply the correct evaluation logic.
- What happens when a tenant tries to access another tenant's campaign data? System enforces complete isolation -- cross-tenant access is prevented at both application and database levels.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST store and serve a catalog of grain types with official ARCA species codes (ncespecie), Spanish names, internal short codes, base moisture percentages, drying-formula moisture (Hf), fixed manipuleo deduction, fixed volatil deduction, and grading system classification (GRADO or TOLERANCE).
- **FR-002**: System MUST enforce that each grain type has a unique internal code and a unique ARCA species code -- no two grain types can share either identifier.
- **FR-003**: System MUST provide a grain type fixture containing at minimum the 7 primary Argentine grains: Trigo pan (15), Maiz (19), Soja (23), Girasol (2), Sorgo granifero (22), Cebada forrajera (11), Cebada cervecera (17), with all regulatory parameter values sourced from official Camara Arbitral tables.
- **FR-004**: System MUST support agricultural campaign year configuration per organization, storing the campaign code in "YYYY/YY" format (e.g., "2025/26") with start and end dates.
- **FR-005**: System MUST enforce that only one campaign is active per organization at any given time.
- **FR-006**: System MUST validate campaign codes: format must be "YYYY/YY", the two years must be consecutive, and the end date must be after the start date.
- **FR-007**: System MUST provide a conversion utility to transform campaign codes from internal format ("2024/25") to WSLPG submission format ("2425").
- **FR-008**: System MUST store quality tolerance thresholds per grain type and quality parameter, organized by grade level, with temporal versioning (valid_from/valid_to dates) to support regulatory changes without losing historical data.
- **FR-009**: System MUST store grain loss (merma) zarandeo deduction bands per grain type as progressive percentage ranges based on foreign matter content, with temporal versioning matching the tolerance table pattern.
- **FR-010**: System MUST provide a seed data operation that loads all three reference datasets (grain types, tolerance thresholds, merma bands) idempotently -- safe to run multiple times without creating duplicates.
- **FR-011**: System MUST provide a preview mode for the seed data operation that reports planned changes without applying them.
- **FR-012**: System MUST expose read-only query endpoints for grain types, tolerance tables, and merma tables accessible to all authenticated users regardless of organization membership.
- **FR-013**: System MUST expose full create/read/update/delete endpoints for campaign configuration, restricted to the authenticated user's organization with complete cross-tenant data isolation.
- **FR-014**: System MUST support filtering grain types by active status, tolerance tables by grain type and validity date, merma tables by grain type, and campaigns by active status.
- **FR-015**: System MUST return all list queries in a paginated envelope format with total count, next/previous page links, and results array.
- **FR-016**: Grain types, tolerance tables, and merma tables MUST be shared across all organizations (global reference data). Campaign configuration MUST be isolated per organization (tenant-scoped data).
- **FR-017**: System MUST provide administrative interfaces for managing all four reference data entities with appropriate display fields, filters, and search capabilities.

### Key Entities

- **Grain Type**: An officially recognized grain species with its ARCA code, commercial name, and regulatory parameters (moisture bases, fixed deduction percentages, grading system). Global entity shared across all organizations. Examples: Trigo pan (wheat), Soja (soybean), Maiz (corn).
- **Campaign Configuration**: An agricultural marketing year period defined per organization, with a code (e.g., "2025/26"), date range, and active status. Only one campaign can be active per organization at a time. Tenant-scoped entity.
- **Tolerance Table**: A versioned record of quality parameter tolerance thresholds for a specific grain type and grade level, established by government resolutions. Used to determine bonification/rebaja (premium/discount) on grain quality. Global entity.
- **Merma Table**: A versioned record of zarandeo (screening) deduction bands for a specific grain type, defining progressive weight deductions based on foreign matter content. Used by the merma calculation engine to compute grain loss. Global entity.

### Assumptions

- The 7 primary grain types cover 95%+ of Argentine grain elevator operations; extended grain types (triticale, canola, millet, etc.) can be added as supplementary fixtures later.
- Tolerance and merma values sourced from Camara Arbitral de Cereales and SAGPyA/SENASA resolutions are the authoritative regulatory reference.
- The Soja drying-formula moisture (Hf) of 12.5% is the correct implementation value per the Camara Arbitral software-implementation reference table, reconciling a discrepancy with the blueprint's 13.0% base-reference value.
- Cereals (trigo, maiz, sorgo) use the GRADO grading system (grades 1/2/3 with bonification/rebaja), while oleaginosas (soja, girasol) use the TOLERANCE system (progressive rebaja per percentage point above threshold).
- Campaign years are not grain-specific -- a single campaign period covers all grain types for an organization, even though different grains have different marketing year start months.
- The merma calculation engine consuming the zarandeo bands is out of scope for this spec (spec-11, Rust implementation). This spec provides the reference data only.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 7 primary grain types are queryable with correct ARCA codes and regulatory parameters within 1 second of system initialization.
- **SC-002**: Seed data operation completes successfully on both empty and pre-populated systems, producing identical end-state data with zero duplicate records.
- **SC-003**: Campaign creation, activation, and deactivation workflows complete in under 2 seconds per operation with correct tenant isolation verified.
- **SC-004**: Cross-tenant data isolation is enforced -- campaign data from Organization A is never visible to Organization B under any query pattern.
- **SC-005**: Tolerance and merma table lookups by grain type return results in under 1 second, supporting real-time quality grading workflows.
- **SC-006**: All reference data queries return paginated results in a consistent envelope format.
- **SC-007**: The drying-formula moisture (Hf) values are independently verified as distinct from base moisture values for all grain types where they differ, preventing the 168 kg/truck calculation error.
- **SC-008**: Temporal versioning allows regulatory changes to tolerance/merma tables without destroying historical records -- both current and historical versions are retrievable.
- **SC-009**: Test coverage reaches 90% or higher for all new grain reference data functionality.
- **SC-010**: Reference data (grain types, tolerances, merma bands) is accessible to users from any organization without tenant restrictions, while campaign data is strictly tenant-isolated.
