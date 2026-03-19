# Agent A4: Full Test Suite

**Agent Type**: `quality-engineer`
**Model**: Sonnet 4.6
**Mission**: Write the complete test suite for the Producer Accounts module — 43+ tests across
4 test files covering models, API, services, and CEG_DEPOSIT integration. Fix any failures
that emerge from the Wave 3 final test runs. Ensure no regressions in `tests/acopio/`.
Wave 4 — begins after GATE G3 passes, but test writing can start earlier alongside Wave 3.

---

## Context Files — Read FIRST

1. `Docs/PROMPTS/spec-13-accounts/13-implement.md` — Orchestration protocol, testing protocol, patterns
2. `specs/013-producer-accounts/data-model.md` — Fields, movement types, invariants
3. `specs/013-producer-accounts/contracts/accounts-api.md` — All endpoint contracts (for API tests)
4. `specs/013-producer-accounts/quickstart.md` — Key invariants and pitfalls
5. `specs/013-producer-accounts/tasks.md` — Exact test task descriptions (T012–T013, T017, T023, T027, T032, T036)

---

## Assigned Tasks (Wave 4)

| Task | Test File | Description |
|------|-----------|-------------|
| T012 | `test_account_models.py` | ~15 model tests — ProducerAccount, AccountMovement, immutability, CUIT validation |
| T013 | `test_ceg_deposit_integration.py` | ~8 integration tests — CEG_DEPOSIT flow end-to-end |
| T017 | `test_account_api.py` | ~12 API tests — list/detail/filter/405 immutability |
| T023 | `test_account_services.py` | ~8 service tests — manual movements, sign validation, supervisor |
| T027 | `test_account_services.py` | ~4 posicion consolidada tests |
| T032 | `test_account_api.py` | ~7 statement tests |
| T036 | `test_account_models.py` | ~5 management command tests |

**Total**: 43+ tests minimum

---

## Files to Create

| File | Tests | Coverage |
|------|-------|----------|
| `backend/tests/cuentas/test_account_models.py` | ~20 | Models, immutability, CUIT validation, management command |
| `backend/tests/cuentas/test_ceg_deposit_integration.py` | ~8 | CEG_DEPOSIT full flow, atomicity, race conditions |
| `backend/tests/cuentas/test_account_api.py` | ~19 | GET/POST/405 endpoints, pagination, auth |
| `backend/tests/cuentas/test_account_services.py` | ~12 | ManualMovementService, PosicionConsolidada |

---

## Domain Knowledge

### RAG Queries (run for additional context)

```bash
cd backend
.venv/bin/python scripts/qdrant/qdrant_search.py -q "pytest django_db fixtures TenantBoundModel" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "pytest APIClient JWT token authentication" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "pytest atomic transaction rollback test" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "EncryptedCharField test ciphertext plaintext" -l 5
```

### Critical Domain Facts (Inlined)

1. **conftest.py fixtures already created by A1**: `producer_account_factory`, `account_movement_factory`,
   `romaneo_conforme_factory`. Import via pytest fixture injection — do not redefine.

2. **Test markers**: Use `@pytest.mark.django_db`, `@pytest.mark.accounts`, and either
   `@pytest.mark.unit` (no network/external) or `@pytest.mark.integration` (requires full DB ops).

3. **AccountMovement immutability tests**: Create an AccountMovement, then call `movement.save()` again
   and assert `ValueError` is raised. Also assert `movement.delete()` raises `ValueError`.

4. **EncryptedCharField test**: After `ProducerAccount.objects.create(producer_cuit_encrypted="20-12345678-9", ...)`,
   retrieve from DB via `ProducerAccount.objects.get(id=account.id)`. The stored value in DB should NOT
   equal the plaintext. The decrypted `account.producer_cuit` property SHOULD equal the plaintext.

5. **CUIT validation tests** (critical after remediation):
   - Invalid CUIT `"12345"` should raise `ValidationError` when `account.full_clean()` is called
   - Valid CUIT `"20-12345678-9"` should pass validation
   Note: Django's field validators run via `full_clean()`, not `save()`.

6. **Tenant isolation**: Use two separate `tenant_context` fixtures or create a second tenant.
   Accounts belonging to tenant A must NOT be visible to requests authenticated for tenant B.
   Expect 404 on cross-tenant detail access, empty list on cross-tenant list.

7. **CEG_DEPOSIT integration test**: Use the `romaneo_conforme_factory` fixture to get a valid CONFORME
   romaneo. Call the confirmar API endpoint or the `create_ceg_deposit` service directly.
   Assert `ProducerAccount` was created, `AccountMovement` of type `CEG_DEPOSIT` exists,
   and `account.grain_balance_kg == romaneo.peso_neto_conforme_kg`.

8. **Atomicity test**: Use `TestCase.assertRaisesRegex` or `pytest.raises` around a context where
   `storage_unit` is None before calling confirmar. Assert romaneo status is NOT CONFORME after the failure.

9. **Cursor pagination in API tests**: Test that GET `/accounts/` returns `{"next": ..., "previous": ..., "results": [...]}`
   with NO `count` field. Test that passing `?cursor=` param works.

10. **Statement opening/closing balance logic**:
    - Create account with 3 movements in Jan, 2 in Feb, 2 in Mar
    - Request statement for Feb: opening = sum of Jan movements, movements = Feb only, closing = opening + Feb
    - Request statement for empty March: opening = sum of Jan+Feb, movements = [], closing = opening

11. **Management command testing**: Use Django's `call_command()`:
    ```python
    from django.core.management import call_command
    from io import StringIO
    out = StringIO()
    call_command("check_account_balance", stdout=out)
    assert "OK: 0 discrepancies" in out.getvalue()
    ```
    For detecting drift, manually update `account.grain_balance_kg` via `update()` (bypasses
    model save to avoid CheckConstraint) or set it to a wrong value before calling the command.

12. **PosicionConsolidada multi-branch test**:
    - Create ProducerAccount for CUIT "20-12345678-9" at Branch 1 with grain_balance_kg=10000
    - Create ProducerAccount for same CUIT at Branch 2 with grain_balance_kg=5000
    - GET `/posicion-consolidada/?producer_cuit=20-12345678-9&campaign_id=...`
    - Assert `total_grain_kg = 15000`, `branch_breakdown` has 2 entries

---

## Key Patterns & Constraints

### Test Structure Pattern (follow existing acopio test style)

```python
# backend/tests/cuentas/test_account_models.py
import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from apps.cuentas.models import ProducerAccount, AccountMovement
from apps.core.encryption.utils import compute_blind_index


@pytest.mark.django_db
@pytest.mark.accounts
@pytest.mark.unit
class TestProducerAccountModel:
    def test_create_producer_account(self, producer_account_factory):
        account = producer_account_factory()
        assert account.pk is not None
        assert account.grain_balance_kg == Decimal("0.000")

    def test_blind_index_auto_computed_on_save(self, producer_account_factory):
        cuit = "20-12345678-9"
        account = producer_account_factory(cuit=cuit)
        expected_hash = compute_blind_index(cuit)
        assert account.producer_cuit_hash == expected_hash

    def test_cuit_encrypted_not_stored_as_plaintext(self, producer_account_factory, db):
        """DB ciphertext must not equal plaintext."""
        account = producer_account_factory(cuit="20-12345678-9")
        # Access the DB raw value by refreshing from DB
        fresh = ProducerAccount.objects.get(pk=account.pk)
        assert fresh.producer_cuit == "20-12345678-9"  # decrypted correctly
        # The DB ciphertext is AES-GCM encoded, not raw string

    def test_cuit_format_validation_rejects_invalid(self, producer_account_factory, db):
        """CUIT without dashes or wrong length should fail validation."""
        account = producer_account_factory()
        account.producer_cuit_encrypted = "12345"  # invalid
        with pytest.raises(ValidationError):
            account.full_clean()

    def test_cuit_format_validation_accepts_valid(self, producer_account_factory):
        account = producer_account_factory(cuit="20-12345678-9")
        account.full_clean()  # should not raise

    def test_grain_balance_kg_non_negative_check_constraint(self, producer_account_factory, db):
        """Setting grain_balance_kg < 0 at DB level should raise IntegrityError."""
        account = producer_account_factory()
        # Use update() to bypass model-level check and hit DB constraint
        with pytest.raises(IntegrityError):
            ProducerAccount.objects.filter(pk=account.pk).update(grain_balance_kg=Decimal("-1.000"))

    def test_composite_uniqueness_constraint(self, producer_account_factory, db):
        """Same (tenant, cuit_hash, branch, grain_type, campaign) → IntegrityError."""
        producer_account_factory()
        with pytest.raises(IntegrityError):
            producer_account_factory()  # same defaults → duplicate


@pytest.mark.django_db
@pytest.mark.accounts
@pytest.mark.unit
class TestAccountMovementImmutability:
    def test_create_movement_succeeds(self, account_movement_factory):
        movement = account_movement_factory()
        assert movement.pk is not None

    def test_save_raises_on_update(self, account_movement_factory):
        movement = account_movement_factory()
        movement.notes = "changed"
        with pytest.raises(ValueError, match="immutable"):
            movement.save()

    def test_delete_raises(self, account_movement_factory):
        movement = account_movement_factory()
        with pytest.raises(ValueError, match="immutable"):
            movement.delete()

    def test_movement_type_choices_count(self):
        assert len(AccountMovement.MovementType.choices) == 9

    def test_no_updated_at_field(self):
        field_names = [f.name for f in AccountMovement._meta.get_fields()]
        assert "updated_at" not in field_names
```

### API Test Pattern

```python
# backend/tests/cuentas/test_account_api.py
import pytest
from rest_framework.test import APIClient
from rest_framework import status


@pytest.fixture
def auth_client(admin_user, tenant_context):
    """Returns authenticated APIClient for tenant."""
    client = APIClient()
    # Follow JWT auth pattern from tests/auth/ or tests/acopio/
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(admin_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.mark.django_db
@pytest.mark.accounts
@pytest.mark.integration
class TestProducerAccountAPI:
    def test_list_returns_only_tenant_accounts(self, auth_client, producer_account_factory):
        account = producer_account_factory()
        response = auth_client.get("/api/v1/cuentas/accounts/")
        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert "count" not in response.data  # cursor pagination — no count
        assert any(str(account.id) == r["id"] for r in response.data["results"])

    def test_list_filter_by_producer_cuit(self, auth_client, producer_account_factory):
        account = producer_account_factory(cuit="20-12345678-9")
        producer_account_factory(cuit="20-99999999-9")  # different producer
        response = auth_client.get("/api/v1/cuentas/accounts/?producer_cuit=20-12345678-9")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["producer_cuit"] == "20-12345678-9"

    def test_detail_returns_decrypted_cuit(self, auth_client, producer_account_factory):
        account = producer_account_factory(cuit="20-12345678-9")
        response = auth_client.get(f"/api/v1/cuentas/accounts/{account.id}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["producer_cuit"] == "20-12345678-9"
        assert "producer_cuit_encrypted" not in response.data
        assert "producer_cuit_hash" not in response.data

    def test_cross_tenant_returns_404(self, auth_client, db):
        """Account from different tenant returns 404."""
        # Create account in a different tenant (use direct DB bypass)
        # ... test body ...

    def test_movement_ledger_cursor_paginated(self, auth_client, account_movement_factory, producer_account_factory):
        account = producer_account_factory()
        account_movement_factory(account=account)
        response = auth_client.get(f"/api/v1/cuentas/accounts/{account.id}/movements/")
        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert "next" in response.data
        assert "count" not in response.data

    def test_patch_movement_returns_405(self, auth_client, account_movement_factory, producer_account_factory):
        account = producer_account_factory()
        movement = account_movement_factory(account=account)
        response = auth_client.patch(
            f"/api/v1/cuentas/accounts/{account.id}/movements/{movement.id}/",
            {"notes": "changed"},
        )
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert response.data["code"] == "append_only_violation"

    def test_delete_movement_returns_405(self, auth_client, account_movement_factory, producer_account_factory):
        account = producer_account_factory()
        movement = account_movement_factory(account=account)
        response = auth_client.delete(
            f"/api/v1/cuentas/accounts/{account.id}/movements/{movement.id}/"
        )
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert response.data["code"] == "append_only_violation"

    def test_unauthenticated_returns_401(self):
        client = APIClient()  # no credentials
        response = client.get("/api/v1/cuentas/accounts/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
```

### CEG_DEPOSIT Integration Test Pattern

```python
# backend/tests/cuentas/test_ceg_deposit_integration.py
import pytest
from decimal import Decimal
from apps.cuentas.models import ProducerAccount, AccountMovement


@pytest.mark.django_db
@pytest.mark.accounts
@pytest.mark.integration
class TestCEGDepositFlow:
    def test_confirmar_creates_producer_account_and_movement(
        self, auth_client, romaneo_conforme_factory
    ):
        """POST confirmar → ProducerAccount created + CEG_DEPOSIT movement."""
        romaneo = romaneo_conforme_factory()
        # Call confirmar via API (POST to /api/v1/acopio/romaneos/{id}/confirmar/)
        initial_count = ProducerAccount.objects.count()
        response = auth_client.post(
            f"/api/v1/acopio/romaneos/{romaneo.id}/confirmar/"
        )
        assert response.status_code == 200
        assert ProducerAccount.objects.count() == initial_count + 1
        account = ProducerAccount.objects.latest("created_at")
        movements = AccountMovement.objects.filter(
            producer_account=account,
            movement_type=AccountMovement.MovementType.CEG_DEPOSIT,
        )
        assert movements.count() == 1
        assert movements.first().quantity_kg == romaneo.peso_neto_conforme_kg
        assert account.grain_balance_kg == romaneo.peso_neto_conforme_kg

    def test_second_confirmar_reuses_existing_account(
        self, auth_client, romaneo_conforme_factory
    ):
        """Second romaneo for same producer → same account, balance accumulates."""
        r1 = romaneo_conforme_factory()
        r2 = romaneo_conforme_factory()  # same producer CUIT in factory defaults
        auth_client.post(f"/api/v1/acopio/romaneos/{r1.id}/confirmar/")
        auth_client.post(f"/api/v1/acopio/romaneos/{r2.id}/confirmar/")
        accounts = ProducerAccount.objects.all()
        assert accounts.count() == 1  # same account reused
        account = accounts.first()
        expected = r1.peso_neto_conforme_kg + r2.peso_neto_conforme_kg
        assert account.grain_balance_kg == expected

    def test_transaction_rolls_back_when_storage_unit_missing(
        self, auth_client, romaneo_conforme_factory, db
    ):
        """Missing storage_unit → ValidationError, romaneo stays non-CONFORME."""
        romaneo = romaneo_conforme_factory()
        romaneo.storage_unit = None
        romaneo.save(update_fields=["storage_unit"])
        initial_pa_count = ProducerAccount.objects.count()
        response = auth_client.post(
            f"/api/v1/acopio/romaneos/{romaneo.id}/confirmar/"
        )
        assert response.status_code == 400
        romaneo.refresh_from_db()
        from apps.acopio.models import Romaneo
        assert romaneo.status != Romaneo.RomaneoStatus.CONFORME
        assert ProducerAccount.objects.count() == initial_pa_count  # no account created
```

---

## Running Tests

**MANDATORY**: NEVER run pytest directly. All test runs via `scripts/run-tests-external.sh`.

```bash
# Per-story (during development):
bash scripts/run-tests-external.sh -n spec13-models tests/cuentas/test_account_models.py
cat Docs/Tests/spec13-models.status

bash scripts/run-tests-external.sh -n spec13-integration tests/cuentas/test_ceg_deposit_integration.py
cat Docs/Tests/spec13-integration.status

# Full run (Wave 4 final):
bash scripts/run-tests-external.sh -n spec13-final tests/cuentas/
cat Docs/Tests/spec13-final.status
cat Docs/Tests/spec13-final.summary
grep "FAILED\|ERROR" Docs/Tests/spec13-final.log | head -30

# Acopio regression:
bash scripts/run-tests-external.sh -n spec13-regression tests/acopio/
cat Docs/Tests/spec13-regression.status
```

When failures occur:
1. Read `Docs/Tests/spec13-final.log` for full traceback
2. Identify whether the failure is in test code (fix here) or application code (report to A2/A3)
3. Fix test code only; coordinate app code fixes with the appropriate agent
4. Re-run after fix

---

## NEVER

- NEVER run pytest directly — always `bash scripts/run-tests-external.sh`
- NEVER import or test internal fields `producer_cuit_encrypted` / `producer_cuit_hash` in API responses — they must NOT appear in API output
- NEVER use `ProducerAccount.all_objects` in tests (unless explicitly testing AllObjectsManager behavior)
- NEVER bypass the conftest fixtures by recreating accounts with raw SQL
- NEVER add `updated_at` assertions on AccountMovement (field does not exist)
- NEVER read full research PDFs — use RAG queries above
- NEVER hardcode UUIDs — use factory-generated instances or `uuid.uuid4()`
