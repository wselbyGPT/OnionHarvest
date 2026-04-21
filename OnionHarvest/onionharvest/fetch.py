from __future__ import annotations

import subprocess


class FetchError(RuntimeError):
    """Raised when fetching through Tor fails."""


def fetch_url_via_tor(url: str, proxy_host: str = "127.0.0.1", proxy_port: int = 9050, timeout_sec: int = 20) -> str:
    """Fetch URL content over Tor using curl + SOCKS5 hostname proxy."""
    cmd = [
        "curl",
        "--silent",
        "--show-error",
        "--location",
        "--max-time",
        str(timeout_sec),
        "--socks5-hostname",
        f"{proxy_host}:{proxy_port}",
        url,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        raise FetchError("Fetch failed: `curl` is not installed in this environment.") from exc

    if result.returncode != 0:
        stderr = (result.stderr or "unknown error").strip()
        raise FetchError(f"Fetch failed for URL '{url}': {stderr}")

    if not result.stdout:
        raise FetchError(f"Fetch failed for URL '{url}': empty response body.")

    return result.stdout
