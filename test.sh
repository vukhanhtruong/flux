#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PACKAGES=(core api-server mcp-server agent-bot)
FAILED=()
COVERAGE=false

for arg in "$@"; do
    case $arg in
        --coverage|-c) COVERAGE=true ;;
    esac
done

for pkg in "${PACKAGES[@]}"; do
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Testing: $pkg"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    if $COVERAGE; then
        if ! (cd "$ROOT/packages/$pkg" && pytest tests/ -v --cov=src --cov-report=term-missing); then
            FAILED+=("$pkg")
        fi
    else
        if ! (cd "$ROOT/packages/$pkg" && pytest tests/ -v); then
            FAILED+=("$pkg")
        fi
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ ${#FAILED[@]} -eq 0 ]; then
    echo "  All packages passed ✓"
else
    echo "  Failed packages: ${FAILED[*]}"
    exit 1
fi
