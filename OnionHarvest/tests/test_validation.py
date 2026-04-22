from __future__ import annotations

import pytest

from onionharvest import crawl
from onionharvest.validation import URLValidationError, validate_url


@pytest.mark.parametrize(
    "url, expected_message",
    [
        ("", "cannot be empty"),
        ("example.onion", "unsupported scheme"),
        ("ftp://example.onion", "unsupported scheme"),
        ("http:///path-only", "host is missing"),
        ("http://bad host.onion", "not syntactically valid"),
        ("http://example.com", "not a .onion domain"),
    ],
)
def test_validate_url_rejects_malformed_and_unsupported_inputs(url: str, expected_message: str) -> None:
    with pytest.raises(URLValidationError, match=expected_message):
        validate_url(url)


def test_validate_url_accepts_valid_onion_url() -> None:
    assert validate_url("  http://exampleonion123.onion/path?q=1  ") == "http://exampleonion123.onion/path?q=1"


def test_validate_url_optionally_allows_https() -> None:
    assert (
        validate_url("https://secureexample.onion", allow_https=True)
        == "https://secureexample.onion"
    )


def test_crawl_pipeline_raises_pipeline_error_for_invalid_url() -> None:
    with pytest.raises(crawl.PipelineError, match="not a .onion domain"):
        crawl.run_happy_path_pipeline("http://example.com")
