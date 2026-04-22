from __future__ import annotations

import random
import subprocess
import time


class FetchError(RuntimeError):
    """Raised when fetching through Tor fails."""


_TRANSIENT_CURL_EXIT_CODES = {5, 6, 7, 28, 35, 52, 56}
_TRANSIENT_ERROR_KEYWORDS = (
    "timed out",
    "timeout",
    "connection reset",
    "connection refused",
    "temporar",
    "try again",
    "network is unreachable",
    "proxy connect aborted",
)
_PERMANENT_ERROR_KEYWORDS = (
    "malformed",
    "bad/illegal format",
    "unsupported protocol",
    "could not resolve proxy",
    "not a valid",
)


def _is_transient_curl_error(returncode: int, stderr: str) -> bool:
    normalized_stderr = stderr.lower()
    if returncode in _TRANSIENT_CURL_EXIT_CODES:
        if any(keyword in normalized_stderr for keyword in _PERMANENT_ERROR_KEYWORDS):
            return False
        return True
    return any(keyword in normalized_stderr for keyword in _TRANSIENT_ERROR_KEYWORDS)


def fetch_url_via_tor(
    url: str,
    proxy_host: str = "127.0.0.1",
    proxy_port: int = 9050,
    timeout_sec: int = 20,
    max_retries: int = 2,
    retry_backoff_base_sec: float = 0.25,
    retry_backoff_max_sec: float = 2.0,
    retry_jitter_sec: float = 0.1,
) -> str:
    """Fetch URL content over Tor using curl + SOCKS5 hostname proxy."""
    if max_retries < 0:
        raise FetchError("Invalid retry setting: max_retries must be >= 0.")

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

    attempts = max_retries + 1
    last_error_context: str | None = None

    for attempt in range(1, attempts + 1):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        except FileNotFoundError as exc:
            raise FetchError("Fetch failed: `curl` is not installed in this environment.") from exc

        if result.returncode == 0:
            if not result.stdout:
                raise FetchError(f"Fetch failed for URL '{url}': empty response body.")
            return result.stdout

        stderr = (result.stderr or "unknown error").strip()
        last_error_context = f"curl exit {result.returncode}: {stderr}"
        if not _is_transient_curl_error(result.returncode, stderr):
            raise FetchError(f"Fetch failed for URL '{url}' (non-retriable): {last_error_context}")

        if attempt == attempts:
            break

        backoff = min(retry_backoff_max_sec, retry_backoff_base_sec * (2 ** (attempt - 1)))
        jitter = random.uniform(0.0, max(retry_jitter_sec, 0.0))
        time.sleep(max(0.0, backoff + jitter))

    raise FetchError(
        f"Fetch failed for URL '{url}' after {attempts} attempt(s). Last error: {last_error_context}"
    )
