#!/usr/bin/env bash
set -euo pipefail

BASE="${GATE_BASE:-origin/main}"
THRESHOLD="$(uv run python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['tool']['coverage']['report']['fail_under'])")"

echo "[1/5] Ruff lint & format..."
uv run ruff check --no-fix .
uv run ruff format --check .

echo "[2/5] Mypy..."
uv run mypy .

echo "[3/5] Pytest & coverage..."
uv run pytest

echo "[4/5] Changed-line coverage vs ${BASE}..."
uv run diff-cover coverage.xml --compare-branch="${BASE}" --include-untracked --fail-under="${THRESHOLD}"

echo "[5/5] Pre-commit hygiene (all files)..."
uv run pre-commit run --all-files

echo "[SUCCESS] All quality gates passed."
