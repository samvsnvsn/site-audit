#!/usr/bin/env bash
# verify.sh - runs the full automated test suite for site-audit.
# Requires Python 3.8+. No internet needed (tests serve fixture pages locally).
# Picks a working interpreter: python3 if real, otherwise the Windows py launcher.
set -euo pipefail
cd "$(dirname "$0")"

PY=""
if command -v python3 >/dev/null 2>&1 && python3 -c "import sys" 2>/dev/null; then
  PY=python3
elif command -v python >/dev/null 2>&1 && python -c "import sys" 2>/dev/null; then
  PY=python
elif command -v py >/dev/null 2>&1; then
  PY=py
else
  echo "error: no Python interpreter found (need python3, python, or py)" >&2
  exit 1
fi

echo "==> verify.sh: running automated tests for site-audit (interpreter: $PY)"
"$PY" -m unittest -v test_site_audit
echo "==> all tests passed"