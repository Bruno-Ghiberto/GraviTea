"""
ARCA client facade for electronic invoicing.

Provides the ARCAClient class which orchestrates credential loading,
WSAA authentication with Redis caching, and returns an authenticated
context ready for WSFEv1 or CAEA web service calls.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from apps.facturacion.models import ARCACredential

from .exceptions import ARCAAuthError
from .wsaa import WSAAClient

logger = logging.getLogger("facturacion.arca")


@dataclass(frozen=True)
class ARCAAuthContext:
    """
    Authenticated context for ARCA web service calls.

    Attributes:
        token: WSAA authentication token.
        sign: WSAA authentication signature.
        cuit: Effective CUIT for the invoicing operation
            (cuit_represented if delegation, else cuit_holder).
        is_production: Whether to use production endpoints.
    """

    token: str
    sign: str
    cuit: str
    is_production: bool


class ARCAClient:
    """
    High-level facade for ARCA web service authentication.

    Loads the tenant's ARCACredential, authenticates via WSAA
    (with Redis caching), and returns an ARCAAuthContext.

    Usage::

        client = ARCAClient()
        ctx = client.get_auth_context(tenant, is_production=False)
        # ctx.token, ctx.sign, ctx.cuit, ctx.is_production
    """

    def __init__(self) -> None:
        self._wsaa = WSAAClient()

    def get_auth_context(
        self,
        tenant_id: str,
        *,
        is_production: bool = False,
        service: str = "wsfe",
    ) -> ARCAAuthContext:
        """
        Obtain an authenticated ARCA context for a tenant.

        Loads the active credential for the tenant+environment pair,
        authenticates via WSAA (using cached token if available),
        and returns the context needed for WSFEv1/CAEA calls.

        Args:
            tenant_id: UUID of the tenant.
            is_production: True for production, False for homologacion.
            service: Target ARCA web service (default: 'wsfe').

        Returns:
            ARCAAuthContext with token, sign, cuit, and env flag.

        Raises:
            ARCAAuthError: If no active credential exists or
                WSAA authentication fails.
        """
        credential = self._load_credential(tenant_id, is_production)

        # Effective CUIT: represented company (delegation) or holder.
        cuit = credential.cuit_represented or credential.cuit_holder

        token, sign = self._wsaa.get_or_refresh(
            cuit=cuit,
            private_key_pem=credential.private_key_pem.encode("utf-8"),
            cert_pem=credential.certificate_pem.encode("utf-8"),
            service=service,
            is_production=is_production,
        )

        return ARCAAuthContext(
            token=token,
            sign=sign,
            cuit=cuit,
            is_production=is_production,
        )

    @staticmethod
    def _load_credential(
        tenant_id: str, is_production: bool
    ) -> ARCACredential:
        """
        Load the active ARCACredential for a tenant and environment.

        Raises:
            ARCAAuthError: If no active credential is found.
        """
        env_label = "production" if is_production else "homologacion"
        try:
            return ARCACredential.all_objects.get(
                tenant_id=tenant_id,
                is_production=is_production,
                is_active=True,
            )
        except ARCACredential.DoesNotExist:
            raise ARCAAuthError(
                message=(
                    f"No active ARCA credential for {env_label} environment. "
                    "Upload a certificate and private key first."
                ),
                code="ARCA_NO_CREDENTIAL",
            )

    def invalidate_cache(
        self, cuit: str, service: str = "wsfe", *, is_production: bool = False
    ) -> None:
        """Force re-authentication for a tenant CUIT on next call."""
        self._wsaa.invalidate(cuit, service, is_production=is_production)
