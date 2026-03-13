"""Facturacion app configuration."""

from datetime import timedelta

from django.apps import AppConfig
from django.core.checks import Warning, register


class FacturacionConfig(AppConfig):
    """Configuration for Facturacion (electronic invoicing) app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.facturacion"
    label = "gravitea_facturacion"
    verbose_name = "Electronic Invoicing"

    def ready(self) -> None:
        register(check_certificate_expiration, "arca")


def check_certificate_expiration(app_configs, **kwargs):
    """
    Django system check: warn if any ARCA certificate expires within 30 days.

    Check ID: arca.W001
    """
    warnings = []

    try:
        from django.utils import timezone

        from apps.facturacion.models import ARCACredential

        threshold = timezone.now() + timedelta(days=30)

        expiring = ARCACredential.all_objects.filter(
            is_active=True,
            certificate_expires_at__isnull=False,
            certificate_expires_at__lte=threshold,
        ).select_related("tenant")

        for cred in expiring:
            days_left = (cred.certificate_expires_at - timezone.now()).days
            warnings.append(
                Warning(
                    f"ARCA certificate for tenant '{cred.tenant.name}' "
                    f"({'production' if cred.is_production else 'homologacion'}) "
                    f"expires in {days_left} days.",
                    hint="Rotate the certificate before expiration to avoid auth failures.",
                    id="arca.W001",
                )
            )
    except Exception:
        # Don't fail system checks if DB is unavailable (e.g., during migrations)
        pass

    return warnings
