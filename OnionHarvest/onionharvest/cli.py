from __future__ import annotations

import argparse

from .crawl import PipelineError, run_happy_path_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OnionHarvest happy-path pipeline")
    parser.add_argument("url", help="Input URL to fetch through Tor")
    parser.add_argument(
        "--out",
        default="artifacts/harvest.json",
        help="Output artifact path (default: artifacts/harvest.json)",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=["json", "sqlite"],
        default="json",
        help="Output artifact format",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        artifact = run_happy_path_pipeline(args.url, args.out, args.output_format)
    except (PipelineError, RuntimeError) as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f"Pipeline complete. Artifact written to: {artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
