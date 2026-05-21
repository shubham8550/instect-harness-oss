#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Instect, Inc.
#
# drift_check.sh — fail if committed `_generated/` outputs no longer match the
# codegen pipeline. Wraps `tools/codegen/codegen.py --mode=check`.
#
# Local usage:
#   bash tools/drift_check.sh
#
# CI usage: invoked by `.github/workflows/codegen-drift.yml`.

set -euo pipefail

# Resolve repo root from this script's location so the wrapper works no matter
# where it is invoked from.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

SCHEMAS_DIR="${SCHEMAS_DIR:-schemas}"
OUT_PY="${OUT_PY:-python/packages/instect_core/src/instect_core/_generated}"
OUT_TS="${OUT_TS:-typescript/packages/core/src/_generated}"
OUT_RUST="${OUT_RUST:-crates/insect-core/src/_generated}"

PY="${PY:-}"
if [[ -z "${PY}" ]]; then
  if command -v uv >/dev/null 2>&1; then
    PY="uv run python"
  elif command -v python3 >/dev/null 2>&1; then
    PY="python3"
  else
    echo "drift_check: no python interpreter (need 'uv' or 'python3')" >&2
    exit 2
  fi
fi

echo "drift_check: invoking codegen in check mode" >&2

if ! ${PY} tools/codegen/codegen.py \
  --mode=check \
  --schemas-dir="${SCHEMAS_DIR}" \
  --out-py="${OUT_PY}" \
  --out-ts="${OUT_TS}" \
  --out-rust="${OUT_RUST}"; then
  cat >&2 <<'EOF'

drift_check: FAIL — generated outputs do not match committed files.

Fix:
  1. Run  just codegen
  2. git add -p  the regenerated `_generated/` files
  3. Commit and re-push

If `just codegen` doesn't exist locally, install:
  uv pip install -r tools/codegen/requirements.txt
  cargo install typify-cli         # Rust generator
  # node 22 LTS + pnpm for the TS generator

EOF
  exit 1
fi

echo "drift_check: ok" >&2
