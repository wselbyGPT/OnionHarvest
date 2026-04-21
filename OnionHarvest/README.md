# OnionHarvest

This repository is currently a scaffold (most source files are present but empty), so there is not yet a working command-line interface to run.

## Use from WSL Ubuntu CLI

From your WSL Ubuntu shell:

```bash
cd /workspace/OnionHarvest/OnionHarvest
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

At this point, there are two ways to run code while developing:

1. Run a module directly:

```bash
python -m onionharvest.cli
```

2. Run tests:

```bash
pytest -q
```

## Current status

- `pyproject.toml` is empty, so there is no install metadata or console script configured yet.
- `onionharvest/*.py` files are placeholders and do not currently implement behavior.

If you want, I can next add a minimal working CLI (`onionharvest --help`) and proper `pyproject.toml` so it can be installed and used normally from WSL.
