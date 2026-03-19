# Spec 12: Producer Accounts -- Implementation Context

**Branch**: `012-producer-accounts` | **Date**: 2026-03-17
**Spec**: `specs/005-acopio-hld/` (HLD), `Docs/Project Blueprint/Data Model & Domain Model.md` (Data Model v1.0 S6)
**Target app**: `backend/apps/cuentas/` (NEW Django app)

---

> **MANDATORY: CLAUDE CODE AGENT TEAMS WITH TMUX MULTI-PANE**
>
> This is an Implementation spec (09+). Execution REQUIRES Claude Code Agent Teams
> (https://code.claude.com/docs/en/agent-teams) with tmux multi-pane coordination.
> Single-session execution is NOT permitted. The orchestrator spawns specialized agents
> in separate tmux panes, each reading their instruction file before starting work.
>
> **tmux session setup (run BEFORE launching Claude Code):**
>
> ```bash
> cd ~/Documents/Projects/GraviTea && \
> export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 && \
> tmux has-session -t GraviTea 2>/dev/null || \
>   tmux new-session -d -s GraviTea -x 240 -y 60 && \
> tmux set-option -t GraviTea -g mouse on && \
> tmux set-option -t GraviTea -g history-limit 50000 && \
> tmux set-option -t GraviTea -g pane-border-status top && \
> tmux set-option -t GraviTea -g pane-border-format " #{pane_index}: #{pane_title} " && \
> tmux set-option -t GraviTea -g pane-border-style "fg=colour240" && \
> tmux set-option -t GraviTea -g pane-active-border-style "fg=colour75,bold" && \
> tmux set-option -t GraviTea -g status-right "#{pane_title} | %H:%M" && \
> tmux set-option -t GraviTea -g status-interval 5 && \
> tmux set-option -t GraviTea -g display-panes-time 3000 && \
> tmux set-option -t GraviTea -g pane-base-index 1 && \
> tmux set-option -t GraviTea -g base-index 1 && \
> tmux set-option -t GraviTea -g remain-on-exit off && \
> tmux attach-session -t GraviTea
> ```
>
> **REQUIRED env var in every pane:**
> ```bash
> export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
> ```

---

## 1. What You Are Building

The Producer Current Accounts module (`backend/apps/cuentas/`). This implements the dual-ledger
accounting system that tracks grain custody (kg) and monetary balances (ARS/USD) for each
producer, per plant, per grain type, per campaign.

Three Django models, four DRF ViewSets, one derived SQL aggregation view, and AES-256-GCM
encryption for the producer CUIT field with HMAC-SHA256 blind index for search.

This is a backend-only spec. No frontend. No Rust. No ARCA integration.

---

## 2. Agent Team Roster

| Role | Emoji | subagent_type | Model | Instruction File | Responsibility |
|------|-------|---------------|-------|------------------|----------------|
| CODER | wrench | `python-expert` | Opus 4.6 | `Docs/PROMPTS/spec-12-accounts/agents/agent-CODER.md` | Django models, ViewSets, serializers, services, migrations |
| QA | clipboard | `quality-engineer` | Sonnet 4.6 | `Docs/PROMPTS/spec-12-accounts/agents/agent-QA.md` | pytest test suites (unit + integration) |
| SECURITY | lock | `security-engineer` | Opus 4.6 | `Docs/PROMPTS/spec-12-accounts/agents/agent-SECURITY.md` | Encrypted CUIT field, tenant isolation validation, security tests |

The **Orchestrator** is the user's Claude Code session. It reads this file, spawns agents, and
coordinates wave execution. The orchestrator does NOT have an instruction file.

---

## 3. Wave Execution Order

### Wave 0: Orchestrator Setup

1. Orchestrator reads this entire file
2. Orchestrator reads each agent instruction file in `agents/`
3. Orchestrator spawns CODER, QA, and SECURITY in separate tmux panes
4. Each agent reads its instruction file and signals ready

### Wave 1: Models + Migrations (CODER only)

CODER creates:
- `backend/apps/cuentas/__init__.py`
- `backend/apps/cuentas/apps.py`
- `backend/apps/cuentas/models.py` -- ProducerAccount, AccountMovement, FijacionRecord
- `backend/apps/cuentas/admin.py`
- Migration via `python manage.py makemigrations cuentas`

CODER registers the app in `backend/gravitea/settings/base.py` INSTALLED_APPS.

**Gate 1 checkpoint**: Migration applies cleanly. All three models visible in Django admin shell.

### Wave 2: ViewSets + Serializers + Encrypted CUIT (parallel)

**CODER** creates:
- `backend/apps/cuentas/serializers.py`
- `backend/apps/cuentas/views.py` -- AccountViewSet, MovementViewSet, FijacionViewSet, PosicionConsolidadaView
- `backend/apps/cuentas/urls.py`
- `backend/apps/cuentas/services.py` -- business logic (create movement, validate fijacion, compute posicion)

**SECURITY** creates (in parallel):
- `backend/apps/cuentas/fields.py` -- EncryptedCUITField (AES-256-GCM + HMAC-SHA256 blind index)
- `backend/apps/cuentas/lookups.py` -- BlindIndexLookup for ORM `.filter(producer_cuit=value)`

SECURITY then signals CODER to integrate the encrypted field into ProducerAccount model.

**Gate 2 checkpoint**: All endpoints respond. Encrypted CUIT round-trips correctly.

### Wave 3: Test Suites (parallel)

**QA** creates:
- `backend/tests/cuentas/__init__.py`
- `backend/tests/cuentas/conftest.py` -- fixtures for ProducerAccount, AccountMovement
- `backend/tests/cuentas/test_models.py` -- unit tests
- `backend/tests/cuentas/test_views.py` -- integration tests
- `backend/tests/cuentas/test_services.py` -- business logic tests

**SECURITY** creates (in parallel):
- `backend/tests/cuentas/test_security.py` -- cross-tenant, IDOR, append-only, encryption tests

**Gate 3 checkpoint**: All tests pass via `scripts/run-tests-external.sh`.

### Wave 4: Integration Testing + Fix Cycle

All agents collaborate to fix any failing tests. QA runs the full suite.
CODER and SECURITY fix their respective domains.

**Gate 4 checkpoint**: Full test suite green. Done criteria satisfied.

---

## 4. Files to Create / Modify

### Files to CREATE (new)

| File | Agent | Wave |
|------|-------|------|
| `backend/apps/cuentas/__init__.py` | CODER | 1 |
| `backend/apps/cuentas/apps.py` | CODER | 1 |
| `backend/apps/cuentas/models.py` | CODER | 1 |
| `backend/apps/cuentas/admin.py` | CODER | 1 |
| `backend/apps/cuentas/serializers.py` | CODER | 2 |
| `backend/apps/cuentas/views.py` | CODER | 2 |
| `backend/apps/cuentas/urls.py` | CODER | 2 |
| `backend/apps/cuentas/services.py` | CODER | 2 |
| `backend/apps/cuentas/fields.py` | SECURITY | 2 |
| `backend/apps/cuentas/lookups.py` | SECURITY | 2 |
| `backend/tests/cuentas/__init__.py` | QA | 3 |
| `backend/tests/cuentas/conftest.py` | QA | 3 |
| `backend/tests/cuentas/test_models.py` | QA | 3 |
| `backend/tests/cuentas/test_views.py` | QA | 3 |
| `backend/tests/cuentas/test_services.py` | QA | 3 |
| `backend/tests/cuentas/test_security.py` | SECURITY | 3 |

### Files to MODIFY (existing)

| File | Agent | Change |
|------|-------|--------|
| `backend/gravitea/settings/base.py` | CODER | Add `"apps.cuentas"` to INSTALLED_APPS |
| `backend/gravitea/urls.py` | CODER | Include `apps.cuentas.urls` |

---

## 5. Entity Specifications

### 5.1 ProducerAccount

- Inherits: **TenantBoundModel**
- Composite uniqueness: `(tenant, producer_cuit_blind_index, branch, grain_type, campaign)`
- `producer_cuit`: EncryptedCUITField (AES-256-GCM plaintext, HMAC-SHA256 blind index -- ADR-022)
- `producer_cuit_blind_index`: CharField(max_length=64, db_index=True) -- deterministic hash for lookups
- `branch`: FK to Branch (PROTECT)
- `grain_type`: FK to GrainType (PROTECT)
- `campaign`: FK to CampanaConfig (PROTECT)
- `grain_balance_kg`: DecimalField(max_digits=17, decimal_places=3, default=Decimal("0"))
- `ars_balance`: DecimalField(max_digits=17, decimal_places=3, default=Decimal("0"))
- `usd_balance`: DecimalField(max_digits=17, decimal_places=3, default=Decimal("0"))
- `is_active`: BooleanField(default=True)

### 5.2 AccountMovement

- Inherits: **TenantBoundModel**
- **APPEND-ONLY LEDGER** -- Override save() to block UPDATE; override delete() to raise ValueError (ADR-008)
- `producer_account`: FK to ProducerAccount (PROTECT)
- `movement_type`: CharField choices from 8 types:
  CEG_DEPOSIT, LPG_SALE, FIJACION, RETIRO, SERVICE_CHARGE, CANJE_GRAIN_DEBIT, CANJE_INPUT_CREDIT, RETENTION_DEDUCTION
- `romaneo`: FK to Romaneo (SET_NULL, null=True, blank=True)
- `liquidacion`: FK to LiquidacionPrimaria (SET_NULL, null=True, blank=True)
- `quantity_kg`: DecimalField(max_digits=17, decimal_places=3, null=True, blank=True)
- `ars_amount`: DecimalField(max_digits=17, decimal_places=3, null=True, blank=True)
- `usd_amount`: DecimalField(max_digits=17, decimal_places=3, null=True, blank=True)
- `movement_at`: DateTimeField(auto_now_add=True)
- `reference_document`: CharField(max_length=100, null=True, blank=True)
- `notes`: TextField(null=True, blank=True)

### 5.3 FijacionRecord

- Inherits: **TenantBoundModel**
- `deposit_movement`: FK to AccountMovement (PROTECT) -- must be movement_type=CEG_DEPOSIT
- `liquidacion`: FK to LiquidacionPrimaria (PROTECT)
- `pizarra_price`: DecimalField(max_digits=17, decimal_places=3)
- `kg_fixed`: DecimalField(max_digits=17, decimal_places=3)
- `remaining_unfixed_kg`: DecimalField(max_digits=17, decimal_places=3)
- `fixed_at`: DateTimeField(auto_now_add=True)
- `fixed_by`: FK to AppUser (PROTECT)

---

## 6. API Endpoints

| Method | Path | ViewSet | Description |
|--------|------|---------|-------------|
| GET | `/api/v1/cuentas/accounts/` | AccountViewSet | List accounts (filter by producer_cuit, grain_type, campaign) |
| GET | `/api/v1/cuentas/accounts/{id}/` | AccountViewSet | Account detail with balances |
| GET | `/api/v1/cuentas/accounts/{id}/movements/` | MovementViewSet | Cursor-paginated append-only ledger |
| GET | `/api/v1/cuentas/posicion-consolidada/` | PosicionConsolidadaView | Derived SQL aggregation (ADR-013) |
| POST | `/api/v1/cuentas/fijaciones/` | FijacionViewSet | Create FijacionRecord |
| GET | `/api/v1/cuentas/fijaciones/` | FijacionViewSet | List FijacionRecords |

The CUIT filter on AccountViewSet accepts plaintext CUIT, computes the blind index server-side,
and queries via `producer_cuit_blind_index`. The response always returns the decrypted plaintext.

The posicion-consolidada endpoint returns a SQL aggregation across all branches for a given
producer+grain_type+campaign. It is a derived view, NOT a stored entity (ADR-013).

---

## 7. Key Code Patterns

### 7.1 TenantBoundModel Inheritance (gravitea-tenant skill)

```python
from apps.core.models.base import TenantBoundModel

class ProducerAccount(TenantBoundModel):
    class Meta:
        db_table = "cuentas_producer_account"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "producer_cuit_blind_index", "branch", "grain_type", "campaign"],
                name="unique_producer_account_per_context",
            )
        ]
```

### 7.2 Append-Only Ledger (ADR-008)

```python
class AccountMovement(TenantBoundModel):
    def save(self, *args, **kwargs):
        if self.pk and not self._state.adding:
            raise ValueError("AccountMovement is append-only. UPDATE is forbidden.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("AccountMovement is append-only. DELETE is forbidden.")
```

### 7.3 Encrypted CUIT Field (ADR-022, gravitea-encryption skill)

```python
# fields.py -- SECURITY agent implements this
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import hashlib, os

class EncryptedCUITField(models.BinaryField):
    """AES-256-GCM encrypted storage with HMAC-SHA256 blind index."""

    def get_prep_value(self, value):
        if value is None:
            return None
        nonce = os.urandom(12)
        aesgcm = AESGCM(self._get_key())
        ciphertext = aesgcm.encrypt(nonce, value.encode(), None)
        return nonce + ciphertext

    def from_db_value(self, value, expression, connection):
        if value is None:
            return None
        nonce, ciphertext = value[:12], value[12:]
        aesgcm = AESGCM(self._get_key())
        return aesgcm.decrypt(nonce, ciphertext, None).decode()

    @staticmethod
    def compute_blind_index(plaintext_cuit: str) -> str:
        """HMAC-SHA256 deterministic hash for equality search."""
        return hashlib.sha256(
            (settings.BLIND_INDEX_KEY + plaintext_cuit).encode()
        ).hexdigest()
```

### 7.4 Posicion Consolidada (ADR-013)

```python
# services.py -- derived aggregation, NOT a stored model
from django.db.models import Sum, F

def get_posicion_consolidada(tenant_id, producer_cuit_blind_index, grain_type_id=None, campaign_id=None):
    qs = ProducerAccount.objects.filter(
        tenant_id=tenant_id,
        producer_cuit_blind_index=producer_cuit_blind_index,
        is_active=True,
    )
    if grain_type_id:
        qs = qs.filter(grain_type_id=grain_type_id)
    if campaign_id:
        qs = qs.filter(campaign_id=campaign_id)
    return qs.values("grain_type__name", "campaign__campaign_code").annotate(
        total_grain_kg=Sum("grain_balance_kg"),
        total_ars=Sum("ars_balance"),
        total_usd=Sum("usd_balance"),
    )
```

---

## 8. Checkpoint Gates

### Gate 1 (after Wave 1)

```bash
cd backend && .venv/bin/python manage.py showmigrations cuentas
# Expected: migration listed with [X] applied

cd backend && .venv/bin/python manage.py shell -c "
from apps.cuentas.models import ProducerAccount, AccountMovement, FijacionRecord
print('ProducerAccount:', ProducerAccount._meta.db_table)
print('AccountMovement:', AccountMovement._meta.db_table)
print('FijacionRecord:', FijacionRecord._meta.db_table)
"
```

### Gate 2 (after Wave 2)

```bash
cd backend && .venv/bin/python manage.py shell -c "
from apps.cuentas.fields import EncryptedCUITField
idx = EncryptedCUITField.compute_blind_index('20-12345678-9')
print('Blind index length:', len(idx))  # Expected: 64
print('Deterministic:', idx == EncryptedCUITField.compute_blind_index('20-12345678-9'))
"

# Verify URL routing
cd backend && .venv/bin/python manage.py show_urls 2>/dev/null | grep cuentas || \
  .venv/bin/python manage.py shell -c "
from django.urls import reverse
print(reverse('account-list'))
"
```

### Gate 3 (after Wave 3)

```bash
scripts/run-tests-external.sh --path tests/cuentas/ --markers "unit" -v
scripts/run-tests-external.sh --path tests/cuentas/ --markers "integration" -v
scripts/run-tests-external.sh --path tests/cuentas/ --markers "security" -v
```

### Gate 4 (final)

```bash
scripts/run-tests-external.sh --path tests/cuentas/ -v
# Expected: ALL tests pass, zero failures
```

---

## 9. Testing Protocol

**ALWAYS use `scripts/run-tests-external.sh` to run tests. NEVER run pytest inside Claude Code.**

```bash
# Run all cuentas tests
scripts/run-tests-external.sh --path tests/cuentas/ -v

# Run only unit tests
scripts/run-tests-external.sh --path tests/cuentas/ --markers "unit" -v

# Run only integration tests
scripts/run-tests-external.sh --path tests/cuentas/ --markers "integration" -v

# Run only security tests
scripts/run-tests-external.sh --path tests/cuentas/ --markers "security" -v

# Run specific test file
scripts/run-tests-external.sh --path tests/cuentas/test_models.py -v
```

---

## 10. Research Inputs

### RAG Queries (run these for domain context)

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q "producer current account movements" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "canje grain barter supplies" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "grain pricing contracts market mechanisms" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "fijacion partial price fixation grain" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "posicion consolidada cross plant view" -l 5
```

### Critical Domain Facts

- A ProducerAccount is per-plant, per-grain-type, per-campaign. NOT a global account.
- The posicion consolidada is a cross-plant aggregation derived on demand (ADR-013). NOT stored.
- One CEG_DEPOSIT can spawn multiple FijacionRecords over time (partial fixation).
- `remaining_unfixed_kg` on FijacionRecord tracks open position, reaches 0 when fully fixed.
- The 8 movement types are authoritative per PRD v1.0 S4.4.
- AccountMovement is append-only (ADR-008). No UPDATE, no DELETE. Same pattern as GrainMovement.
- producer_cuit is AES-256-GCM encrypted with HMAC-SHA256 blind index (ADR-022).
- Blind index supports ONLY exact-match (equality) search. No LIKE, no range queries on CUIT.
- All weight fields: DECIMAL(17,3). All monetary fields: DECIMAL(17,3). Zero FLOAT/DOUBLE.

---

## 11. Dependencies

- **Depends on**: spec-09 (Grain Reference Data -- GrainType, CampanaConfig models must exist)
- **Depends on**: spec-10 (Romaneo Core -- Romaneo model must exist for FK references)
- **Blocks**: spec-14 (WSLPG Integration -- LiquidacionPrimaria credits via AccountMovement)
- **Blocks**: spec-16 (Canje -- CanjeOperation references ProducerAccount and AccountMovement)

If Romaneo or LiquidacionPrimaria models do not yet exist, CODER must create stub FK references
with `to="acopio.Romaneo"` string-based lazy references in the FK declarations.

---

## 12. Done Criteria

The implementation is DONE when ALL of the following are true:

1. `backend/apps/cuentas/` directory exists with all module files
2. Three models created: ProducerAccount, AccountMovement, FijacionRecord
3. All models inherit TenantBoundModel with proper tenant isolation
4. AccountMovement enforces append-only (save raises ValueError on UPDATE, delete raises ValueError)
5. ProducerAccount.producer_cuit uses AES-256-GCM encryption with HMAC-SHA256 blind index
6. Blind index supports exact-match ORM lookups (`.filter(producer_cuit=value)` works)
7. Composite uniqueness constraint on ProducerAccount enforced at DB level
8. Four API endpoints respond correctly (accounts, movements, posicion-consolidada, fijaciones)
9. Posicion consolidada returns derived SQL aggregation, not stored data
10. FijacionRecord validates deposit_movement is CEG_DEPOSIT type
11. All tests pass via `scripts/run-tests-external.sh --path tests/cuentas/ -v`
12. Security tests verify cross-tenant isolation, IDOR prevention, and append-only enforcement
13. Zero FLOAT or DOUBLE in any field definition -- all DECIMAL(17,3)
