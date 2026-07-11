#!/usr/bin/env bash
# Test loop for the PostToolUse hook: runs the repo's two fast, in-process suites
# (test_kya.py — all 36 ledger routes; services/test_compose.py — the cross-service
# journey) after Claude edits a Python source file. Reads the hook's stdin JSON,
# skips non-.py edits, and prints a one-line JSON {"systemMessage": ...} verdict.
# Never blocks the turn — a failure is surfaced, not enforced.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"

# Resolve a Python that actually has the app's deps (this Mac has a stale x86 3.8
# first on PATH that fails "Bad CPU type" — so probe, don't trust bare `python3`).
PY=""
for cand in /opt/homebrew/bin/python3 /usr/bin/python3 python3 python; do
  if command -v "$cand" >/dev/null 2>&1 && "$cand" -c 'import fastapi, uvicorn, nacl' >/dev/null 2>&1; then
    PY="$cand"; break
  fi
done
[ -z "$PY" ] && { echo '{"systemMessage":"[tests] skipped — no Python with fastapi/uvicorn/pynacl found"}'; exit 0; }

# The hook pipes {"tool_input":{"file_path":"..."}} on stdin. If invoked by hand
# (no stdin), fall through and run the suites anyway.
HOOK_PAYLOAD="$(cat 2>/dev/null || true)"
export HOOK_PAYLOAD
if [ -n "$HOOK_PAYLOAD" ]; then
  f="$("$PY" -c 'import os,json
try:
    d=json.loads(os.environ.get("HOOK_PAYLOAD","") or "{}")
except Exception:
    d={}
print(d.get("tool_input",{}).get("file_path","") or d.get("tool_response",{}).get("filePath",""))')"
  # Only react to Python sources inside this repo. Markdown/HTML/db edits are a no-op.
  case "$f" in
    *.py) : ;;
    "")   : ;;   # manual run, no file → run anyway
    *)    exit 0 ;;
  esac
fi

log="$(mktemp)"
trap 'rm -f "$log"' EXIT
rc=0
"$PY" test_kya.py                >>"$log" 2>&1 || rc=1
"$PY" services/test_compose.py   >>"$log" 2>&1 || rc=1

kya="$(grep -oE '[0-9]+ passed, [0-9]+ failed' "$log" | head -1)"
comp="$(grep -oE 'compose: [0-9]+ passed, [0-9]+ failed' "$log" | head -1)"

if [ "$rc" -eq 0 ]; then
  printf '{"systemMessage":"[tests] GREEN — %s · %s"}\n' "${kya:-test_kya ok}" "${comp:-compose ok}"
else
  tail="$(grep -E 'FAIL|Error|Traceback|failed' "$log" | tail -3 | tr '\n' ' ' | sed 's/"/'"'"'/g')"
  printf '{"systemMessage":"[tests] RED — %s · %s | %s"}\n' "${kya:-?}" "${comp:-?}" "$tail"
fi
exit 0
