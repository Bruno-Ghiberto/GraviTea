---
name: gravitea-encryption
description: >
  Encryption patterns for GRAVITEA-ERP including AES-256-GCM encrypted fields, HMAC-SHA256 blind indexes for search, and key management.
  Trigger: When editing apps/core/encryption/, working with PII fields, barcode encryption, or searchable encrypted data.
license: MIT
metadata:
  author: gravitea-team
  version: "1.0"
---

# Gravitea Encryption Skill

Patterns for AES-256-GCM field encryption, HMAC-SHA256 blind indexes for searchable encrypted data, and secure key management.

## When to Use

- Adding encrypted fields to models (PII: tax_id, email, phone, address)
- Implementing searchable encrypted fields with blind indexes
- Working with barcode encryption on products
- Key management and rotation
- Database-level encryption conventions

---

## Critical Patterns

### Pattern 1: AES-256-GCM Encrypted CharField

**Stores PII encrypted at rest with automatic encryption/decryption.**

```python
# apps/core/encryption/fields.py
from django.db import models
from apps.core.encryption.utils import encrypt_value, decrypt_value


class EncryptedCharField(models.CharField):
    """
    AES-256-GCM encrypted CharField for PII storage.

    Stores: base64(nonce || ciphertext || tag)

    The field automatically encrypts on save and decrypts on load.
    Note: Encrypted values are larger than plain text, so max_length
    should account for ~100 bytes of overhead.

    Usage:
        tax_id_encrypted = EncryptedCharField(max_length=50)
    """

    def __init__(self, *args, **kwargs):
        # Add overhead for encryption (nonce + tag + base64 expansion)
        if "max_length" in kwargs:
            kwargs["max_length"] = kwargs["max_length"] + 100
        super().__init__(*args, **kwargs)

    def get_prep_value(self, value):
        """Encrypt value before saving to database."""
        if value is None or value == "":
            return value
        return encrypt_value(value)

    def from_db_value(self, value, expression, connection):
        """Decrypt value when loading from database."""
        if value is None or value == "":
            return value
        return decrypt_value(value)

    def to_python(self, value):
        """Handle value assignment and form cleaning."""
        if value is None:
            return value
        # If value looks like encrypted data (base64), decrypt it
        if isinstance(value, str) and len(value) > 50:
            try:
                return decrypt_value(value)
            except ValueError:
                # Not encrypted, return as-is
                pass
        return value
```

**Usage in models:**

```python
# apps/inventario/models.py
from apps.core.encryption.fields import EncryptedCharField, BlindIndexField

class Product(TenantBoundModel):
    sku = models.CharField(max_length=50, db_index=True)
    name = models.CharField(max_length=255)

    # Encrypted barcode with blind index for search
    barcode = EncryptedCharField(max_length=255, null=True, blank=True)
    barcode_blind_idx = BlindIndexField(null=True, blank=True, db_index=True)

    def save(self, *args, **kwargs):
        """Generate blind index for barcode if set."""
        if self.barcode and not self.barcode_blind_idx:
            from apps.core.encryption.utils import compute_blind_index
            self.barcode_blind_idx = compute_blind_index(self.barcode)
        super().save(*args, **kwargs)
```

---

### Pattern 2: Blind Index for Searchable Encryption

**HMAC-SHA256 hash enables exact-match lookups on encrypted data.**

```python
# apps/core/encryption/fields.py
class BlindIndexField(models.CharField):
    """
    HMAC-SHA256 hash field for exact-match searches on encrypted data.

    Creates a searchable blind index that allows equality lookups
    without exposing the plain text value.

    The field normalizes input (lowercase, strip) before hashing
    to ensure consistent lookups.

    Usage:
        # In model:
        tax_id_encrypted = EncryptedCharField(max_length=50)
        tax_id_hash = BlindIndexField(source_field='tax_id')

        # In code, update hash when setting encrypted value:
        supplier.tax_id_encrypted = "20-12345678-9"
        supplier.tax_id_hash = compute_blind_index("20-12345678-9")

        # Search by hash:
        Supplier.objects.filter(tax_id_hash=compute_blind_index("20-12345678-9"))
    """

    def __init__(self, *args, source_field=None, **kwargs):
        kwargs.setdefault("max_length", 64)  # SHA256 hex output
        kwargs.setdefault("db_index", True)  # Index for efficient lookups
        kwargs.setdefault("null", True)
        kwargs.setdefault("blank", True)
        kwargs.setdefault("editable", False)  # Auto-computed, not user-editable
        self.source_field = source_field
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.source_field:
            kwargs["source_field"] = self.source_field
        # Remove defaults for cleaner migrations
        if kwargs.get("max_length") == 64:
            del kwargs["max_length"]
        if kwargs.get("db_index") is True:
            del kwargs["db_index"]
        return name, path, args, kwargs

    @staticmethod
    def compute_hash(value):
        """
        Compute the blind index hash for a value.

        Args:
            value: Plain text value to hash.

        Returns:
            64-character hex string or None.
        """
        return compute_blind_index(value)
```

---

### Pattern 3: Encryption/Decryption Utilities

**Core cryptographic operations using AES-256-GCM.**

```python
# apps/core/encryption/utils.py
import os
import base64
import hmac
import hashlib
from typing import Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def get_encryption_key() -> bytes:
    """
    Get the AES-256 encryption key from environment.

    Key must be 32 bytes (256 bits).

    Raises:
        ValueError: If key is missing or invalid length.
    """
    key_b64 = os.environ.get("GRAVITEA_ENCRYPTION_KEY")
    if not key_b64:
        raise ValueError("GRAVITEA_ENCRYPTION_KEY environment variable not set")

    key = base64.b64decode(key_b64)
    if len(key) != 32:
        raise ValueError("Encryption key must be 32 bytes (256 bits)")

    return key


def get_hmac_key() -> bytes:
    """
    Get the HMAC key for blind index computation.

    Key should be at least 32 bytes for HMAC-SHA256.
    """
    key_b64 = os.environ.get("GRAVITEA_HMAC_KEY")
    if not key_b64:
        raise ValueError("GRAVITEA_HMAC_KEY environment variable not set")

    return base64.b64decode(key_b64)


def encrypt_value(value: str) -> str:
    """
    Encrypt a string value using AES-256-GCM.

    Args:
        value: Plain text to encrypt.

    Returns:
        Base64-encoded string containing nonce + ciphertext + tag.

    Format: base64(nonce[12] || ciphertext || tag[16])
    """
    if value is None:
        return None
    if value == "":
        return ""

    key = get_encryption_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit nonce for GCM

    ciphertext = aesgcm.encrypt(nonce, value.encode("utf-8"), None)

    # Combine nonce + ciphertext (tag is appended by AESGCM)
    encrypted = nonce + ciphertext

    return base64.b64encode(encrypted).decode("utf-8")


def decrypt_value(encrypted: str) -> str:
    """
    Decrypt a value encrypted with AES-256-GCM.

    Args:
        encrypted: Base64-encoded encrypted value.

    Returns:
        Decrypted plain text.

    Raises:
        ValueError: If decryption fails (invalid key, tampered data).
    """
    if encrypted is None:
        return None
    if encrypted == "":
        return ""

    key = get_encryption_key()
    aesgcm = AESGCM(key)

    try:
        data = base64.b64decode(encrypted)
        nonce = data[:12]
        ciphertext = data[12:]

        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")
    except Exception as e:
        raise ValueError(f"Decryption failed: {e}")


def compute_blind_index(value: str) -> Optional[str]:
    """
    Compute HMAC-SHA256 blind index for searchable encrypted fields.

    Normalizes input (lowercase, strip whitespace) before hashing
    to ensure consistent lookups.

    Args:
        value: Plain text value to hash.

    Returns:
        64-character hex string (SHA256 output) or None if value is None.
    """
    if value is None:
        return None

    key = get_hmac_key()

    # Normalize: lowercase, strip whitespace
    normalized = value.lower().strip()

    # Compute HMAC-SHA256
    h = hmac.new(key, normalized.encode("utf-8"), hashlib.sha256)

    return h.hexdigest()
```

---

### Pattern 4: Database Schema Convention

**Encrypted fields use `_encrypted` suffix, blind indexes use `_hash` suffix.**

```sql
-- database/SQL/001_schema.sql
CREATE TABLE customer (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenant(id),

    -- Plain text fields
    name VARCHAR(255) NOT NULL,

    -- Encrypted PII fields
    tax_id_encrypted TEXT,
    email_encrypted TEXT,
    phone_encrypted TEXT,
    address_encrypted TEXT,

    -- Blind indexes for search
    tax_id_hash CHAR(64),
    email_hash CHAR(64),
    phone_hash CHAR(64),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index blind indexes for efficient lookups
CREATE INDEX idx_customer_tenant_taxid_hash ON customer (tenant_id, tax_id_hash);
CREATE INDEX idx_customer_tenant_email_hash ON customer (tenant_id, email_hash);
```

---

### Pattern 5: Model with Encrypted Fields

**Complete model pattern with encrypted fields and auto-computed blind indexes.**

```python
# apps/customers/models.py
from apps.core.models import TenantBoundModel
from apps.core.encryption.fields import EncryptedCharField, BlindIndexField
from apps.core.encryption.utils import compute_blind_index


class Customer(TenantBoundModel):
    """
    Customer with encrypted PII fields.

    Encrypted fields:
    - tax_id_encrypted: Tax identifier (CUIT/CUIL in Argentina)
    - email_encrypted: Contact email
    - phone_encrypted: Contact phone
    - address_encrypted: Physical address

    Blind indexes (for search):
    - tax_id_hash: HMAC-SHA256 of normalized tax_id
    - email_hash: HMAC-SHA256 of normalized email
    - phone_hash: HMAC-SHA256 of normalized phone
    """

    # Plain text
    name = models.CharField(max_length=255)

    # Encrypted PII
    tax_id_encrypted = EncryptedCharField(max_length=50, null=True, blank=True)
    email_encrypted = EncryptedCharField(max_length=255, null=True, blank=True)
    phone_encrypted = EncryptedCharField(max_length=50, null=True, blank=True)
    address_encrypted = EncryptedCharField(max_length=500, null=True, blank=True)

    # Blind indexes for search
    tax_id_hash = BlindIndexField(source_field="tax_id_encrypted")
    email_hash = BlindIndexField(source_field="email_encrypted")
    phone_hash = BlindIndexField(source_field="phone_encrypted")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "tax_id_hash"],
                name="unique_customer_tax_id_per_tenant",
                condition=models.Q(tax_id_hash__isnull=False),
            ),
        ]

    def save(self, *args, **kwargs):
        """Auto-compute blind indexes before saving."""
        # Compute blind indexes for searchable fields
        if self.tax_id_encrypted:
            self.tax_id_hash = compute_blind_index(self.tax_id_encrypted)
        if self.email_encrypted:
            self.email_hash = compute_blind_index(self.email_encrypted)
        if self.phone_encrypted:
            self.phone_hash = compute_blind_index(self.phone_encrypted)

        super().save(*args, **kwargs)

    @classmethod
    def find_by_tax_id(cls, tenant, tax_id):
        """
        Find customer by tax ID using blind index.

        Args:
            tenant: Tenant instance
            tax_id: Plain text tax ID to search

        Returns:
            Customer or None
        """
        tax_id_hash = compute_blind_index(tax_id)
        return cls.objects.filter(
            tenant=tenant,
            tax_id_hash=tax_id_hash,
        ).first()
```

---

## Decision Tree

```
Adding a new field?
|-- Contains PII (tax_id, email, phone, address)?
|   |-- Yes -> Use EncryptedCharField
|   |   |-- Need to search by this field?
|   |   |   |-- Yes -> Add BlindIndexField companion
|   |   |   +-- No -> EncryptedCharField only
|   +-- No -> Regular CharField/TextField
|
|-- Contains barcode/product identifier?
|   +-- Use EncryptedCharField + BlindIndexField

Searching encrypted data?
|-- Exact match lookup?
|   +-- Use blind index: .filter(field_hash=compute_blind_index(value))
|-- Range/partial match?
|   +-- NOT SUPPORTED - Encryption prevents range queries
|-- Full text search?
|   +-- NOT SUPPORTED - Use non-encrypted searchable fields

Key management?
|-- Development? -> Use test keys in .env.local
|-- Production? -> Use secrets manager (AWS KMS, HashiCorp Vault)
|-- Key rotation needed? -> Re-encrypt all data with new key
```

---

## Anti-Patterns (What NOT to Do)

### Anti-Pattern 1: Searching Encrypted Fields Directly

```python
# FORBIDDEN - Cannot search encrypted ciphertext
Customer.objects.filter(email_encrypted__icontains="john")  # Will never match!

# CORRECT - Use blind index for exact match
email_hash = compute_blind_index("john@example.com")
Customer.objects.filter(email_hash=email_hash)
```

### Anti-Pattern 2: Logging Decrypted PII

```python
# FORBIDDEN - PII in logs
logger.info(f"Customer email: {customer.email_encrypted}")  # Shows decrypted!

# CORRECT - Log only non-sensitive identifiers
logger.info(f"Customer ID: {customer.id} updated")
```

### Anti-Pattern 3: Hardcoding Encryption Keys

```python
# FORBIDDEN - Keys in source code
ENCRYPTION_KEY = b"my-super-secret-key-12345678901"

# CORRECT - Keys from environment
key = get_encryption_key()  # Reads from GRAVITEA_ENCRYPTION_KEY
```

### Anti-Pattern 4: Missing Blind Index Updates

```python
# FORBIDDEN - Updating encrypted field without blind index
customer.tax_id_encrypted = "20-12345678-9"
customer.save()  # tax_id_hash is now stale!

# CORRECT - Let model's save() auto-compute, or update explicitly
customer.tax_id_encrypted = "20-12345678-9"
customer.tax_id_hash = compute_blind_index("20-12345678-9")
customer.save()

# BETTER - Use model save() which auto-computes (if implemented)
customer.tax_id_encrypted = "20-12345678-9"
customer.save()  # Model.save() computes blind index
```

### Anti-Pattern 5: Using Weak Hash for Blind Index

```python
# FORBIDDEN - MD5/SHA1 without HMAC (vulnerable to rainbow tables)
import hashlib
hash = hashlib.sha256(value.encode()).hexdigest()

# CORRECT - HMAC with secret key
key = get_hmac_key()
h = hmac.new(key, value.encode("utf-8"), hashlib.sha256)
hash = h.hexdigest()
```

---

## Testing Encryption

```python
# tests/encryption/test_fields.py
import pytest
from apps.core.encryption.utils import (
    encrypt_value,
    decrypt_value,
    compute_blind_index,
)
from apps.core.encryption.fields import EncryptedCharField, BlindIndexField


class TestEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        """Encrypted data can be decrypted."""
        original = "20-12345678-9"
        encrypted = encrypt_value(original)
        decrypted = decrypt_value(encrypted)

        assert decrypted == original
        assert encrypted != original  # Ciphertext differs

    def test_empty_values(self):
        """Empty/None values pass through unchanged."""
        assert encrypt_value(None) is None
        assert encrypt_value("") == ""
        assert decrypt_value(None) is None
        assert decrypt_value("") == ""

    def test_different_nonces(self):
        """Same plaintext produces different ciphertext."""
        value = "test value"
        encrypted1 = encrypt_value(value)
        encrypted2 = encrypt_value(value)

        assert encrypted1 != encrypted2  # Different nonces
        assert decrypt_value(encrypted1) == value
        assert decrypt_value(encrypted2) == value


class TestBlindIndex:
    def test_consistent_hash(self):
        """Same value produces same hash."""
        value = "john@example.com"
        hash1 = compute_blind_index(value)
        hash2 = compute_blind_index(value)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex

    def test_normalization(self):
        """Normalized values produce same hash."""
        hash1 = compute_blind_index("John@Example.COM")
        hash2 = compute_blind_index("  john@example.com  ")
        hash3 = compute_blind_index("john@example.com")

        assert hash1 == hash2 == hash3

    def test_different_values_different_hashes(self):
        """Different values produce different hashes."""
        hash1 = compute_blind_index("value1")
        hash2 = compute_blind_index("value2")

        assert hash1 != hash2


@pytest.mark.django_db
class TestEncryptedModel:
    def test_customer_find_by_tax_id(self, tenant, customer_factory):
        """Can find customer by tax ID using blind index."""
        customer = customer_factory(
            tenant=tenant,
            tax_id_encrypted="20-12345678-9",
        )

        found = Customer.find_by_tax_id(tenant, "20-12345678-9")
        assert found == customer

        # Different tax ID returns None
        not_found = Customer.find_by_tax_id(tenant, "20-99999999-9")
        assert not_found is None
```

---

## Commands

```bash
# Generate encryption key (32 bytes, base64 encoded)
python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"

# Generate HMAC key
python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"

# Run encryption tests
cd backend && pytest tests/encryption/ -v

# Test encryption in shell
cd backend && python manage.py shell -c "
from apps.core.encryption.utils import encrypt_value, decrypt_value
encrypted = encrypt_value('test')
print(f'Encrypted: {encrypted}')
print(f'Decrypted: {decrypt_value(encrypted)}')
"

# Verify blind index consistency
cd backend && python manage.py shell -c "
from apps.core.encryption.utils import compute_blind_index
print(compute_blind_index('test@example.com'))
print(compute_blind_index('TEST@EXAMPLE.COM'))  # Should match
"
```

---

## Environment Variables

```bash
# Required for encryption
GRAVITEA_ENCRYPTION_KEY=<base64-encoded-32-byte-key>
GRAVITEA_HMAC_KEY=<base64-encoded-32-byte-key>

# Example (DO NOT USE IN PRODUCTION)
# Generate with: python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
GRAVITEA_ENCRYPTION_KEY=qW5z8vF2j3kL9mN1pR4tY7uI0oP3aS6dF9gH2jK5lM8=
GRAVITEA_HMAC_KEY=xC7vB2nM5qK8wE1rT4yU7iO0pA3sD6fG9hJ2kL5zX8c=
```

---

## Developer Checklist

Before submitting encryption-related code, verify:

- [ ] PII fields use EncryptedCharField
- [ ] Searchable encrypted fields have BlindIndexField companion
- [ ] Blind index updated in model's save() method
- [ ] No PII logged (use IDs instead)
- [ ] Keys loaded from environment, not hardcoded
- [ ] max_length accounts for encryption overhead (+100 bytes)
- [ ] Database indexes on blind index columns
- [ ] Unique constraints use blind index, not encrypted field
- [ ] Tests verify encrypt/decrypt roundtrip
- [ ] Tests verify blind index normalization

---

## Resources

- **Fields**: See `backend/apps/core/encryption/fields.py`
- **Utilities**: See `backend/apps/core/encryption/utils.py`
- **Tests**: See `backend/tests/encryption/`
- **Database Schema**: See `database/SQL/001_schema.sql`
- **Customer Model Example**: See `backend/apps/customers/models.py`
- **Product Model Example**: See `backend/apps/inventario/models.py`

---

*Last updated: 2026-01-20*
*Algorithm: AES-256-GCM | Blind Index: HMAC-SHA256*
