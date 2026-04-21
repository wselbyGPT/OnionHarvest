from __future__ import annotations

from pathlib import Path
from typing import Literal

from .extract import extract_structured_fields
from .fetch import fetch_url_via_tor
from .store import store_json_record, store_sqlite_record
from .tor import bootstrap_tor


class PipelineError(RuntimeError):
    """Raised when the happy-path crawl pipeline fails."""


def run_happy_path_pipeline(
    url: str,
    output_path: str | Path = "artifacts/harvest.json",
    output_format: Literal["json", "sqlite"] = "json",
) -> Path:
    if not url.strip():
        raise PipelineError("Invalid input: URL cannot be empty.")

    tor_endpoint = bootstrap_tor()
    html = fetch_url_via_tor(url)
    fields = extract_structured_fields(html)
    record = {"url": url, "fetched_via": tor_endpoint, **fields}

    if output_format == "json":
        return store_json_record(record, output_path)
    if output_format == "sqlite":
        return store_sqlite_record(record, output_path)

    raise PipelineError(f"Invalid output format: '{output_format}'. Use 'json' or 'sqlite'.")
