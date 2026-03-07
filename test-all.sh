#!/usr/bin/env bash
#
# test-all.sh — Run all tests locally with isolated test databases.
#
# Usage:
#   ./test-all.sh              # Run all tests
#   ./test-all.sh --coverage   # Run with coverage reports
#
# Creates a temporary SQLite + zvec database for E2E tests,
# completely isolated from the dev environment (.dev-data/).
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$ROOT/.venv"

# --- Activate venv -----------------------------------------------------------
if [ ! -d "$VENV" ]; then
    echo "Error: venv not found at $VENV. Run ./dev.sh first to set up the environment."
    exit 1
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"
PACKAGES=(core api-server mcp-server agent-bot)
FAILED=()
COVERAGE=false

for arg in "$@"; do
    case $arg in
        --coverage|-c) COVERAGE=true ;;
    esac
done

# --- Isolated test data directory (auto-cleaned) ----------------------------
TEST_DATA="$(mktemp -d "${TMPDIR:-/tmp}/flux-test-XXXXXX")"
mkdir -p "$TEST_DATA/sqlite" "$TEST_DATA/zvec"
export DATABASE_PATH="$TEST_DATA/sqlite/flux-test.db"
export ZVEC_PATH="$TEST_DATA/zvec"

cleanup() {
    echo ""
    echo "Cleaning up test data: $TEST_DATA"
    rm -rf "$TEST_DATA"
}
trap cleanup EXIT

echo ""
echo "Test data directory: $TEST_DATA"
echo "  DATABASE_PATH=$DATABASE_PATH"
echo "  ZVEC_PATH=$ZVEC_PATH"

# --- Run tests per package ---------------------------------------------------
for pkg in "${PACKAGES[@]}"; do
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Testing: $pkg"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    PYTEST_ARGS=(tests/ -v --tb=short)
    if $COVERAGE; then
        PYTEST_ARGS+=(--cov=src --cov-report=term-missing)
    fi
    if ! (cd "$ROOT/packages/$pkg" && pytest "${PYTEST_ARGS[@]}"); then
        FAILED+=("$pkg")
    fi
done

# --- Performance benchmarks --------------------------------------------------
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Performance benchmarks"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -d "$ROOT/packages/core/tests/test_perf" ]; then
    if ! (cd "$ROOT/packages/core" && pytest tests/test_perf/ -v --benchmark-only); then
        FAILED+=("core:perf")
    fi
else
    echo "  Skipped (no test_perf directory)"
fi

# --- Summary -----------------------------------------------------------------
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ ${#FAILED[@]} -eq 0 ]; then
    echo "  All tests passed"
else
    echo "  Failed: ${FAILED[*]}"
    exit 1
fi
