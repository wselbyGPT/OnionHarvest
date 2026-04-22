from __future__ import annotations

import argparse
from pathlib import Path

from .crawl import PipelineError, run_batch_pipeline, run_happy_path_pipeline
from .fetch import FetchError, fetch_url_via_tor
from .tor import TorBootstrapError, bootstrap_tor
from .validation import URLValidationError, validate_url


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OnionHarvest CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch", help="Fetch URL content through Tor and print it")
    fetch_parser.add_argument("url", help="Input URL to fetch through Tor")
    _add_fetch_retry_arguments(fetch_parser)

    run_parser = subparsers.add_parser("run", help="Run the full happy-path pipeline")
    run_parser.add_argument("url", help="Input URL to fetch through Tor")
    run_parser.add_argument(
        "--out",
        default="artifacts/harvest.json",
        help="Output artifact path (default: artifacts/harvest.json)",
    )
    run_parser.add_argument(
        "--format",
        dest="output_format",
        choices=["json", "sqlite"],
        default="json",
        help="Output artifact format",
    )
    _add_fetch_retry_arguments(run_parser)

    run_batch_parser = subparsers.add_parser(
        "run-batch",
        help="Run the happy-path pipeline for each URL listed in an input file",
    )
    run_batch_parser.add_argument(
        "--input",
        required=True,
        help="Path to a text file containing one URL per line",
    )
    run_batch_parser.add_argument(
        "--out",
        default="artifacts/harvest.db",
        help="Output SQLite artifact path (default: artifacts/harvest.db)",
    )
    _add_fetch_retry_arguments(run_batch_parser)

    subparsers.add_parser("test-connection", help="Validate local Tor SOCKS proxy connectivity")

    return parser


def _add_fetch_retry_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--fetch-max-retries",
        type=int,
        default=2,
        help="Number of retries for transient fetch failures (default: 2).",
    )
    parser.add_argument(
        "--fetch-retry-backoff-base-sec",
        type=float,
        default=0.25,
        help="Base exponential backoff delay in seconds (default: 0.25).",
    )
    parser.add_argument(
        "--fetch-retry-backoff-max-sec",
        type=float,
        default=2.0,
        help="Maximum backoff delay in seconds (default: 2.0).",
    )
    parser.add_argument(
        "--fetch-retry-jitter-sec",
        type=float,
        default=0.1,
        help="Maximum random jitter added to retries in seconds (default: 0.1).",
    )


def _load_batch_urls(input_path: str | Path) -> list[str]:
    path = Path(input_path)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise PipelineError(f"Invalid input: unable to read URL list file '{path}'.") from exc

    indexed_urls = [
        (line_number, line.strip())
        for line_number, line in enumerate(lines, start=1)
        if line.strip() and not line.strip().startswith("#")
    ]
    if not indexed_urls:
        raise PipelineError(f"Invalid input: URL list file '{path}' did not contain any URLs.")

    validated_urls: list[str] = []
    for line_number, candidate in indexed_urls:
        try:
            validated_urls.append(validate_url(candidate))
        except URLValidationError as exc:
            raise PipelineError(
                f"Invalid input: URL on line {line_number} in '{path}' is invalid. {exc}"
            ) from exc

    return validated_urls


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "test-connection":
            endpoint = bootstrap_tor()
            print(f"Connection OK: {endpoint}")
            return 0

        if args.command == "fetch":
            bootstrap_tor()
            url = validate_url(args.url)
            html = fetch_url_via_tor(
                url,
                max_retries=args.fetch_max_retries,
                retry_backoff_base_sec=args.fetch_retry_backoff_base_sec,
                retry_backoff_max_sec=args.fetch_retry_backoff_max_sec,
                retry_jitter_sec=args.fetch_retry_jitter_sec,
            )
            print(html)
            return 0

        if args.command == "run":
            url = validate_url(args.url)
            artifact = run_happy_path_pipeline(
                url,
                args.out,
                args.output_format,
                fetch_max_retries=args.fetch_max_retries,
                fetch_retry_backoff_base_sec=args.fetch_retry_backoff_base_sec,
                fetch_retry_backoff_max_sec=args.fetch_retry_backoff_max_sec,
                fetch_retry_jitter_sec=args.fetch_retry_jitter_sec,
            )
            print(f"Pipeline complete. Artifact written to: {artifact}")
            return 0

        if args.command == "run-batch":
            urls = _load_batch_urls(args.input)
            result = run_batch_pipeline(
                urls,
                args.out,
                fetch_max_retries=args.fetch_max_retries,
                fetch_retry_backoff_base_sec=args.fetch_retry_backoff_base_sec,
                fetch_retry_backoff_max_sec=args.fetch_retry_backoff_max_sec,
                fetch_retry_jitter_sec=args.fetch_retry_jitter_sec,
            )
            print(
                "Batch pipeline complete. "
                f"Processed {result.processed_count}/{result.total_urls} URL(s): "
                f"{result.success_count} succeeded, {result.error_count} failed. "
                f"Artifact written to: {result.artifact_path}"
            )
            if result.failed:
                print("Failed URLs:")
                for error in result.failed:
                    print(f"- {error.url}: {error.message}")
            return 1 if result.error_count else 0

    except (PipelineError, RuntimeError, FetchError, TorBootstrapError, URLValidationError) as exc:
        print(f"ERROR: {exc}")
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
