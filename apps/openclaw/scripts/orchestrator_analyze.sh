#!/usr/bin/env bash
# OpenClaw exec entry — resolves repo venv/python and runs orchestrator_analyze.py
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PY="${MYTRADING_PYTHON:-${ROOT}/.venv/bin/python}"

if [[ ! -x "${PY}" ]]; then
  PY="$(command -v python3)"
fi

cd "${ROOT}"
exec "${PY}" "${SCRIPT_DIR}/orchestrator_analyze.py" "$@"
