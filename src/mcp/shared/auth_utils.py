"""Utilities for OAuth 2.0 Resource Indicators (RFC 8707) and PKCE (RFC 7636)."""

import math
import posixpath
import time
from urllib.parse import unquote, urlparse, urlsplit, urlunsplit

from pydantic import AnyUrl, HttpUrl


def _normalize_resource_path(path: str) -> str | None:
    """Normalize a URL path and ensure dot-segments cannot traverse out."""
    decoded = path
    for _ in range(5):
        next_decoded = unquote(decoded)
        if next_decoded == decoded:
            break
        decoded = next_decoded
    if "\\" in decoded or "\x00" in decoded:
        return None
    segments = [seg for seg in decoded.split("/") if seg]
    if any(seg in (".", "..") for seg in segments):
        # Resolve cleanly with posixpath, collapsing leading slashes
        resolved = posixpath.normpath("/" + "/".join(segments))
        if not resolved.startswith("/"):
            resolved = "/" + resolved
    else:
        resolved = "/" + "/".join(segments) if segments else "/"
    if resolved != "/" and not resolved.endswith("/"):
        resolved += "/"
    return resolved


def resource_url_from_server_url(url: str | HttpUrl | AnyUrl) -> str:
    """Convert server URL to canonical resource URL per RFC 8707.

    RFC 8707 section 2 states that resource URIs "MUST NOT include a fragment component".
    Returns absolute URI with lowercase scheme/host for canonical form.

    Args:
        url: Server URL to convert

    Returns:
        Canonical resource URL string
    """
    # Convert to string if needed
    url_str = str(url)

    # Parse the URL and remove fragment, create canonical form
    parsed = urlsplit(url_str)
    canonical = urlunsplit(parsed._replace(scheme=parsed.scheme.lower(), netloc=parsed.netloc.lower(), fragment=""))

    return canonical


def check_resource_allowed(requested_resource: str, configured_resource: str) -> bool:
    """Check if a requested resource URL matches a configured resource URL.

    A requested resource matches if it has the same scheme, domain, port,
    and its path starts with the configured resource's path. This allows
    hierarchical matching where a token for a parent resource can be used
    for child resources.

    Args:
        requested_resource: The resource URL being requested
        configured_resource: The resource URL that has been configured

    Returns:
        True if the requested resource matches the configured resource
    """
    # Parse both URLs
    requested = urlparse(requested_resource)
    configured = urlparse(configured_resource)

    # Require absolute scheme and authority, and reject URL fragments per RFC 8707
    if not requested.scheme or not requested.netloc or not configured.scheme or not configured.netloc:
        return False
    if requested.fragment or configured.fragment:
        return False

    # Compare scheme, host, and port (origin)
    if requested.scheme.lower() != configured.scheme.lower() or requested.netloc.lower() != configured.netloc.lower():
        return False

    # Normalize trailing slashes and dot-segments before comparison so that
    # "/foo" and "/foo/" match while "/api/../admin" cannot escape "/api/".
    requested_path = _normalize_resource_path(requested.path)
    configured_path = _normalize_resource_path(configured.path)
    if requested_path is None or configured_path is None:
        return False

    # Check hierarchical match: requested must start with configured path.
    # The trailing-slash normalization ensures "/api123/" won't match "/api/".
    return requested_path.startswith(configured_path)


def calculate_token_expiry(expires_in: int | str | None) -> float | None:
    """Calculate token expiry timestamp from expires_in seconds.

    Args:
        expires_in: Seconds until token expiration (may be string from some servers)

    Returns:
        Unix timestamp when token expires, or None if no expiry specified
    """
    if expires_in is None:
        return None  # pragma: no cover
    if isinstance(expires_in, bool):
        raise ValueError("expires_in must be an integer or numeric string, not bool")
    if isinstance(expires_in, float) and not math.isfinite(expires_in):
        raise ValueError("expires_in must be finite")
    # Defensive: handle servers that return expires_in as string
    seconds = int(expires_in)
    if seconds < 0:
        raise ValueError("expires_in must be non-negative")
    return time.time() + seconds
