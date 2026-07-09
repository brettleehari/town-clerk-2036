#!/usr/bin/env bash
# "A Day at the Storefront" — the KYA demo, as raw curls.
# Usage: ./demo.sh   (defaults to the live deployment; BASE=http://localhost:8000 for local)
set -e
BASE="${BASE:-https://civil-ledger.onrender.com}"
j() { python3 -c "import sys,json;d=json.load(sys.stdin);print(json.dumps({k:d.get(k) for k in ['agent_id','proceed','reason_code','allowed_categories']}))"; }

echo "=== KYA · A Day at the Storefront (base: $BASE) ==="
echo
echo "You are Marsh & Co.'s corporate agent. Six customers line up to buy (category: commerce)."
echo

for A in a-ada-01 a-marlow-01 a-june-01 a-silas-01 a-tam-01 a-shadow-99; do
  printf "customer %-14s -> " "$A"
  curl -s "$BASE/verify-counterparty?agent_id=$A&category=commerce" | j
done

echo
echo "--- a-shadow-99 is an impostor (NO_VALID_BINDING). Register as police and flag it. ---"
POLICE_KEY=$(curl -s -X POST "$BASE/institutions/register" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Demo Police","role":"police"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['api_key'])")
curl -s -X POST "$BASE/attestations" -H "X-API-Key: $POLICE_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"principal_id":"-","event":"flag_rogue","detail":{"agent_id":"a-shadow-99"}}' | python3 -c "import sys,json;print('flagged:',json.load(sys.stdin))"

echo
echo "--- The executor of the late Silas Crane settles the estate (category: estate). ---"
printf "executor a-vane-exec -> "
curl -s "$BASE/verify-counterparty?agent_id=a-vane-exec&category=estate" | j

echo
echo "--- The DNS-style resolution chain for a living citizen ---"
curl -s "$BASE/resolve/a-ada-01" | python3 -c "import sys,json;d=json.load(sys.stdin);print(' -> '.join(h.get('authority',h['level']) for h in d['chain']))"

echo
echo "Day's ledger: served the living, refused the dead/frozen/jailed/minor, caught one impostor."
