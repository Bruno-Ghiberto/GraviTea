# Data Model: Romaneo Core

**Feature**: 011-romaneo-core | **Date**: 2026-03-19

## Entities

### Romaneo

The central grain reception document. Tenant-scoped, 31 fields across 7 groups.

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| id | UUID (PK) | No | Auto-generated |
| tenant | FK(Tenant) PROTECT | No | Owning tenant |
| romaneo_number | CharField(20) | No | Auto-generated: ROM-YYYY-NNNNN per branch |
| status | CharField (choices) | No | Default: PENDIENTE. 6 states. |
| grain_type | FK(GrainType) PROTECT | No | Grain species |
| campaign | FK(CampanaConfig) PROTECT | No | Active campaign |
| branch | FK(Branch) PROTECT | No | Receiving plant |
| ts_entrada | DateTimeField | No | Arrival timestamp |
| ts_pesada_bruta | DateTimeField | Yes | Gross weight timestamp |
| ts_calado | DateTimeField | Yes | Sampling timestamp |
| ts_analisis | DateTimeField | Yes | Analysis completion timestamp |
| ts_descarga | DateTimeField | Yes | Unloading timestamp |
| ts_tara | DateTimeField | Yes | Tare weight timestamp |
| patente_chasis | CharField(15) | No | Truck plate |
| patente_acoplado | CharField(15) | Yes | Trailer plate |
| driver_name | CharField(200) | No | Driver name |
| driver_dni | CharField(20) | No | Driver DNI |
| peso_bruto_kg | DecimalField(17,3) | Yes | Gross weight |
| tara_kg | DecimalField(17,3) | Yes | Tare weight |
| peso_neto_bruto_kg | DecimalField(17,3) | Yes | Computed: bruto - tara |
| weighbridge_device | CharField(100) | Yes | Placeholder for future FK |
| cpe_numero | CharField(20) | No | CPE number |
| ctg_codigo | CharField(20) | Yes | CTG code (from ARCA) |
| producer_cuit | CharField(13) | No | Producer CUIT |
| origin_locality | CharField(200) | No | Origin locality |
| operator_id | FK(AppUser) PROTECT | No | Responsible operator |
| laboratorista_id | FK(AppUser) SET_NULL | Yes | Lab analyst |
| device_id | CharField(100) | Yes | Capture device |
| grado_asignado | IntegerField | Yes | Grade: 1/2/3 (cereals), 0 (oleaginosas), NULL before analysis |
| bonificacion_rebaja_pct | DecimalField(5,2) | Yes | Price adjustment % |
| tolerance_table_version | FK(ToleranceTable) PROTECT | Yes | Pinned version |
| peso_neto_conforme_kg | DecimalField(17,3) | Yes | Final commercial weight |

**State Machine**:
```
PENDIENTE -> EN_PROCESO -> PESADO -> ANALIZADO -> CONFORME -> CERRADO
                                                    ↑ IMMUTABILITY GATE
```

**Indexes**: (tenant_id, status, ts_entrada), (tenant_id, branch_id, ts_entrada), (tenant_id, campaign_id, grain_type_id)

**Constraints**: UNIQUE(tenant, cpe_numero), UNIQUE(tenant, romaneo_number)

### QualityAnalysis

One-to-one satellite of Romaneo. Tenant-scoped. Captures lab quality parameters.

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| id | UUID (PK) | No | Auto-generated |
| romaneo | OneToOne(Romaneo) CASCADE | No | Parent romaneo |
| humedad_pct | DecimalField(5,2) | No | Moisture % (Hi for secado) |
| materias_extranas_pct | DecimalField(5,2) | No | Foreign matter % (drives zarandeo) |
| granos_danados_pct | DecimalField(5,2) | No | Damaged grains % |
| granos_quebrados_pct | DecimalField(5,2) | No | Broken grains % |
| peso_hectolitrico_kg | DecimalField(5,2) | Yes | Hectolitre weight (cereals only) |
| proteina_pct | DecimalField(5,2) | Yes | Protein % (trigo only) |
| granos_verdes_pct | DecimalField(5,2) | Yes | Green grains % (soja only) |
| granos_ardidos_pct | DecimalField(5,2) | No | Heat-damaged grains % |
| cuerpos_extranos_pct | DecimalField(5,2) | No | Foreign bodies % |
| analysis_timestamp | DateTimeField | No | When sample was analysed |
| sample_reference | CharField(50) | Yes | Lab sample reference |

### MermaCalculation

One-to-one immutable satellite of Romaneo. Tenant-scoped. Stores full merma audit trail.

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| id | UUID (PK) | No | Auto-generated |
| romaneo | OneToOne(Romaneo) CASCADE | No | Parent romaneo |
| merma_table_version | FK(MermaTable) PROTECT | No | Pinned MermaTable version |
| peso_neto_bruto_input_kg | DecimalField(17,3) | No | Input snapshot |
| hi_input_pct | DecimalField(5,2) | No | Humidity input (Hi) |
| hf_used_pct | DecimalField(5,2) | No | Regulatory moisture used (Hf) |
| materias_extranas_input_pct | DecimalField(5,2) | No | Foreign matter input |
| zarandeo_pct | DecimalField(5,2) | No | Zarandeo deduction |
| secado_pct | DecimalField(5,2) | No | Secado deduction (0 if Hi <= Hf) |
| manipuleo_pct | DecimalField(5,2) | No | Manipuleo deduction (0 if no secado) |
| volatil_pct | DecimalField(5,2) | No | Volatil deduction |
| peso_post_zarandeo_kg | DecimalField(17,3) | No | After zarandeo |
| peso_post_secado_kg | DecimalField(17,3) | No | After secado |
| peso_post_manipuleo_kg | DecimalField(17,3) | No | After manipuleo |
| peso_final_kg | DecimalField(17,3) | No | Final weight |
| total_merma_kg | DecimalField(17,3) | No | Total deduction |
| total_factor_pct | DecimalField(7,4) | No | Combined factor |
| calculated_at | DateTimeField | No | auto_now_add |
| calculated_by | FK(AppUser) PROTECT | No | Operator who triggered |

**Immutability**: `save()` raises ValueError if record exists. `delete()` raises ValueError.

## Relationships

```
GrainType (spec-10, GLOBAL) ──1:N──> Romaneo
CampanaConfig (spec-10, TENANT) ──1:N──> Romaneo
ToleranceTable (spec-10, GLOBAL) ──1:N──> Romaneo (tolerance_table_version)
MermaTable (spec-10, GLOBAL) ──1:N──> MermaCalculation (merma_table_version)
Branch (core, TENANT) ──1:N──> Romaneo
Tenant (core) ──1:N──> Romaneo, QualityAnalysis, MermaCalculation
AppUser (auth) ──1:N──> Romaneo (operator_id, laboratorista_id), MermaCalculation (calculated_by)

Romaneo ──1:1──> QualityAnalysis (satellite)
Romaneo ──1:1──> MermaCalculation (immutable satellite)
```

## Validation Rules

- `peso_bruto_kg` and `tara_kg` must be positive non-zero
- `peso_bruto_kg` > `tara_kg` (validated at tare capture)
- `cpe_numero` unique within tenant scope
- `romaneo_number` unique within tenant scope
- State transitions strictly linear (no skips)
- No field modifications after CONFORME (except tare capture and status -> CERRADO)
- No modifications at all after CERRADO
- MermaCalculation: no updates, no deletes
- QualityAnalysis: one per romaneo (OneToOne enforced)
- Tolerance/merma table versions pinned at `ts_entrada`
