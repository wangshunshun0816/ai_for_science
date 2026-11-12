#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
uv lock --check
uv sync --locked --no-install-project
uv sync --locked --no-build-isolation --no-editable --reinstall-package danus-ai
uv run --no-sync python --version
uv run --no-sync ruff check danus_ai scripts/check_import_boundaries.py scripts/export_r02_schema.py tests
uv run --no-sync ruff format --check danus_ai scripts/check_import_boundaries.py scripts/export_r02_schema.py tests
uv run --no-sync mypy
uv run --no-sync python scripts/check_import_boundaries.py
uv run --no-sync python scripts/export_r02_schema.py --check
uv run --no-sync pytest -q
uv build --no-build-isolation
