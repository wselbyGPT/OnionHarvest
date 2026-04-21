from onionharvest import cli


def test_main_test_connection_success(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "bootstrap_tor", lambda: "tor://127.0.0.1:9050")
    monkeypatch.setattr("sys.argv", ["onionharvest", "test-connection"])

    code = cli.main()

    out = capsys.readouterr().out
    assert code == 0
    assert "Connection OK" in out


def test_main_fetch_success(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "bootstrap_tor", lambda: "tor://127.0.0.1:9050")
    monkeypatch.setattr(cli, "fetch_url_via_tor", lambda _url: "<html>ok</html>")
    monkeypatch.setattr("sys.argv", ["onionharvest", "fetch", "http://example.onion"])

    code = cli.main()

    out = capsys.readouterr().out
    assert code == 0
    assert "<html>ok</html>" in out


def test_main_run_success(monkeypatch, tmp_path, capsys) -> None:
    out_file = tmp_path / "artifact.json"
    monkeypatch.setattr(cli, "run_happy_path_pipeline", lambda _url, _out, _fmt: out_file)
    monkeypatch.setattr(
        "sys.argv",
        ["onionharvest", "run", "http://example.onion", "--out", str(out_file), "--format", "json"],
    )

    code = cli.main()

    out = capsys.readouterr().out
    assert code == 0
    assert str(out_file) in out
