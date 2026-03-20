"""
URL validator for SSRF prevention.

OWASP A10:2021 - Server-Side Request Forgery (SSRF)

This module provides URL validation functions to prevent SSRF attacks
by blocking requests to internal networks, cloud metadata endpoints,
and dangerous URI schemes.
"""

import ipaddress
import re
import socket
from typing import Optional
from urllib.parse import urlparse


# Allowed schemes - only HTTP and HTTPS
ALLOWED_SCHEMES = {"http", "https"}

# Blocked hostnames (case-insensitive)
BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "metadata.gcp.internal",
}

# Cloud metadata IPs
METADATA_IPS = {
    "169.254.169.254",  # AWS/Azure metadata
    "169.254.170.2",    # AWS ECS task metadata
}

# Private network ranges (RFC 1918 + loopback + link-local)
PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),       # Loopback
    ipaddress.ip_network("169.254.0.0/16"),    # Link-local (includes metadata)
    ipaddress.ip_network("0.0.0.0/8"),         # "This" network
    ipaddress.ip_network("::1/128"),           # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),          # IPv6 unique local
    ipaddress.ip_network("fe80::/10"),         # IPv6 link-local
    ipaddress.ip_network("::ffff:0:0/96"),     # IPv4-mapped IPv6
]


class URLValidator:
    """
    URL validator with SSRF protection.

    Validates URLs to ensure they don't point to internal resources,
    cloud metadata endpoints, or use dangerous URI schemes.
    """

    def __init__(
        self,
        allowed_schemes: Optional[set] = None,
        blocked_hostnames: Optional[set] = None,
        resolve_dns: bool = True,
    ):
        """
        Initialize the URL validator.

        Args:
            allowed_schemes: Set of allowed URI schemes (default: http, https)
            blocked_hostnames: Set of blocked hostnames (case-insensitive)
            resolve_dns: Whether to resolve DNS and validate the IP
        """
        self.allowed_schemes = allowed_schemes or ALLOWED_SCHEMES
        self.blocked_hostnames = blocked_hostnames or BLOCKED_HOSTNAMES
        self.resolve_dns = resolve_dns

    def is_safe(self, url: str) -> bool:
        """
        Check if a URL is safe to request.

        Args:
            url: The URL to validate

        Returns:
            True if the URL is safe, False otherwise
        """
        from apps.core.security.ssrf_engine import is_safe_url as _engine  # noqa: PLC0415
        return _engine(url)


def is_safe_url(url: Optional[str]) -> bool:
    """
    Check if a URL is safe to request (not an SSRF target).

    This function validates URLs against SSRF attack vectors:
    - Blocks non-HTTP(S) schemes
    - Blocks localhost and loopback addresses
    - Blocks private network addresses (RFC 1918)
    - Blocks cloud metadata endpoints
    - Blocks URLs with credentials
    - Handles various bypass attempts (IP encoding, etc.)

    Args:
        url: The URL to validate

    Returns:
        True if the URL is safe to request, False otherwise
    """
    if not url or not isinstance(url, str):
        return False

    url = url.strip()
    if not url:
        return False

    # Parse the URL
    try:
        parsed = urlparse(url)
    except Exception:
        return False

    # Check scheme
    scheme = (parsed.scheme or "").lower()
    if scheme not in ALLOWED_SCHEMES:
        return False

    # Block URLs with credentials
    if parsed.username or parsed.password:
        return False

    # Get hostname
    hostname = parsed.hostname
    if not hostname:
        return False

    hostname_lower = hostname.lower()

    # Check blocked hostnames
    if hostname_lower in BLOCKED_HOSTNAMES:
        return False

    # Try to parse as IP address
    ip = _parse_ip(hostname)
    if ip is not None:
        if _is_private_ip(ip):
            return False
        if str(ip) in METADATA_IPS:
            return False
    else:
        # It's a hostname - check for suspicious patterns
        if _is_suspicious_hostname(hostname_lower):
            return False

        # Optionally resolve DNS to check the actual IP
        resolved_ip = _resolve_hostname(hostname)
        if resolved_ip is not None:
            if _is_private_ip(resolved_ip):
                return False
            if str(resolved_ip) in METADATA_IPS:
                return False

    return True


def _parse_ip(hostname: str) -> Optional[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    """
    Parse hostname as an IP address, handling various encodings.

    Handles:
    - Standard IP addresses (127.0.0.1, ::1)
    - IPv6 in brackets ([::1])
    - Decimal IP (2130706433 = 127.0.0.1)
    - Hexadecimal IP (0x7f000001 = 127.0.0.1)
    - Octal IP (0177.0.0.1 = 127.0.0.1)
    - Shortened IP (127.1 = 127.0.0.1)

    Args:
        hostname: The hostname to parse

    Returns:
        IP address object if valid, None otherwise
    """
    # Remove IPv6 brackets
    if hostname.startswith("[") and hostname.endswith("]"):
        hostname = hostname[1:-1]

    # Try standard IP parsing first
    try:
        return ipaddress.ip_address(hostname)
    except ValueError:
        pass

    # Try decimal IP (e.g., 2130706433)
    try:
        if hostname.isdigit():
            decimal_ip = int(hostname)
            if 0 <= decimal_ip <= 0xFFFFFFFF:
                return ipaddress.ip_address(decimal_ip)
    except (ValueError, OverflowError):
        pass

    # Try hexadecimal IP (e.g., 0x7f000001)
    try:
        if hostname.lower().startswith("0x"):
            hex_ip = int(hostname, 16)
            if 0 <= hex_ip <= 0xFFFFFFFF:
                return ipaddress.ip_address(hex_ip)
    except (ValueError, OverflowError):
        pass

    # Try octal IP (e.g., 0177.0.0.1)
    if "." in hostname:
        parts = hostname.split(".")
        if len(parts) <= 4:
            try:
                octal_parts = []
                for part in parts:
                    if part.startswith("0") and len(part) > 1 and part.isdigit():
                        # Octal
                        octal_parts.append(int(part, 8))
                    else:
                        octal_parts.append(int(part))
                # Pad to 4 parts
                while len(octal_parts) < 4:
                    octal_parts.append(0)
                if all(0 <= p <= 255 for p in octal_parts):
                    return ipaddress.ip_address(".".join(str(p) for p in octal_parts))
            except (ValueError, OverflowError):
                pass

    # Try shortened IP (e.g., 127.1 = 127.0.0.1)
    if "." in hostname and hostname.replace(".", "").isdigit():
        parts = hostname.split(".")
        if 1 < len(parts) < 4:
            try:
                # Expand shortened IP
                if len(parts) == 2:
                    # a.b = a.0.0.b
                    expanded = f"{parts[0]}.0.0.{parts[1]}"
                elif len(parts) == 3:
                    # a.b.c = a.b.0.c
                    expanded = f"{parts[0]}.{parts[1]}.0.{parts[2]}"
                else:
                    expanded = hostname
                return ipaddress.ip_address(expanded)
            except ValueError:
                pass

    return None


def _is_private_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """
    Check if an IP address is in a private/internal range.

    Args:
        ip: The IP address to check

    Returns:
        True if the IP is private/internal, False otherwise
    """
    for network in PRIVATE_NETWORKS:
        try:
            if ip in network:
                return True
        except TypeError:
            # IPv4/IPv6 mismatch
            continue
    return False


def _is_suspicious_hostname(hostname: str) -> bool:
    """
    Check if a hostname appears to be attempting SSRF bypass.

    Args:
        hostname: The hostname to check (lowercase)

    Returns:
        True if suspicious, False otherwise
    """
    # Check for localhost variations
    if "localhost" in hostname:
        return True

    # Check for IP-based wildcard DNS services
    suspicious_patterns = [
        r"\.nip\.io$",
        r"\.xip\.io$",
        r"\.sslip\.io$",
        r"localtest\.me$",
        r"127\.0\.0\.1",
        r"169\.254\.",
        r"192\.168\.",
        r"10\.\d+\.",
        r"172\.(1[6-9]|2\d|3[01])\.",
    ]

    for pattern in suspicious_patterns:
        if re.search(pattern, hostname):
            return True

    # Check for null bytes or encoded characters
    if "\x00" in hostname or "%00" in hostname:
        return True

    # Check for IPv6 private address prefixes that might be URL-mangled
    # When IPv6 addresses aren't properly bracketed in URLs, urlparse
    # may truncate them. Check if the hostname looks like a private
    # IPv6 prefix (fd00, fc00, fe80, etc.)
    ipv6_private_prefixes = ["fd", "fc", "fe80"]
    if any(hostname.startswith(prefix) for prefix in ipv6_private_prefixes):
        # If it looks like it could be an IPv6 prefix followed by hex chars
        remaining = hostname[4:] if hostname.startswith("fe80") else hostname[2:]
        if not remaining or remaining.isalnum():
            return True

    return False


def _resolve_hostname(hostname: str) -> Optional[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    """
    Resolve hostname to IP address for validation.

    Args:
        hostname: The hostname to resolve

    Returns:
        IP address if resolved, None otherwise
    """
    try:
        # Get all addresses
        infos = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        if infos:
            # Return the first resolved IP
            addr = infos[0][4][0]
            return ipaddress.ip_address(addr)
    except (socket.gaierror, socket.herror, ValueError, OSError):
        pass
    return None
