from __future__ import annotations

import argparse
from pathlib import Path

from .crawl import PipelineError, run_batch_pipeline, run_happy_path_pipeline
from .fetch import FetchError, fetch_url_via_tor
from .tor import TorBootstrapError, bootstrap_tor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OnionHarvest CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch", help="Fetch URL content through Tor and print it")
    fetch_parser.add_argument("url", help="Input URL to fetch through Tor")

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

    subparsers.add_parser("test-connection", help="Validate local Tor SOCKS proxy connectivity")

    return parser


def _load_batch_urls(input_path: str | Path) -> list[str]:
    path = Path(input_path)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise PipelineError(f"Invalid input: unable to read URL list file '{path}'.") from exc

    urls = [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]
    if not urls:
        raise PipelineError(f"Invalid input: URL list file '{path}' did not contain any URLs.")
    return urls


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
            html = fetch_url_via_tor(args.url)
            print(html)
            return 0

        if args.command == "run":
            artifact = run_happy_path_pipeline(args.url, args.out, args.output_format)
            print(f"Pipeline complete. Artifact written to: {artifact}")
            return 0

        if args.command == "run-batch":
            urls = _load_batch_urls(args.input)
            artifact = run_batch_pipeline(urls, args.out)
            print(f"Batch pipeline complete. Processed {len(urls)} URL(s). Artifact written to: {artifact}")
            return 0

    except (PipelineError, RuntimeError, FetchError, TorBootstrapError) as exc:
        print(f"ERROR: {exc}")
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
