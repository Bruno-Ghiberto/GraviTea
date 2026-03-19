---
agent: A4
type: quality-engineer
model: Sonnet 4.6
mission: "Write comprehensive test suite for spec-10 and verify all acceptance criteria"
wave: 3
tasks: [T024, T028, T029, T033, T037, T039, T040, T041, T042]
---

# A4: Tests

## Context Files (read FIRST)

Read these files before writing any code:

1. `Docs/PROMPTS/spec-10-grain-reference/10-specify.md` -- acceptance criteria AC-10-001
   through AC-10-012, field definitions, domain facts
2. `Docs/PROMPTS/spec-10-grain-reference/10-plan.md` -- Pattern 12 (Test Fixtures),
   Testing Protocol, Gate 3, Gate 4
3. `specs/010-grain-reference/spec.md` -- user stories, acceptance scenarios, edge cases
4. `specs/010-grain-reference/tasks.md` -- test tasks
5. `specs/010-grain-reference/contracts/api.md` -- API response schemas for assertions

## Mission

Write and run the complete test suite:

1. Write API tests for all 4 endpoints (T024, T029, T033, T037)
2. Write model tests for CampanaConfig (T028) and GrainType (T039)
3. Write model tests for ToleranceTable/MermaTable (T040)
4. Run full test suite via external runner (T041)
5. Verify all 12 acceptance criteria (T042)

---

## Assigned Tasks

| Task | User Story | Description |
|------|-----------|-------------|
| T024 | US1 | Write API tests for GrainType endpoint in `backend/tests/acopio/test_api.py` |
| T028 | US2 | Write model tests for CampanaConfig in `backend/tests/acopio/test_models.py` |
| T029 | US2 | Write API tests for CampanaConfig endpoint in `backend/tests/acopio/test_api.py` |
| T033 | US3 | Write API tests for ToleranceTable endpoint in `backend/tests/acopio/test_api.py` |
| T037 | US4 | Write API tests for MermaTable endpoint in `backend/tests/acopio/test_api.py` |
| T039 | Polish | Write GrainType model unit tests in `backend/tests/acopio/test_models.py` |
| T040 | Polish | Write ToleranceTable and MermaTable model tests in `backend/tests/acopio/test_models.py` |
| T041 | Polish | Run full test suite via external runner |
| T042 | Polish | Run Gate 4 acceptance verification: confirm all 12 ACs pass |

---

## Domain Knowledge

### RAG Queries (optional -- for expected assertion values)

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q "grain types quality parameters reference" -l 3
```

### Critical Test Facts

- **Minimum 20 tests total** (AC-10-010).
- **Coverage target**: 90%+ for `apps/acopio/` (NF-010-005).
- **GrainType tests**: unique `code`, unique `arca_codigo`, `hf_secado_pct !=
  humedad_base_pct` for grains where they differ.
- **CampanaConfig tests**: format validation (`^\d{4}/\d{2}$`), consecutive years,
  one-active constraint per tenant (IntegrityError), tenant isolation, `wslpg_code`
  property conversion.
- **API tests**: paginated envelope (`count`/`next`/`previous`), auth required
  (401 without token), global tables same for all tenants, campaign tenant-isolated.
- **Seed tests**: idempotency (run twice, same count), dry-run (no writes),
  Soja `hf_secado_pct` = 12.50.

### Test Count Target

| File | Estimated Tests |
|------|----------------|
| `test_models.py` | 8--10 (fields, constraints, validation, wslpg_code, Hf check) |
| `test_api.py` | 8--10 (4 endpoints x list/detail, filtering, auth, tenant isolation) |
| `test_fixtures.py` | 4--6 (seed, idempotency, dry-run, data correctness) |
| **Total** | **20--26** |

---

## Testing Protocol (CRITICAL)

**NEVER** run pytest directly inside Claude Code. It consumes too many tokens and
can hang the session. **ALWAYS** use the external runner:

```bash
# Run all acopio tests
bash scripts/run-tests-external.sh -n spec10 tests/acopio/

# Poll for completion
cat Docs/Tests/spec10.status

# Read results
cat Docs/Tests/spec10.summary

# Debug failures (only if FAILED)
grep "FAILED" Docs/Tests/spec10.log
grep -A 10 "FAILED tests/acopio/test_" Docs/Tests/spec10.log

# Run with coverage
bash scripts/run-tests-external.sh -n spec10-coverage tests/acopio/
```

---

## Files to Create

```
backend/tests/acopio/test_models.py
backend/tests/acopio/test_api.py
backend/tests/acopio/test_fixtures.py
```

NOTE: `backend/tests/acopio/__init__.py` and `backend/tests/acopio/conftest.py` were
already created by A1 in Wave 1 (T012). Verify they exist. If additional fixtures
are needed for your test scenarios (beyond `grain_type_factory`, `campana_factory`,
and `seed_grain_types`), extend the conftest -- do not overwrite it.

---

## Existing Test Fixtures to Reuse

These fixtures are defined in `backend/tests/conftest.py` (root conftest) and are
automatically available to all tests:

| Fixture | Description | Use For |
|---------|-------------|---------|
| `tenant_context` | Creates tenant + sets tenant context | CampanaConfig tenant-scoped tests |
| `other_tenant` | Creates a second tenant | Cross-tenant isolation tests |
| `other_tenant_client` | Authenticated client for different tenant | API cross-tenant tests |
| `authenticated_client` | JWT-authenticated admin API client | All API endpoint tests |
| `api_client` | Unauthenticated API client | Auth-required (401) tests |
| `admin_user` | Admin user for primary tenant | API tests via `authenticated_client` |

These fixtures are in `backend/tests/acopio/conftest.py` (created by A1):

| Fixture | Description | Use For |
|---------|-------------|---------|
| `grain_type_factory` | Factory for creating GrainType instances | Model unit tests |
| `campana_factory` | Factory for creating CampanaConfig instances | Model + API tests |
| `seed_grain_types` | Loads all 7 grain types via management command | API tests needing data |

---

## Key Patterns

### Pattern: Model Unit Tests (T028, T039, T040)

```python
import pytest
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError


@pytest.mark.django_db
class TestGrainType:
    """GrainType model unit tests (AC-10-001, AC-10-012)."""

    def test_grain_type_creation(self, grain_type_factory):
        gt = grain_type_factory()
        assert gt.code == "TRI"
        assert gt.arca_codigo == 15
        assert gt.name == "Trigo pan"

    def test_grain_type_unique_code(self, grain_type_factory):
        grain_type_factory(code="TRI", arca_codigo=15)
        with pytest.raises(IntegrityError):
            grain_type_factory(code="TRI", arca_codigo=99)

    def test_grain_type_unique_arca_codigo(self, grain_type_factory):
        grain_type_factory(code="TRI", arca_codigo=15)
        with pytest.raises(IntegrityError):
            grain_type_factory(code="XXX", arca_codigo=15)

    def test_hf_not_equal_humedad_base(self, seed_grain_types):
        """AC-10-011: Hf != humedad_base for applicable grains."""
        from apps.acopio.models import GrainType
        grains_where_differ = GrainType.objects.exclude(code="CEB_C")
        for gt in grains_where_differ:
            assert gt.hf_secado_pct != gt.humedad_base_pct, (
                f"{gt.code}: hf_secado_pct ({gt.hf_secado_pct}) must differ "
                f"from humedad_base_pct ({gt.humedad_base_pct})"
            )

    def test_grain_type_str_repr(self, grain_type_factory):
        gt = grain_type_factory()
        assert str(gt) == "TRI - Trigo pan"


@pytest.mark.django_db
class TestCampanaConfig:
    """CampanaConfig model unit tests (AC-10-003)."""

    def test_campana_creation(self, campana_factory):
        campana = campana_factory()
        assert campana.campaign_code == "2025/26"

    def test_campana_code_format_validation(self, campana_factory):
        campana = campana_factory()
        campana.campaign_code = "2025-26"  # Wrong format
        with pytest.raises(ValidationError):
            campana.full_clean()

    def test_campana_consecutive_years_validation(self, campana_factory):
        campana = campana_factory()
        campana.campaign_code = "2025/27"  # Not consecutive
        with pytest.raises(ValidationError):
            campana.full_clean()

    def test_campana_date_range_validation(self, campana_factory):
        campana = campana_factory(
            start_date=date(2026, 12, 1),
            end_date=date(2025, 11, 30),  # end before start
        )
        with pytest.raises(ValidationError):
            campana.full_clean()

    def test_campana_one_active_per_tenant(self, campana_factory):
        campana_factory(campaign_code="2024/25", is_active=True)
        with pytest.raises(IntegrityError):
            campana_factory(campaign_code="2025/26", is_active=True)

    def test_wslpg_code_conversion(self, campana_factory):
        campana = campana_factory(campaign_code="2025/26")
        assert campana.wslpg_code == "2526"

    def test_campana_tenant_isolation(self, campana_factory, other_tenant):
        """AC-10-008: Campaigns are tenant-scoped."""
        from apps.acopio.models import CampanaConfig
        from apps.core.managers.tenant_bound import set_current_tenant_id
        campana_factory()  # Created for primary tenant
        set_current_tenant_id(other_tenant.id)
        assert CampanaConfig.objects.count() == 0  # Other tenant sees nothing


@pytest.mark.django_db
class TestToleranceTable:
    """ToleranceTable model unit tests (AC-10-004)."""

    def test_tolerance_versioning(self, seed_grain_types):
        from apps.acopio.models import GrainType, ToleranceTable
        trigo = GrainType.objects.get(code="TRI")
        active = ToleranceTable.objects.filter(
            grain_type=trigo, valid_to__isnull=True
        )
        assert active.count() > 0


@pytest.mark.django_db
class TestMermaTable:
    """MermaTable model unit tests (AC-10-005)."""

    def test_merma_bands_ordering(self, seed_grain_types):
        from apps.acopio.models import GrainType, MermaTable
        trigo = GrainType.objects.get(code="TRI")
        bands = MermaTable.objects.filter(
            grain_type=trigo, valid_to__isnull=True
        ).order_by("materias_extranas_from_pct")
        assert bands.count() > 0
```

### Pattern: API Integration Tests (T024, T029, T033, T037)

```python
import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestGrainTypeAPI:
    """GrainType API tests (AC-10-006, AC-10-007)."""

    def test_grain_types_list(self, authenticated_client, seed_grain_types):
        url = reverse("grain-type-list")
        response = authenticated_client.get(url)
        assert response.status_code == 200
        data = response.json()
        # Paginated envelope
        assert "count" in data
        assert "next" in data
        assert "previous" in data
        assert "results" in data
        assert data["count"] >= 7

    def test_grain_types_detail(self, authenticated_client, seed_grain_types):
        from apps.acopio.models import GrainType
        trigo = GrainType.objects.get(code="TRI")
        url = reverse("grain-type-detail", args=[trigo.id])
        response = authenticated_client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "TRI"
        assert data["codigo"] == 15  # mapped from arca_codigo
        assert data["nombre"] == "Trigo pan"  # mapped from name

    def test_grain_types_filter_active(self, authenticated_client, seed_grain_types):
        url = reverse("grain-type-list")
        response = authenticated_client.get(url, {"is_active": "true"})
        assert response.status_code == 200
        for gt in response.json()["results"]:
            assert gt["is_active"] is True

    def test_grain_types_requires_auth(self, api_client, seed_grain_types):
        url = reverse("grain-type-list")
        response = api_client.get(url)
        assert response.status_code == 401

    def test_grain_types_same_for_all_tenants(
        self, authenticated_client, other_tenant_client, seed_grain_types
    ):
        """AC-10-007: Global tables return same data for different tenants."""
        url = reverse("grain-type-list")
        resp_a = authenticated_client.get(url)
        resp_b = other_tenant_client.get(url)
        assert resp_a.json()["count"] == resp_b.json()["count"]


@pytest.mark.django_db
class TestCampanaConfigAPI:
    """CampanaConfig API tests (AC-10-006, AC-10-008)."""

    def test_campaigns_list_tenant_scoped(self, authenticated_client, campana_factory):
        campana_factory()
        url = reverse("campaign-list")
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert response.json()["count"] >= 1

    def test_campaigns_create(self, authenticated_client):
        url = reverse("campaign-list")
        payload = {
            "campaign_code": "2025/26",
            "start_date": "2025-12-01",
            "end_date": "2026-11-30",
            "is_active": False,
        }
        response = authenticated_client.post(url, payload, format="json")
        assert response.status_code == 201

    def test_campaigns_cross_tenant_isolation(
        self, authenticated_client, other_tenant_client, campana_factory
    ):
        """AC-10-008: CampanaConfig returns different data per tenant."""
        campana_factory()  # Created for primary tenant
        url = reverse("campaign-list")
        # Primary tenant sees campaign
        resp_a = authenticated_client.get(url)
        assert resp_a.json()["count"] >= 1
        # Other tenant sees nothing
        resp_b = other_tenant_client.get(url)
        assert resp_b.json()["count"] == 0

    def test_campaigns_requires_auth(self, api_client):
        url = reverse("campaign-list")
        response = api_client.get(url)
        assert response.status_code == 401


@pytest.mark.django_db
class TestToleranceTableAPI:
    """ToleranceTable API tests (AC-10-006, AC-10-007)."""

    def test_tolerance_tables_list(self, authenticated_client, seed_grain_types):
        url = reverse("tolerance-table-list")
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert response.json()["count"] > 0

    def test_tolerance_tables_filter_by_grain_type(
        self, authenticated_client, seed_grain_types
    ):
        from apps.acopio.models import GrainType
        trigo = GrainType.objects.get(code="TRI")
        url = reverse("tolerance-table-list")
        response = authenticated_client.get(url, {"grain_type": str(trigo.id)})
        assert response.status_code == 200
        for entry in response.json()["results"]:
            assert entry["grain_type"] == str(trigo.id)

    def test_tolerance_tables_same_for_all_tenants(
        self, authenticated_client, other_tenant_client, seed_grain_types
    ):
        url = reverse("tolerance-table-list")
        resp_a = authenticated_client.get(url)
        resp_b = other_tenant_client.get(url)
        assert resp_a.json()["count"] == resp_b.json()["count"]


@pytest.mark.django_db
class TestMermaTableAPI:
    """MermaTable API tests (AC-10-006, AC-10-007)."""

    def test_merma_tables_list(self, authenticated_client, seed_grain_types):
        url = reverse("merma-table-list")
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert response.json()["count"] > 0

    def test_merma_tables_filter_by_grain_type(
        self, authenticated_client, seed_grain_types
    ):
        from apps.acopio.models import GrainType
        trigo = GrainType.objects.get(code="TRI")
        url = reverse("merma-table-list")
        response = authenticated_client.get(url, {"grain_type": str(trigo.id)})
        assert response.status_code == 200
        for entry in response.json()["results"]:
            assert entry["grain_type"] == str(trigo.id)

    def test_merma_tables_same_for_all_tenants(
        self, authenticated_client, other_tenant_client, seed_grain_types
    ):
        url = reverse("merma-table-list")
        resp_a = authenticated_client.get(url)
        resp_b = other_tenant_client.get(url)
        assert resp_a.json()["count"] == resp_b.json()["count"]
```

---

## Constraints

- **NEVER** run pytest directly inside Claude Code. ALWAYS use `scripts/run-tests-external.sh`.
- Minimum 20 tests total across all 3 test files.
- All test classes must use `@pytest.mark.django_db` decorator.
- Reuse root conftest fixtures (`tenant_context`, `authenticated_client`,
  `other_tenant_client`, `api_client`). Do NOT recreate them.
- Reuse acopio conftest fixtures (`grain_type_factory`, `campana_factory`,
  `seed_grain_types`). Do NOT recreate them.
- All function parameters and return values must have type hints.
- All Python commands must use `.venv/bin/python`, never system python.

---

## Gate 3 Checks

Run after completing all test files.

```bash
# 1. Run full acopio test suite
bash scripts/run-tests-external.sh -n spec10-verify tests/acopio/

# 2. Poll for completion (repeat until not RUNNING)
cat Docs/Tests/spec10-verify.status

# 3. Read summary when status is PASSED or FAILED
cat Docs/Tests/spec10-verify.summary

# 4. If FAILED, debug specific failures
grep "FAILED" Docs/Tests/spec10-verify.log
grep -A 10 "FAILED tests/acopio/test_" Docs/Tests/spec10-verify.log
```

**Pass criteria**: `.status` file reads `PASSED`. Summary shows 0 failures, 0 errors.
Minimum 20 tests collected. If FAILED, fix failures and re-run.

---

## Gate 4 Checks (Final Acceptance)

After Gate 3 passes, verify all 12 acceptance criteria:

| AC | Description | How to Verify |
|----|-------------|---------------|
| AC-10-001 | GrainType model complete | `test_grain_type_creation` passes, all fields present |
| AC-10-002 | GrainType fixture loaded (>= 7 grains) | `test_seed_creates_grain_types` passes |
| AC-10-003 | CampanaConfig tenant isolation + one-active | `test_campana_one_active_per_tenant` + `test_campana_tenant_isolation` pass |
| AC-10-004 | ToleranceTable temporal versioning | `test_tolerance_versioning` passes |
| AC-10-005 | MermaTable zarandeo bands | `test_merma_bands_ordering` passes |
| AC-10-006 | All 4 API endpoints functional | All `test_*_list` tests pass |
| AC-10-007 | Global tables same for all tenants | All `test_*_same_for_all_tenants` tests pass |
| AC-10-008 | CampanaConfig tenant-isolated | `test_campaigns_cross_tenant_isolation` passes |
| AC-10-009 | Fixture idempotency | `test_seed_idempotency` passes |
| AC-10-010 | Test suite passing (>= 20 tests) | Gate 3 summary shows 20+ collected, 0 failures |
| AC-10-011 | Hf != humedad_base for applicable grains | `test_hf_not_equal_humedad_base` passes |
| AC-10-012 | ARCA code uniqueness enforced | `test_grain_type_unique_arca_codigo` passes |

Run coverage check:

```bash
bash scripts/run-tests-external.sh -n spec10-coverage tests/acopio/
cat Docs/Tests/spec10-coverage.summary
# Check TOTAL line -- coverage must be >= 90%
```

**Pass criteria**: All 12 ACs satisfied. Coverage >= 90%. 20+ tests, 0 failures.
