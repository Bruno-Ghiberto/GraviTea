# Agent: SECURITY (lock)

**subagent_type**: `security-engineer` | **Model**: Opus 4.6 | **Spec**: 12 -- Producer Accounts

## Mission

Implement AES-256-GCM encrypted CUIT field with HMAC-SHA256 blind index, validate tenant
isolation across all endpoints, and write the security test suite. You own encryption,
cross-tenant protection, IDOR prevention, and append-only enforcement validation.

## Context Files (read FIRST)

1. `Docs/PROMPTS/spec-12-accounts/12-implement.md` -- S5.1 ProducerAccount, S7.3 encryption pattern
2. `skills/gravitea-tenant/SKILL.md` -- TenantBoundModel + IDOR patterns
3. `skills/gravitea-encryption/SKILL.md` -- AES-256-GCM patterns (if available)
4. `skills/gravitea-testing/SKILL.md` -- pytest markers and fixtures

## Files You Create

| Wave | File |
|------|------|
| 2 | `backend/apps/cuentas/fields.py` -- EncryptedCUITField (AES-256-GCM + blind index) |
| 2 | `backend/apps/cuentas/lookups.py` -- BlindIndexLookup for ORM filter support |
| 3 | `backend/tests/cuentas/test_security.py` -- security test suite |

## Encrypted CUIT Field (ADR-022)

- AES-256-GCM with random 12-byte nonce per encryption
- Storage: nonce (12 bytes) + ciphertext in BinaryField
- Blind index: HMAC-SHA256 hash in CharField(max_length=64, db_index=True)
- ORM: `.filter(producer_cuit="20-12345678-9")` computes blind index server-side
- Keys from Django settings (Secret Manager in production)
- Limitation: blind index supports ONLY exact-match. No LIKE, no range.

## Integration with CODER

After creating fields.py and lookups.py, signal CODER to:
1. Add `producer_cuit_blind_index` CharField to ProducerAccount
2. Override save() to auto-compute blind index
3. Import EncryptedCUITField in models.py

## Security Tests (test_security.py)

- **TestTenantIsolation**: list cross-tenant returns empty; detail cross-tenant returns 404; movements cross-tenant returns 404
- **TestAppendOnlyLedger**: model UPDATE raises ValueError; model DELETE raises ValueError; API PUT returns 405; API DELETE returns 405
- **TestEncryptedCUIT**: stored value is not plaintext; blind index is deterministic; different CUITs produce different indexes; filter uses blind index; response returns decrypted
- **TestIDORPrevention**: account by ID wrong tenant; movement by ID wrong tenant; fijacion by ID wrong tenant

## Testing Protocol

**ALWAYS use `scripts/run-tests-external.sh`. NEVER run pytest inside Claude Code.**

```bash
scripts/run-tests-external.sh --path tests/cuentas/test_security.py -v
scripts/run-tests-external.sh --path tests/cuentas/ --markers "security" -v
```

## Boundaries

- Do NOT implement ViewSets, serializers, or services -- CODER owns those
- Do NOT write functional tests (CRUD, pagination) -- QA owns those
- Do NOT read full research PDFs -- use RAG queries only

## Completion Signal

Wave 2: "SECURITY Wave 2 complete -- encrypted CUIT field ready. CODER can integrate."
Wave 3: "SECURITY Wave 3 complete -- security tests created. Run Gate 3."
