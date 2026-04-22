from __future__ import annotations

import json
import sqlite3

from onionharvest import crawl
from onionharvest.extract import extract_structured_fields


def test_extract_structured_fields_basic_html() -> None:
    html = """
    <html>
      <head>
        <title>Example Onion Page</title>
        <meta name="description" content="A test onion service page." />
      </head>
      <body>
        <a href="/a">A</a>
        <a href="/b">B</a>
        <p>Hello from onionharvest.</p>
      </body>
    </html>
    """

    result = extract_structured_fields(html)

    assert result["title"] == "Example Onion Page"
    assert result["description"] == "A test onion service page."
    assert result["links_count"] == 2
    assert "Hello from onionharvest." in (result["text_preview"] or "")


def test_extract_structured_fields_prefers_first_meta_description() -> None:
    html = """
    <html>
      <head>
        <meta name="description" content="first description" />
        <meta name="description" content="second description" />
        <title>  Onion   Site  </title>
      </head>
      <body>
        <a href="/1">one</a>
      </body>
    </html>
    """

    result = extract_structured_fields(html)

    assert result == {
        "title": "Onion   Site",
        "description": "first description",
        "links_count": 1,
        "text_preview": "Onion   Site one",
    }


def test_extract_structured_fields_handles_empty_and_entities() -> None:
    html = """
    <html>
      <head><title>AT&amp;T Onion</title></head>
      <body>
        <p>   </p>
        <p>Tom &amp; Jerry</p>
      </body>
    </html>
    """

    result = extract_structured_fields(html)

    assert result["description"] is None
    assert result["links_count"] == 0
    assert result["title"] == "AT&T Onion"
    assert result["text_preview"] == "AT&T Onion Tom & Jerry"


def test_extract_structured_fields_preview_capped_at_280_chars() -> None:
    long_text = "x" * 400
    html = f"<html><body><p>{long_text}</p></body></html>"

    result = extract_structured_fields(html)

    assert result["text_preview"] == long_text[:280]
    assert len(result["text_preview"]) == 280


def test_run_happy_path_pipeline_json(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(crawl, "bootstrap_tor", lambda: "tor://127.0.0.1:9050")
    monkeypatch.setattr(
        crawl,
        "fetch_url_via_tor",
        lambda _url: "<html><head><title>T</title></head><body><a href='/'>x</a></body></html>",
    )

    out = tmp_path / "artifact.json"
    written = crawl.run_happy_path_pipeline("http://example.onion", out, "json")

    assert written == out
    assert out.exists()
    payload = out.read_text(encoding="utf-8")
    assert "example.onion" in payload
    assert '"links_count": 1' in payload


def test_pipeline_integration_calls_tor_and_fetch_boundaries(monkeypatch, tmp_path) -> None:
    call_log: list[tuple[str, str | None]] = []

    def fake_bootstrap_tor() -> str:
        call_log.append(("bootstrap_tor", None))
        return "tor://127.0.0.1:9050"

    def fake_fetch_url_via_tor(url: str) -> str:
        call_log.append(("fetch_url_via_tor", url))
        return (
            "<html><head><title>Hidden Service</title>"
            "<meta name='description' content='mocked boundary'>"
            "</head><body><a href='/x'>x</a><p>hello integration</p></body></html>"
        )

    monkeypatch.setattr(crawl, "bootstrap_tor", fake_bootstrap_tor)
    monkeypatch.setattr(crawl, "fetch_url_via_tor", fake_fetch_url_via_tor)

    out = tmp_path / "integration.json"
    written = crawl.run_happy_path_pipeline("http://example.onion", out, "json")

    assert written == out
    assert call_log == [
        ("bootstrap_tor", None),
        ("fetch_url_via_tor", "http://example.onion"),
    ]

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload == {
        "url": "http://example.onion",
        "fetched_via": "tor://127.0.0.1:9050",
        "title": "Hidden Service",
        "description": "mocked boundary",
        "links_count": 1,
        "text_preview": "Hidden Service x hello integration",
    }


def test_run_batch_pipeline_writes_each_url_as_sqlite_row(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(crawl, "bootstrap_tor", lambda: "tor://127.0.0.1:9050")
    monkeypatch.setattr(
        crawl,
        "fetch_url_via_tor",
        lambda url: (
            f"<html><head><title>{url}</title></head>"
            "<body><a href='/a'>a</a><a href='/b'>b</a></body></html>"
        ),
    )

    out = tmp_path / "artifact.db"
    written = crawl.run_batch_pipeline(["http://a.onion", "http://b.onion"], out)

    assert written == out
    with sqlite3.connect(out) as conn:
        rows = conn.execute(
            "SELECT url, fetched_via, links_count FROM harvest_records ORDER BY id"
        ).fetchall()
        statuses = conn.execute(
            "SELECT url, status FROM harvest_url_status ORDER BY url"
        ).fetchall()

    assert rows == [
        ("http://a.onion", "tor://127.0.0.1:9050", 2),
        ("http://b.onion", "tor://127.0.0.1:9050", 2),
    ]
    assert statuses == [
        ("http://a.onion", "success"),
        ("http://b.onion", "success"),
    ]


def test_run_batch_pipeline_resume_skips_success_and_retries_errors(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(crawl, "bootstrap_tor", lambda: "tor://127.0.0.1:9050")
    attempts: dict[str, int] = {"http://a.onion": 0, "http://b.onion": 0}

    def fake_fetch(url: str) -> str:
        attempts[url] += 1
        if url == "http://b.onion" and attempts[url] == 1:
            raise RuntimeError("transient failure")
        return (
            f"<html><head><title>{url}</title></head>"
            "<body><a href='/a'>a</a></body></html>"
        )

    monkeypatch.setattr(crawl, "fetch_url_via_tor", fake_fetch)
    out = tmp_path / "artifact.db"

    crawl.run_batch_pipeline(["http://a.onion", "http://b.onion"], out)
    crawl.run_batch_pipeline(["http://a.onion", "http://b.onion"], out)

    assert attempts == {"http://a.onion": 1, "http://b.onion": 2}

    with sqlite3.connect(out) as conn:
        rows = conn.execute(
            "SELECT url FROM harvest_records ORDER BY id"
        ).fetchall()
        statuses = conn.execute(
            "SELECT url, status FROM harvest_url_status ORDER BY url"
        ).fetchall()

    assert rows == [("http://a.onion",), ("http://b.onion",)]
    assert statuses == [
        ("http://a.onion", "success"),
        ("http://b.onion", "success"),
    ]
