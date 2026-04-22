from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .extract import extract_structured_fields
from .fetch import fetch_url_via_tor
from .store import (
    get_urls_requiring_processing,
    initialize_batch_status,
    store_json_record,
    store_sqlite_record,
    update_url_status,
)
from .tor import bootstrap_tor


class PipelineError(RuntimeError):
    """Raised when the happy-path crawl pipeline fails."""


@dataclass(frozen=True)
class BatchPipelineErrorDetail:
    url: str
    message: str


@dataclass(frozen=True)
class BatchPipelineResult:
    artifact_path: Path
    total_urls: int
    processed_count: int
    success_count: int
    error_count: int
    failed: tuple[BatchPipelineErrorDetail, ...]


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


def run_batch_pipeline(
    urls: list[str],
    output_path: str | Path = "artifacts/harvest.db",
) -> BatchPipelineResult:
    if not urls:
        raise PipelineError("Invalid input: URL list cannot be empty.")

    tor_endpoint = bootstrap_tor()
    final_path = initialize_batch_status(urls, output_path)
    urls_to_process = get_urls_requiring_processing(urls, output_path)
    success_count = 0
    failed: list[BatchPipelineErrorDetail] = []

    for url in urls_to_process:
        if not url.strip():
            raise PipelineError("Invalid input: URL cannot be empty.")

        update_url_status(url, "pending", output_path)
        try:
            html = fetch_url_via_tor(url)
            fields = extract_structured_fields(html)
            record = {"url": url, "fetched_via": tor_endpoint, **fields}
            final_path = store_sqlite_record(record, output_path)
            update_url_status(url, "success", output_path)
            success_count += 1
        except Exception as exc:
            message = str(exc)
            update_url_status(url, "error", output_path, message)
            failed.append(BatchPipelineErrorDetail(url=url, message=message))

    return BatchPipelineResult(
        artifact_path=final_path,
        total_urls=len(urls),
        processed_count=len(urls_to_process),
        success_count=success_count,
        error_count=len(failed),
        failed=tuple(failed),
    )
