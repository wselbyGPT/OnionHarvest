from __future__ import annotations

import socket


class TorBootstrapError(RuntimeError):
    """Raised when a local Tor proxy cannot be reached."""


def bootstrap_tor(proxy_host: str = "127.0.0.1", proxy_port: int = 9050, timeout: float = 4.0) -> str:
    """Verify Tor SOCKS proxy is reachable.

    This is intentionally minimal for package v0.0.0: we only ensure the local
    Tor endpoint is accepting TCP connections.
    """
    try:
        with socket.create_connection((proxy_host, proxy_port), timeout=timeout):
            return f"tor://{proxy_host}:{proxy_port}"
    except OSError as exc:
        raise TorBootstrapError(
            f"Tor bootstrap failed: unable to connect to SOCKS proxy at {proxy_host}:{proxy_port}. "
            "Start Tor locally (for example, `tor` service) and retry."
        ) from exc
