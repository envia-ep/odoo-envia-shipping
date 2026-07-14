#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(python3 -c "import ast; print(ast.literal_eval(open('$ROOT/addons/envia/__manifest__.py').read())['version'])")"
OUT="$ROOT/dist/envia-${VERSION}.zip"
mkdir -p "$ROOT/dist"
cd "$ROOT/addons"
zip -r "$OUT" envia envia_http \
  -x "*/__pycache__/*" "*__pycache__*" "*.pyc" "*.pyo" "*/.DS_Store" "*/scripts/*"
echo "Built $OUT ($(du -h "$OUT" | cut -f1))"
