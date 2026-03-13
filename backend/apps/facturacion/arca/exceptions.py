"""
ARCA exception hierarchy for electronic invoicing.

Provides structured exceptions for WSAA authentication errors,
ARCA request failures, and comprobante rejection handling.
"""

from __future__ import annotations


class ARCAError(Exception):
    """Base exception for all ARCA-related errors."""

    def __init__(self, message: str, code: str | None = None) -> None:
        self.message = message
        self.code = code
        super().__init__(message)

    def __str__(self) -> str:
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message


class ARCAAuthError(ARCAError):
    """
    WSAA authentication failure.

    Raised when TRA generation, CMS signing, or LoginCms fails.
    Examples: expired certificate, invalid private key, WSAA service down.
    """

    pass


class ARCARequestError(ARCAError):
    """
    ARCA SOAP request failure.

    Raised for network errors, WSDL issues, or unexpected SOAP faults
    that are NOT comprobante-specific rejections.
    """

    pass


class ARCAComprobanteRejected(ARCAError):
    """
    Comprobante rejected by ARCA.

    Contains structured observation/error data from ARCA response.

    Attributes:
        code: ARCA error code (e.g., '10016', '10048').
        message: Human-readable error description.
        observations: List of ARCA observation dicts from the response.
    """

    def __init__(
        self,
        message: str,
        code: str | None = None,
        observations: list[dict] | None = None,
    ) -> None:
        super().__init__(message=message, code=code)
        self.observations = observations or []

    def __str__(self) -> str:
        base = super().__str__()
        if self.observations:
            obs_str = "; ".join(
                f"[{o.get('Code', '?')}] {o.get('Msg', '')}"
                for o in self.observations
            )
            return f"{base} | Observations: {obs_str}"
        return base
