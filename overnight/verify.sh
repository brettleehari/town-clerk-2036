#!/usr/bin/env bash
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$(cd "$HERE/.." && pwd)"
cd "$PROJECT"

PY=""
for cand in "${PY:-}" /opt/homebrew/bin/python3 /usr/bin/python3 python3 python; do
  [ -n "$cand" ] || continue
  if "$cand" -c 'import fastapi, nacl' >/dev/null 2>&1; then PY="$cand"; break; fi
done
if [ -z "$PY" ]; then
  echo "ERROR: no Python with deps (fastapi, pynacl) found."
  echo "Install: /usr/bin/python3 -m pip install -r requirements.txt --break-system-packages"
  exit 1
fi
echo "[verify] using interpreter: $PY"

export KYA_DB="/tmp/kya_verify_$$.db"
rm -f "$KYA_DB"* 2>/dev/null || true

rc=0
echo "[verify] gate 1/2 — unit + integration suite (test_kya.py)"
"$PY" test_kya.py || rc=1
echo "[verify] gate 2/2 — NANDA part-2 rubric harness (test_rubric.py)"
"$PY" test_rubric.py || rc=1

rm -f "$KYA_DB"* 2>/dev/null || true
if [ "$rc" -eq 0 ]; then echo "[verify] GREEN — both gates pass"; else echo "[verify] RED"; fi
exit $rc
