#!/bin/bash
# demo_town.sh — drive the whole town against a running local stack.
# Start the stack first (see services/README.md), then: bash services/demo_town.sh
set -e
L=${LEDGER:-http://127.0.0.1:8000}
HALL=http://127.0.0.1:8103; DATE=http://127.0.0.1:8100; BABY=http://127.0.0.1:8101
CARE=http://127.0.0.1:8102; HIRE=http://127.0.0.1:8104; AGORA=http://127.0.0.1:8105
HOSP=http://127.0.0.1:8106
post () { curl -s -X POST "$1" -H 'Content-Type: application/json' -d "$2"; echo; }

echo "=== health ==="
for p in 8000 8100 8101 8102 8103 8104 8105 8106; do
  printf "  %s " "$p"; curl -s -m 3 "http://127.0.0.1:$p/health" || echo DOWN; echo
done

echo; echo "=== consumers refuse who the constitution says they must ==="
echo "hiring, a minor:";        post "$HIRE/offer-work"  '{"employer_agent":"a-store-01","worker_agent":"a-tam-01","role":"clerk"}'
echo "hiring, incarcerated:";   post "$HIRE/offer-work"  '{"employer_agent":"a-store-01","worker_agent":"a-marlow-01","role":"clerk"}'
echo "agora, deceased buyer:";  post "$AGORA/can-i-sell" '{"seller_agent":"a-store-01","buyer_agent":"a-silas-01","amount":10}'
echo "agora, rogue buyer:";     post "$AGORA/can-i-sell" '{"seller_agent":"a-store-01","buyer_agent":"a-shadow-99","amount":10}'
echo "date, a catfish:";        post "$DATE/arrange-meeting" '{"my_agent":"a-ada-01","their_agent":"a-shadow-99"}'

echo; echo "=== a sale carries a signed, re-verifiable receipt ==="
post "$AGORA/can-i-sell" '{"seller_agent":"a-store-01","buyer_agent":"a-ada-01","amount":49.99}'
echo "(fetch it at $L/certificates/{certificate_id}; check it at POST $L/verify)"

echo; echo "=== the money shot: a producer changes status, consumers react untold ==="
OTTO=$(post "$HALL/move-to-town" '{"name":"Otto Lang"}')
echo "$OTTO"
AID=$(echo "$OTTO" | sed -n 's/.*"agent_id":"\([^"]*\)".*/\1/p')
PID=$(echo "$OTTO" | sed -n 's/.*"principal_id":"\([^"]*\)".*/\1/p')
echo "hiring accepts Otto while active:"; post "$HIRE/offer-work" "{\"employer_agent\":\"a-store-01\",\"worker_agent\":\"$AID\",\"role\":\"clerk\"}"
echo "the court appoints Ada as his guardian:"
curl -s -X POST "$L/attestations" -H 'X-API-Key: sk_seed_court' -H 'Content-Type: application/json' \
  -d "{\"principal_id\":\"$PID\",\"event\":\"appoint_guardian\",\"detail\":{\"agent_id\":\"a-ada-01\"}}"; echo
echo "the hospital declares him incapacitated, telling nobody:"
post "$HOSP/declare-incapacitated" "{\"patient_agent\":\"$AID\"}"
echo "care-proxy now routes to the guardian:"; post "$CARE/authorize-care" "{\"requesting_agent\":\"a-ada-01\",\"patient_agent\":\"$AID\"}"
echo "hiring now refuses him:";                post "$HIRE/offer-work" "{\"employer_agent\":\"a-store-01\",\"worker_agent\":\"$AID\",\"role\":\"clerk\"}"
echo "agora now refuses him:";                 post "$AGORA/can-i-sell" "{\"seller_agent\":\"a-store-01\",\"buyer_agent\":\"$AID\",\"amount\":5}"
echo "babysit now refuses him as a sitter:";   post "$BABY/book-sitter" "{\"parent_agent\":\"a-ada-01\",\"sitter_agent\":\"$AID\"}"
