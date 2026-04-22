from __future__ import annotations

import re
from urllib.parse import urlsplit


class URLValidationError(ValueError):
    """Raised when a user-provided URL fails input validation."""


_HOST_LABEL_RE = re.compile(r"^[A-Za-z0-9-]{1,63}$")


def _is_valid_host(host: str) -> bool:
    if not host or len(host) > 253:
        return False

    if host.startswith(".") or host.endswith("."):
        return False

    labels = host.split(".")
    for label in labels:
        if not _HOST_LABEL_RE.fullmatch(label):
            return False
        if label.startswith("-") or label.endswith("-"):
            return False
    return True


def validate_url(url: str, *, allow_https: bool = False, require_onion: bool = True) -> str:
    """Validate URL input and return a normalized stripped URL."""
    normalized = url.strip()
    if not normalized:
        raise URLValidationError("Invalid URL: URL cannot be empty. Provide a URL such as 'http://example.onion'.")

    parsed = urlsplit(normalized)

    allowed_schemes = {"http", "https"} if allow_https else {"http"}
    if parsed.scheme not in allowed_schemes:
        allowed_display = ", ".join(sorted(allowed_schemes))
        raise URLValidationError(
            f"Invalid URL: unsupported scheme '{parsed.scheme or '<missing>'}'. Allowed scheme(s): {allowed_display}."
        )

    host = parsed.hostname
    if not host:
        raise URLValidationError("Invalid URL: host is missing. Include a host like 'example.onion'.")

    if not _is_valid_host(host):
        raise URLValidationError(f"Invalid URL: host '{host}' is not syntactically valid.")

    if require_onion and not host.lower().endswith(".onion"):
        raise URLValidationError(
            f"Invalid URL: host '{host}' is not a .onion domain. Provide a URL ending in '.onion'."
        )

    return normalized
