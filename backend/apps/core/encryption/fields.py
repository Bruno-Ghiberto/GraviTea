"""
Encrypted Django model fields for PII protection.

Implements AES-256-GCM encryption with HMAC-SHA256 blind indexing
for searchable encrypted fields per research.md.
"""

from django.db import models

from .utils import compute_blind_index, decrypt_value, encrypt_value


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


class EncryptedTextField(models.TextField):
    """
    AES-256-GCM encrypted TextField for larger PII content.

    Similar to EncryptedCharField but for larger text blocks
    like addresses, contact information, etc.

    Usage:
        address_encrypted = EncryptedTextField()
    """

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
        if isinstance(value, str) and len(value) > 50:
            try:
                return decrypt_value(value)
            except ValueError:
                pass
        return value


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
