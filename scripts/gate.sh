#!/usr/bin/env bash
set -euo pipefail

BASE="${GATE_BASE:-origin/main}"
THRESHOLD="$(uv run python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['tool']['coverage']['report']['fail_under'])")"

echo "[1/6] Ruff lint & format..."
uv run ruff check --no-fix .
uv run ruff format --check .

echo "[2/6] Mypy..."
uv run mypy .

echo "[3/6] Pytest & coverage..."
uv run pytest

echo "[4/6] Changed-line coverage vs ${BASE}..."
uv run diff-cover coverage.xml --compare-branch="${BASE}" --include-untracked --fail-under="${THRESHOLD}"

echo "[5/6] gov check vs ${BASE}..."
gov check --base "${BASE}"

echo "[6/6] Pre-commit hygiene (all files)..."
uv run pre-commit run --all-files

echo "[SUCCESS] All quality gates passed."
