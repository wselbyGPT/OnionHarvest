# OnionHarvest

Minimal "happy path" pipeline for v0.0.0:

1. Bootstrap local Tor SOCKS endpoint (`127.0.0.1:9050`)
2. Fetch one URL over Tor
3. Extract structured fields from HTML (`title`, `description`, `links_count`, `text_preview`)
4. Store one local artifact as JSON (default) or SQLite

## CLI

```bash
cd /workspace/OnionHarvest/OnionHarvest
python -m onionharvest.cli test-connection
python -m onionharvest.cli fetch "http://example.onion"
python -m onionharvest.cli run "http://example.onion" --out artifacts/harvest.json --format json
```

If Tor is unavailable, the command returns a clear error message.

## Test

```bash
cd /workspace/OnionHarvest/OnionHarvest
pytest -q
```
