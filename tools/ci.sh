#!/usr/bin/env bash
# Project checks (docs/lld/LLD-platform-v1.md, packaging and CI).
#   tools/ci.sh --python-only   lint, format check, strict mypy, tests, generator checks and
#                               the SDD checks (spec-lint and trace-check)
#   tools/ci.sh                 the same plus the 85% coverage gate, a wheel build and
#                               the CLI smoke test (milestone exit and GitHub Actions)
set -euo pipefail

cd "$(dirname "$0")/.."

mode=full
case "${1:-}" in
  --python-only) mode=python ;;
  "") ;;
  *)
    echo "usage: tools/ci.sh [--python-only]" >&2
    exit 2
    ;;
esac

run() {
  echo "+ $*"
  "$@"
}

run uv run ruff check
run uv run ruff format --check
run uv run mypy src

if [[ $mode == python ]]; then
  run uv run pytest -q --cov=research_mcp --cov-report=term
else
  run uv run pytest -q --cov=research_mcp --cov-report=term --cov-fail-under=85
fi

for generator in tools/gen_m0_plan.py tools/gen_inventory.py; do
  if [[ -f $generator ]]; then
    run uv run python "$generator" --check
  fi
done

# Spec-driven development: documents, criteria and @spec links (needs Node 20 or later).
run node tools/sdd/cli.mjs check

if [[ $mode == full ]]; then
  run uv build
  if [[ -f src/research_mcp/cli.py ]]; then
    run uv run research-mcp --help
  fi
fi

echo "ci.sh ($mode): all checks passed"
