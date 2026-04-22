from pathlib import Path

from onionharvest import cli
from onionharvest.crawl import BatchPipelineErrorDetail, BatchPipelineResult


def test_main_test_connection_success(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "bootstrap_tor", lambda: "tor://127.0.0.1:9050")
    monkeypatch.setattr("sys.argv", ["onionharvest", "test-connection"])

    code = cli.main()

    out = capsys.readouterr().out
    assert code == 0
    assert "Connection OK" in out


def test_main_fetch_success(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "bootstrap_tor", lambda: "tor://127.0.0.1:9050")
    monkeypatch.setattr(cli, "fetch_url_via_tor", lambda _url, **_kwargs: "<html>ok</html>")
    monkeypatch.setattr("sys.argv", ["onionharvest", "fetch", "http://example.onion"])

    code = cli.main()

    out = capsys.readouterr().out
    assert code == 0
    assert "<html>ok</html>" in out


def test_main_run_success(monkeypatch, tmp_path, capsys) -> None:
    out_file = tmp_path / "artifact.json"
    monkeypatch.setattr(cli, "run_happy_path_pipeline", lambda _url, _out, _fmt, **_kwargs: out_file)
    monkeypatch.setattr(
        "sys.argv",
        ["onionharvest", "run", "http://example.onion", "--out", str(out_file), "--format", "json"],
    )

    code = cli.main()

    out = capsys.readouterr().out
    assert code == 0
    assert str(out_file) in out


def test_main_run_batch_success(monkeypatch, tmp_path, capsys) -> None:
    urls_file = tmp_path / "urls.txt"
    urls_file.write_text(
        "http://a.onion\n\n# comment\nhttp://b.onion\n",
        encoding="utf-8",
    )
    out_file = tmp_path / "harvest.db"

    calls: list[tuple[list[str], str]] = []

    def fake_run_batch(urls: list[str], out: str, **_kwargs):
        calls.append((urls, out))
        return BatchPipelineResult(
            artifact_path=Path(out),
            total_urls=len(urls),
            processed_count=len(urls),
            success_count=len(urls),
            error_count=0,
            failed=(),
        )

    monkeypatch.setattr(cli, "run_batch_pipeline", fake_run_batch)
    monkeypatch.setattr(
        "sys.argv",
        ["onionharvest", "run-batch", "--input", str(urls_file), "--out", str(out_file)],
    )

    code = cli.main()

    out = capsys.readouterr().out
    assert code == 0
    assert "Processed 2/2 URL(s): 2 succeeded, 0 failed." in out
    assert calls == [(["http://a.onion", "http://b.onion"], str(out_file))]


def test_main_run_batch_reports_errors_and_nonzero_exit(monkeypatch, tmp_path, capsys) -> None:
    urls_file = tmp_path / "urls.txt"
    urls_file.write_text("http://a.onion\nhttp://b.onion\n", encoding="utf-8")
    out_file = tmp_path / "harvest.db"

    def fake_run_batch(_urls: list[str], out: str, **_kwargs) -> BatchPipelineResult:
        return BatchPipelineResult(
            artifact_path=Path(out),
            total_urls=2,
            processed_count=2,
            success_count=1,
            error_count=1,
            failed=(BatchPipelineErrorDetail(url="http://b.onion", message="timeout"),),
        )

    monkeypatch.setattr(cli, "run_batch_pipeline", fake_run_batch)
    monkeypatch.setattr(
        "sys.argv",
        ["onionharvest", "run-batch", "--input", str(urls_file), "--out", str(out_file)],
    )

    code = cli.main()

    out = capsys.readouterr().out
    assert code == 1
    assert "Processed 2/2 URL(s): 1 succeeded, 1 failed." in out
    assert "Failed URLs:" in out
    assert "- http://b.onion: timeout" in out


def test_main_run_batch_empty_input_file(monkeypatch, tmp_path, capsys) -> None:
    urls_file = tmp_path / "urls.txt"
    urls_file.write_text("\n# no entries\n", encoding="utf-8")

    monkeypatch.setattr("sys.argv", ["onionharvest", "run-batch", "--input", str(urls_file)])

    code = cli.main()

    out = capsys.readouterr().out
    assert code == 1
    assert "did not contain any URLs" in out


def test_main_run_batch_invalid_url_in_input(monkeypatch, tmp_path, capsys) -> None:
    urls_file = tmp_path / "urls.txt"
    urls_file.write_text("http://good.onion\nhttp://not-onion.example\n", encoding="utf-8")

    monkeypatch.setattr("sys.argv", ["onionharvest", "run-batch", "--input", str(urls_file)])

    code = cli.main()

    out = capsys.readouterr().out
    assert code == 1
    assert "URL on line 2" in out
    assert "not a .onion domain" in out


def test_main_fetch_threads_retry_flags(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "bootstrap_tor", lambda: "tor://127.0.0.1:9050")
    captured: dict[str, object] = {}

    def fake_fetch(_url: str, **kwargs):
        captured.update(kwargs)
        return "<html>ok</html>"

    monkeypatch.setattr(cli, "fetch_url_via_tor", fake_fetch)
    monkeypatch.setattr(
        "sys.argv",
        [
            "onionharvest",
            "fetch",
            "http://example.onion",
            "--fetch-max-retries",
            "5",
            "--fetch-retry-backoff-base-sec",
            "0.5",
            "--fetch-retry-backoff-max-sec",
            "1.5",
            "--fetch-retry-jitter-sec",
            "0.2",
        ],
    )

    code = cli.main()

    assert code == 0
    assert captured == {
        "max_retries": 5,
        "retry_backoff_base_sec": 0.5,
        "retry_backoff_max_sec": 1.5,
        "retry_jitter_sec": 0.2,
    }
    assert "<html>ok</html>" in capsys.readouterr().out
