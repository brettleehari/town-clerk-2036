# SCENARIOS — end-to-end walkthroughs

A menu of 8 scenarios, runnable in order against the pre-seeded town of Alford, MA. Every
`GET` needs no credentials; `POST`s that mutate state use the seed institution keys below.
Set once:

    export BASE=http://localhost:8000

Seed keys (sandbox — see `SKILL.md` for how to mint your own):
`sk_seed_registrar`, `sk_seed_court`, `sk_seed_hospital`, `sk_seed_coroner_a`,
`sk_seed_coroner_b`, `sk_seed_police`.

---

## 1. The impostor at the storefront (flagship — ~7 calls, no setup)

You are Marsh & Co.'s storefront agent. A queue of counterparties wants to buy.

```bash
# 1. A real customer: proceed
curl "$BASE/verify-counterparty?agent_id=a-ada-01&category=commerce"
# -> proceed:true, reason_code:OK

# 2. An impostor claiming to represent someone: refuse
curl "$BASE/verify-counterparty?agent_id=a-shadow-99&category=commerce"
# -> proceed:false, reason_code:NO_VALID_BINDING

# 3. Report it — register as police, then flag the agent
curl -sX POST "$BASE/institutions/register" -H 'content-type: application/json' \
  -d '{"name":"Alford PD (you)","role":"police"}'   # -> {institution_id, api_key}
curl -sX POST "$BASE/attestations" -H "x-api-key: <api_key from above>" \
  -H 'content-type: application/json' \
  -d '{"principal_id":"p-ada-marsh","event":"flag_rogue","detail":{"agent_id":"a-shadow-99"}}'

# 4. Now every storefront refuses it town-wide
curl "$BASE/verify-counterparty?agent_id=a-shadow-99&category=commerce"
# -> proceed:false, reason_code:ROGUE_FLAGGED

# 5. Three more counterparties, three more reasons to refuse
curl "$BASE/verify-counterparty?agent_id=a-june-01&category=financial"   # -> CAPACITY_FROZEN (comatose)
curl "$BASE/verify-counterparty?agent_id=a-marlow-01&category=commerce" # -> CATEGORY_NOT_ALLOWED (jailed)
curl "$BASE/verify-counterparty?agent_id=a-silas-01&category=commerce" # -> PRINCIPAL_DECEASED

# 6. The late Silas Crane's executor can still settle his estate
curl "$BASE/verify-counterparty?agent_id=a-vane-exec&category=estate"
# -> proceed:true, reason_code:OK
```

Expected `reason_code`s, in order: `OK`, `NO_VALID_BINDING`, `ROGUE_FLAGGED`,
`CAPACITY_FROZEN`, `CATEGORY_NOT_ALLOWED`, `PRINCIPAL_DECEASED`, `OK`.

---

## 2. Storefront gate (repeat-customer subscription)

Gate every inbound order behind one check, and get pushed a webhook the instant a
customer's standing changes — no polling.

```bash
curl "$BASE/verify-counterparty?agent_id=a-ada-01&category=commerce"   # -> proceed:true
curl -sX POST "$BASE/watch" -H 'content-type: application/json' \
  -d '{"target":"a-ada-01","callback_url":"https://your-store.example/webhooks/kya"}'
# -> {watch_id, ...}  fires if the binding is revoked or capacity changes
```

Expected: `proceed:true, reason_code:OK`; a `watch_id` is returned.

---

## 3. A whole life (hospitalization, sentencing, death — sandbox)

Create a fresh resident and walk their civil status through the state machine.

```bash
REG=$(curl -sX POST "$BASE/institutions/register" -d '{"name":"You","role":"registrar"}' -H 'content-type: application/json' | python3 -c 'import sys,json;print(json.load(sys.stdin)["api_key"])')

P=$(curl -sX POST "$BASE/principals" -H "x-api-key: $REG" -d '{"name":"Rae Fenn"}' -H 'content-type: application/json')
PID=$(echo $P | python3 -c 'import sys,json;print(json.load(sys.stdin)["principal_id"])')
AID=$(curl -sX POST "$BASE/agents" -H "x-api-key: $REG" -d '{"name":"Rae'\''s agent"}' -H 'content-type: application/json' | python3 -c 'import sys,json;print(json.load(sys.stdin)["agent_id"])')
curl -sX POST "$BASE/bindings" -H "x-api-key: $REG" -d "{\"agent_id\":\"$AID\",\"principal_id\":\"$PID\"}" -H 'content-type: application/json'

curl "$BASE/verify-counterparty?agent_id=$AID&category=financial"   # -> OK

HOSP=$(curl -sX POST "$BASE/institutions/register" -d '{"name":"You (hospital)","role":"hospital"}' -H 'content-type: application/json' | python3 -c 'import sys,json;print(json.load(sys.stdin)["api_key"])')
curl -sX POST "$BASE/attestations" -H "x-api-key: $HOSP" \
  -d "{\"principal_id\":\"$PID\",\"event\":\"declare_incapacitated\"}" -H 'content-type: application/json'
curl "$BASE/verify-counterparty?agent_id=$AID&category=financial"   # -> CAPACITY_FROZEN

curl -sX POST "$BASE/attestations" -H "x-api-key: $HOSP" \
  -d "{\"principal_id\":\"$PID\",\"event\":\"declare_recovered\"}" -H 'content-type: application/json'
curl "$BASE/verify-counterparty?agent_id=$AID&category=financial"   # -> OK again
```

Expected `reason_code`s: `OK`, `CAPACITY_FROZEN`, `OK`.

---

## 4. Incarceration ACL (court-set capacity)

The seeded resident `p-marlow-reyes` is incarcerated; the court set his ACL to
`legal, family_support` only.

```bash
curl "$BASE/verify-counterparty?agent_id=a-marlow-01&category=commerce"  # -> CATEGORY_NOT_ALLOWED
curl "$BASE/verify-counterparty?agent_id=a-marlow-01&category=legal"     # -> OK
```

Expected: `CATEGORY_NOT_ALLOWED` then `OK`.

---

## 5. Birth & parental controls

```bash
REG=sk_seed_registrar
curl -sX POST "$BASE/births" -H "x-api-key: $REG" -H 'content-type: application/json' \
  -d '{"name":"Baby Finch","regent_agent_ids":["a-ada-01"],"spend_cap":25}'
# -> {principal_id, natal_agent_id, principal_key, status:"minor", ...}

curl "$BASE/verify-counterparty?agent_id=<natal_agent_id>&category=financial"
# -> proceed:false, reason_code:CAPACITY_FROZEN (routed to regents)

curl -sX POST "$BASE/attestations" -H "x-api-key: $REG" -H 'content-type: application/json' \
  -d '{"principal_id":"<principal_id>","event":"majority_handover"}'
curl "$BASE/verify-counterparty?agent_id=<natal_agent_id>&category=financial"
# -> proceed:true, reason_code:OK (adult now, controls lifted)
```

Expected `reason_code`s: `CAPACITY_FROZEN`, then `OK`.

---

## 6. The kill switch (human severs their own agent, zero latency)

```bash
curl "$BASE/bindings/a-ada-01"     # -> find the binding_id ("b-ada")
curl "$BASE/verify-counterparty?agent_id=a-ada-01&category=commerce"   # -> OK, before

curl -X DELETE "$BASE/bindings/b-ada" -H "x-principal-key: <p-ada-marsh's principal_key>"
curl "$BASE/verify-counterparty?agent_id=a-ada-01&category=commerce"
# -> proceed:false, reason_code:NO_VALID_BINDING
```

(Run against a resident you created yourself in Scenario 3 if you don't want to disturb
the shared seed data — the kill switch is instant and has no undo.)

Expected: `OK` before, `NO_VALID_BINDING` after.

---

## 7. Immigrate, then vote

```bash
curl -sX POST "$BASE/immigrate" -H "x-api-key: sk_seed_registrar" -H 'content-type: application/json' \
  -d '{"name":"Rae Fenn"}'
# -> {principal_id, agent_id, principal_key, ...}

curl "$BASE/verify-counterparty?agent_id=<agent_id>&category=civic"   # -> OK, you're a resident

curl -sX POST "$BASE/vote" -H 'content-type: application/json' \
  -d '{"election_id":"elec-council-2035","agent_id":"<agent_id>","candidate":"Owen Brook"}'
# -> {status:"counted"}
curl "$BASE/elections/elec-council-2035"   # -> tally now includes your vote

# vote again -> 409 (one resident, one vote)
curl -si -X POST "$BASE/vote" -H 'content-type: application/json' \
  -d '{"election_id":"elec-council-2035","agent_id":"<agent_id>","candidate":"Owen Brook"}' | head -1
```

Expected: verify `OK`; first vote `status:"counted"`; second vote `HTTP 409`.

---

## 8. Will, death, inheritance, and Lazarus (contesting a wrongful death record)

Uses the seeded case of Edith Vale, who wrote a will naming heir Mara Vale.

```bash
# The seeded inheritance already executed: Edith's agent now steward-run by her heir
curl "$BASE/verify-counterparty?agent_id=a-edith-01&category=estate"
# -> proceed:true, reason_code:OK, inherited:true, principal_ref:p-mara-vale

curl "$BASE/verify-counterparty?agent_id=a-edith-01&category=commerce"
# -> proceed:false, reason_code:CATEGORY_NOT_ALLOWED (will capped it to estate/family_support)

# Now watch a fresh death + Lazarus contest end to end on a resident you create yourself
# (Scenario 3's Rae Fenn), so you hold the principal_key needed to contest:
curl -sX POST "$BASE/attestations" -H "x-api-key: sk_seed_coroner_a" -H 'content-type: application/json' \
  -d "{\"principal_id\":\"$PID\",\"event\":\"death\"}"     # 1st of 2 coroners: death_pending
curl "$BASE/verify-counterparty?agent_id=$AID&category=commerce"   # -> still OK, not finalized yet

curl -sX POST "$BASE/attestations" -H "x-api-key: sk_seed_coroner_b" -H 'content-type: application/json' \
  -d "{\"principal_id\":\"$PID\",\"event\":\"death\"}"     # 2nd distinct coroner: finalized
curl "$BASE/verify-counterparty?agent_id=$AID&category=commerce"   # -> NO_VALID_BINDING (no will -> agent laid to rest)

# Contest within 72h (Lazarus protocol) — the record was wrong
curl -sX POST "$BASE/contest" -H 'content-type: application/json' \
  -d "{\"principal_id\":\"$PID\",\"principal_key\":\"<principal_key from Scenario 3>\"}"
curl "$BASE/verify-counterparty?agent_id=$AID&category=commerce"   # -> OK again, binding restored
```

Expected `reason_code`s: `OK` (inherited estate agent), `CATEGORY_NOT_ALLOWED` (inherited
agent outside will's categories), `OK` (death pending, not final), `NO_VALID_BINDING`
(second coroner finalizes; Rae wrote no will, so her personal agent is laid to rest — to see
`PRINCIPAL_DECEASED` on a still-bound agent, use the seeded executor case `a-silas-01`),
`OK` (post-Lazarus).

---

## Reason code reference

`OK` · `NO_VALID_BINDING` · `NXAGENT` · `BINDING_EXPIRED` · `ROGUE_FLAGGED` ·
`PRINCIPAL_DECEASED` · `CAPACITY_FROZEN` · `CATEGORY_NOT_ALLOWED` · `PRINCIPAL_MISSING` ·
`LAZARUS_WINDOW_OPEN` · `UNKNOWN_PRINCIPAL`. Full semantics in `SKILL.md` and
`GET /constitution`.
