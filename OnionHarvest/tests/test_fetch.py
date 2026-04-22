import subprocess

import pytest

from onionharvest.fetch import FetchError, fetch_url_via_tor


def _result(returncode: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["curl"], returncode=returncode, stdout=stdout, stderr=stderr)


def test_fetch_retries_transient_failures(monkeypatch) -> None:
    responses = [
        _result(28, stderr="Operation timed out"),
        _result(56, stderr="Recv failure: Connection reset by peer"),
        _result(0, stdout="<html>ok</html>"),
    ]
    calls: list[int] = []
    sleeps: list[float] = []

    def fake_run(*_args, **_kwargs):
        calls.append(1)
        return responses.pop(0)

    monkeypatch.setattr("onionharvest.fetch.subprocess.run", fake_run)
    monkeypatch.setattr("onionharvest.fetch.random.uniform", lambda _a, _b: 0.0)
    monkeypatch.setattr("onionharvest.fetch.time.sleep", lambda seconds: sleeps.append(seconds))

    html = fetch_url_via_tor("http://example.onion", max_retries=3, retry_backoff_base_sec=0.2)

    assert html == "<html>ok</html>"
    assert len(calls) == 3
    assert sleeps == [0.2, 0.4]


def test_fetch_does_not_retry_permanent_invalid_input(monkeypatch) -> None:
    calls: list[int] = []

    def fake_run(*_args, **_kwargs):
        calls.append(1)
        return _result(3, stderr="URL using bad/illegal format or missing URL")

    monkeypatch.setattr("onionharvest.fetch.subprocess.run", fake_run)
    monkeypatch.setattr("onionharvest.fetch.time.sleep", lambda _seconds: pytest.fail("should not sleep"))

    with pytest.raises(FetchError, match="non-retriable"):
        fetch_url_via_tor("not-a-url", max_retries=4)

    assert len(calls) == 1


def test_fetch_final_exception_keeps_useful_context(monkeypatch) -> None:
    def fake_run(*_args, **_kwargs):
        return _result(28, stderr="Connection timed out while connecting to upstream")

    monkeypatch.setattr("onionharvest.fetch.subprocess.run", fake_run)
    monkeypatch.setattr("onionharvest.fetch.random.uniform", lambda _a, _b: 0.0)
    monkeypatch.setattr("onionharvest.fetch.time.sleep", lambda _seconds: None)

    with pytest.raises(FetchError) as exc:
        fetch_url_via_tor("http://example.onion", max_retries=2, retry_backoff_base_sec=0.01)

    message = str(exc.value)
    assert "after 3 attempt(s)" in message
    assert "curl exit 28" in message
    assert "Connection timed out" in message
