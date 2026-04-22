# OnionHarvest

OnionHarvest is a minimal, explicit "happy-path" pipeline for fetching one URL via Tor, extracting a few structured fields, and storing the result as JSON (default) or SQLite.

## Quickstart

### 1) Requirements
- Python 3.11+
- A local Tor SOCKS endpoint available at `127.0.0.1:9050`
- `curl` installed (used by the fetch step)

### 2) Setup
```bash
cd /workspace/OnionHarvest/OnionHarvest
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 3) Verify Tor connectivity
```bash
onionharvest test-connection
```
Expected success message:
```text
Connection OK: tor://127.0.0.1:9050
```

### 4) Run the pipeline
```bash
onionharvest run "http://example.onion" --out artifacts/harvest.json --format json
```
Expected success message:
```text
Pipeline complete. Artifact written to: artifacts/harvest.json
```

### 5) Optional commands
Fetch raw HTML via Tor:
```bash
onionharvest fetch "http://example.onion"
```

Write to SQLite instead of JSON:
```bash
onionharvest run "http://example.onion" --out artifacts/harvest.db --format sqlite
```

Run a batch of URLs from a text file into one SQLite artifact:
```bash
onionharvest run-batch --input urls.txt --out artifacts/harvest.db
```

## Legal / Ethical Usage Note

Use OnionHarvest only for lawful, authorized, and ethically justified activities.

- Do **not** use this tool to access systems or content in violation of law, terms of service, or local regulations.
- Do **not** use this tool for harassment, fraud, credential theft, malware operations, or deanonymization attempts.
- Respect privacy, consent, robots/usage policies (where applicable), and data minimization principles.
- You are responsible for ensuring your use complies with all applicable laws and policies in your jurisdiction.

## Expected Output Format

When you run `onionharvest run`, OnionHarvest creates a single record with these fields:

- `url` (string): input URL
- `fetched_via` (string): Tor endpoint used (for example `tor://127.0.0.1:9050`)
- `title` (string or `null`): extracted `<title>` content
- `description` (string or `null`): extracted `<meta name="description">` content
- `links_count` (integer): number of `<a>` tags seen
- `text_preview` (string or `null`): first 280 characters of visible text

### JSON example
```json
{
  "url": "http://example.onion",
  "fetched_via": "tor://127.0.0.1:9050",
  "title": "Example Domain",
  "description": "Example description",
  "links_count": 3,
  "text_preview": "Example Domain This domain is for use in illustrative examples..."
}
```

### SQLite schema
Table name: `harvest_records`

Columns:
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `url` (TEXT NOT NULL)
- `fetched_via` (TEXT NOT NULL)
- `title` (TEXT)
- `description` (TEXT)
- `links_count` (INTEGER)
- `text_preview` (TEXT)

## Troubleshooting

### Tor not running
Symptom:
```text
ERROR: Tor bootstrap failed: unable to connect to SOCKS proxy at 127.0.0.1:9050...
```
What to do:
1. Start Tor on your machine (`tor` service or Tor daemon).
2. Confirm something is listening on `127.0.0.1:9050`.
3. Re-run `onionharvest test-connection`.

### Timeouts during fetch
Symptom:
```text
ERROR: Fetch failed for URL '...': ...timed out...
```
What to do:
1. Retry the command (Tor circuits can be slow/variable).
2. Confirm the target URL is currently reachable.
3. Check local network/firewall restrictions that may block Tor traffic.
4. If needed, update code to increase fetch timeout (default is 20 seconds in `fetch_url_via_tor`).

### Bad or unexpected HTML extraction
Symptom:
- Missing `title`/`description`
- `links_count` seems off
- `text_preview` contains noisy content

What to do:
1. Run `fetch` to inspect the raw HTML returned.
2. Verify the page actually includes `<title>` and `<meta name="description">`.
3. Expect minimal parsing in v0.0.0 (simple HTML parser, no JS rendering).
4. For dynamic/JS-heavy pages, extend extraction logic before relying on outputs.

## Run tests

```bash
cd /workspace/OnionHarvest/OnionHarvest
pytest -q
```
