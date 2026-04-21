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
