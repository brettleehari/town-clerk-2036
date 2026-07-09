#!/usr/bin/env bash
# Smoke test: boot a real uvicorn server, hit the live endpoints an agent would call on
# its very first visit, assert the shapes SKILL.md promises, then shut the server down.
# This exercises the actual ASGI app (routing, startup seeding) — test_kya.py calls the
# Python functions directly and never boots a server, so this is the one gate that would
# catch a broken route path or a startup crash.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

PY=""
for cand in /opt/homebrew/bin/python3 /usr/bin/python3 python3 python; do
  if command -v "$cand" >/dev/null 2>&1 && "$cand" -c 'import fastapi, uvicorn, nacl' >/dev/null 2>&1; then
    PY="$cand"; break
  fi
done
if [ -z "$PY" ]; then
  echo "ERROR: no Python with deps (fastapi, uvicorn, pynacl) found."
  exit 1
fi

PORT=8931
export KYA_DB="/tmp/kya_smoke_$$.db"
rm -f "$KYA_DB"* 2>/dev/null || true
BASE="http://127.0.0.1:$PORT"

"$PY" -m uvicorn app:app --port "$PORT" >"/tmp/kya_smoke_$$.log" 2>&1 &
SERVER_PID=$!
cleanup() {
  kill "$SERVER_PID" >/dev/null 2>&1 || true
  wait "$SERVER_PID" 2>/dev/null || true
  rm -f "$KYA_DB"* "/tmp/kya_smoke_$$.log" 2>/dev/null || true
}
trap cleanup EXIT

echo "[smoke] waiting for $BASE/health ..."
up=0
for _ in $(seq 1 50); do
  if curl -s -o /dev/null "$BASE/health"; then up=1; break; fi
  sleep 0.2
done
if [ "$up" -ne 1 ]; then
  echo "[smoke] FAIL — server never came up"
  cat "/tmp/kya_smoke_$$.log"
  exit 1
fi

rc=0
check() {  # check <label> <url> <python-expr-over-d>
  local label="$1" url="$2" expr="$3"
  local body
  body="$(curl -s "$url")"
  if echo "$body" | "$PY" -c "
import sys, json
d = json.loads(sys.stdin.read())
assert ($expr), 'unexpected: ' + json.dumps(d)[:300]
" 2>/tmp/kya_smoke_check_err; then
    echo "  PASS  $label"
  else
    echo "  FAIL  $label"
    cat /tmp/kya_smoke_check_err
    rc=1
  fi
  rm -f /tmp/kya_smoke_check_err
}

echo "[smoke] gate — live server, zero-auth reads an agent hits first"
check "GET /health"                                  "$BASE/health" \
  "d['ok'] is True and d['service'] == 'KYA Civil Ledger'"
check "GET /constitution"                            "$BASE/constitution" \
  "d['town'] and d['root_pubkey'] and 'status_acl' in d"
check "GET /verify-counterparty (real customer)"     "$BASE/verify-counterparty?agent_id=a-ada-01&category=commerce" \
  "d['proceed'] is True and d['reason_code'] == 'OK'"
check "GET /verify-counterparty (impostor)"          "$BASE/verify-counterparty?agent_id=a-shadow-99&category=commerce" \
  "d['proceed'] is False and d['reason_code'] == 'NO_VALID_BINDING'"
check "GET /elections/elec-council-2035"             "$BASE/elections/elec-council-2035" \
  "d['election_id'] == 'elec-council-2035' and 'tally' in d"

if [ "$rc" -eq 0 ]; then echo "[smoke] GREEN"; else echo "[smoke] RED"; fi
exit $rc
