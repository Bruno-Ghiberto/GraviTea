"""
Signal handlers for core app.

Invalidates cached TenantFieldDefinition querysets when definitions change.
"""

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.core.models import TenantFieldDefinition


@receiver(post_save, sender=TenantFieldDefinition)
@receiver(post_delete, sender=TenantFieldDefinition)
def invalidate_field_defs_cache(sender, instance, **kwargs):
    cache_key = f"field_defs:{instance.tenant_id}:{instance.entity_type}"
    cache.delete(cache_key)
