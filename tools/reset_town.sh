#!/usr/bin/env bash
# On-demand demo reset — restore the seeded town to its canonical state right before a demo.
# Judges immigrate residents, flag rogues (a-shadow-99!), and change statuses; this puts it
# all back. Destructive by design; the root signing key is NOT rotated, so /pubkey and every
# previously issued certificate still verify.
#
# Usage:
#   KYA_ADMIN_KEY=<key> ./tools/reset_town.sh                     # reset the live deployment
#   KYA_ADMIN_KEY=<key> BASE=http://localhost:8000 ./tools/reset_town.sh
#   ./tools/reset_town.sh <admin-key> [base-url]                  # key/base as positional args
#
# The admin key is the value set as KYA_ADMIN_KEY in the deployment's environment
# (Render dashboard → Environment). It is never stored in this script.
set -uo pipefail

BASE="${BASE:-${2:-https://civil-ledger.onrender.com}}"; BASE="${BASE%/}"
KEY="${KYA_ADMIN_KEY:-${1:-}}"

if [ -z "$KEY" ]; then
  echo "✗ No admin key given."
  echo "    KYA_ADMIN_KEY=<key> $0"
  echo "    $0 <key> http://localhost:8000"
  exit 2
fi

# Parsing is pure curl+grep — no python/jq dependency, so it runs anywhere.
_field(){ printf '%s' "$1" | grep -o "\"$2\":\"[^\"]*\"" | head -1 | cut -d'"' -f4; }
_bool(){  printf '%s' "$1" | grep -o "\"$2\":[a-z]*"     | head -1 | cut -d: -f2; }
_num(){   printf '%s' "$1" | grep -o "\"$2\":[0-9]*"     | head -1 | cut -d: -f2; }

verdict(){ # agent, category -> "REASON (proceed=…)"
  local body; body="$(curl -s --max-time 30 "$BASE/verify-counterparty?agent_id=$1&category=$2")"
  local rc; rc="$(_field "$body" reason_code)"
  if [ -n "$rc" ]; then echo "$rc (proceed=$(_bool "$body" proceed))"; else echo "unreachable"; fi
}

echo "→ Target: $BASE"
printf "→ Waking the ledger (free dyno may cold-start)"
up=0
for _ in $(seq 1 45); do
  if curl -s -o /dev/null --max-time 20 "$BASE/health"; then up=1; echo " — awake."; break; fi
  printf "."; sleep 2
done
[ "$up" -ne 1 ] && { echo; echo "✗ $BASE/health never answered."; exit 1; }

echo "→ Before:  a-shadow-99 → $(verdict a-shadow-99 commerce)"
echo "→ Resetting the seeded town…"

resp="$(curl -s --max-time 60 -w $'\n%{http_code}' -X POST "$BASE/admin/reset-seed" -H "X-Admin-Key: $KEY")"
code="${resp##*$'\n'}"; body="${resp%$'\n'*}"
if [ "$code" != "200" ]; then
  echo "✗ Reset failed (HTTP $code): $body"
  case "$code" in
    403) echo "  → KYA_ADMIN_KEY is not set on the deployment. Set it in the Render dashboard (Environment) and redeploy.";;
    401) echo "  → The key you passed does not match the deployment's KYA_ADMIN_KEY.";;
  esac
  exit 1
fi
echo "✓ Reset: $(_num "$body" principals) principals, $(_num "$body" agents) agents · root key unchanged"

echo "→ After (canonical checks):"
printf "    a-ada-01    commerce → %-34s expect OK\n"                "$(verdict a-ada-01 commerce)"
printf "    a-shadow-99 commerce → %-34s expect NO_VALID_BINDING\n"  "$(verdict a-shadow-99 commerce)"
printf "    a-june-01   commerce → %-34s expect CAPACITY_FROZEN\n"   "$(verdict a-june-01 commerce)"
printf "    a-silas-01  estate   → %-34s expect OK (executor)\n"     "$(verdict a-silas-01 estate)"
echo "✓ Town restored. Ready for the demo."
