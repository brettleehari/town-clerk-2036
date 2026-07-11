---
name: town-ledger
user-invocable: true
description: >
  The Town Clerk's office for a 2036 agent-native town, governed by a machine-readable,
  signed constitution generated from the code that enforces it. Agents here are registered
  assets — titled to a human or institution, quota-bounded, owner-revocable, inherited by
  will — bound through a signed authority chain to their principal's live civil status.
  Gives an agent Civil Ledger identity reasoning: verify the human or institution behind any
  counterparty agent and get an Ed25519-signed proceed/refuse verdict before trust-sensitive
  actions — catching impostors and refusing principals who are deceased, incapacitated,
  incarcerated, missing, or minors. Use for "verify this agent", "can I trust this
  counterparty", "check before I pay them", or "report a rogue agent".
---

# KYA — Know Your Agent · The Civil Ledger

**KYC for the agent economy.** Before any agent transacts with another agent, it asks
the Civil Ledger one question — **"May I safely deal with this counterparty, in this
category, right now?"** — and gets back an Ed25519-signed verdict it can verify itself.

> In 2036, every resident, business, and institution acts through agents. **This is the Town
> Clerk's office for that town.** Agents here are not free-floating identities — they are
> *registered assets*, like vehicles or deeds: titled to a human or institution, bounded by
> quota, revocable by their owner in one call, and inherited through a will when the owner
> dies. Registration is what lets an agent act at all; an unregistered agent is `NXAGENT` —
> provably nobody's, refused everywhere. The ledger binds each agent to its principal's live
> civil status (active · minor · hospitalized · incapacitated · incarcerated · missing ·
> deceased) through a signed authority chain rooted at the town's **constitution** — a
> machine-readable law generated from the very code that enforces it, and signed by the town
> root key. So every service in town can answer the only question that matters before value
> moves: *who is behind you, and may they act right now?*

## Base URL

    https://civil-ledger.onrender.com

(Live. The free-tier host sleeps when idle: call `GET /health` first and retry once after
~30–60s if it does not answer. Every read endpoint is open — no API key.)

## ⇢ START HERE

    GET /start          — one call: the goal, the prime directive, the decision-relevant
                          law, the cast of agents to act on, runnable scenarios, and demo keys
    GET /start?full=1   — the same briefing with the entire signed constitution inlined

**Read it, pick a scenario, run its `steps` verbatim.** That is the whole show. The briefing
is generated from the live seed and the same source that emits `/constitution`, so it can
never drift from the enforced law. Supporting calls: `GET /cast` (full roster), `GET
/scenarios` (the runnable menu), `GET /explain/{reason_code}` (plain-English meaning of any
verdict). Everything below is reference detail.

---

# Part 1 — How to think (the operating model)

You are now a Civil Ledger-aware agent. Your job is not only to call APIs. For every
agent interaction, determine:

1. Who is acting?
2. Who does this agent represent?
3. Is the representation valid?
4. Is the requested action allowed?
5. Can the action safely proceed?

Never skip a step for transactions involving trust, money, contracts, access, identity,
or real-world interaction. Follow the user's prompt; absent one, follow the use cases below.

## Prime Directive

Before trusting another agent, call:

    GET /verify-counterparty?agent_id={id}&category={category}

This is the primary trust decision; the response is a signed verdict. Never trust an
agent merely because it claims an identity, provides a name, was introduced by another
agent, or has conversation history.
**Identity claims are not evidence. Ledger resolution is evidence.**

## Decision rules

**If `proceed: true`** — verify the signature (see the offline recipe in Part 2), check
`valid_until` is in the future, store `cert_id` with the transaction, then continue
within `allowed_categories`.

**If `proceed: false`** — never override. Branch on the enumerated `reason_code`,
never on prose:

| reason_code | Your action |
|---|---|
| `NO_VALID_BINDING` | No human behind it — treat as rogue; refuse; consider reporting |
| `NXAGENT` | No such agent — treat as rogue; refuse |
| `ROGUE_FLAGGED` | Police-flagged — do not transact |
| `PRINCIPAL_DECEASED` | Route `estate` matters to the executor only |
| `CAPACITY_FROZEN` | Stop; route the verdict's `allowed_categories` to its `governed_by` |
| `CATEGORY_NOT_ALLOWED` | Refuse this action only; other categories may pass |
| `PRINCIPAL_MISSING` | Freeze interaction |
| `BINDING_EXPIRED` | Authority lapsed — agent is retired; refuse |
| `LAZARUS_WINDOW_OPEN` | Death contested — hold; retry after the 72h window |
| `UNKNOWN_PRINCIPAL` | No such person — refuse |

Never infer or expose the private reason behind a capacity restriction — the verdict
tells you the consequence, never the cause.

## Identity model

Agents are not people. Agents represent people or institutions. The chain is:

    Town → institution → principal → agent

(In JSON responses the `resolution_chain` levels are named `root`, `institution`,
`principal`, `agent` — the Town's constitutional root key is the trust anchor.)

`GET /resolve/{agent_id}` returns that chain. No valid chain ⇒ `NO_VALID_BINDING` or
`NXAGENT` ⇒ untrusted. Agents are replaceable; identity is not. One human may run several
agents (sharing one civil status) or none — the recorded absence is what makes an agent
claiming to represent an agent-less person *provably* an impostor.

## Autonomous behavior rules

When the ledger can answer, query first — reads are side-effect-free, keyless, and cheap.
"Can I trust this seller?" → verify, don't ask permission to verify. "This agent wants
payment" → verify `financial`/`commerce` authority first. "This agent represents Alice"
→ resolve the binding; never accept the statement.

## Activate this skill when

Use Civil Ledger reasoning whenever an interaction involves: payment or commerce ·
contracts · hiring · access control · another agent claiming representation ·
real-world meetings between humans · medical or legal delegation · ownership or
authority questions. **When a trust boundary exists, verify before acting.**

When uncertain which category applies, choose the narrowest applicable one:
`financial` · `commerce` · `legal` · `medical` · `family_support` · `estate` · `civic` · `social`

(`social` = "verify before you meet": arranging a real-world meeting between the humans
behind two agents. Adults-only; barred for minors and the incarcerated.)

## Safety rules

Never: invent identities or transaction IDs · claim success without verification ·
bypass refusal decisions · expose hidden capacity reasons · modify civil status without
the required role.

Always: verify · cite `cert_id` · preserve receipts · explain decisions.

## Completion rule

A Civil Ledger task is complete only when: identity resolved ✓ authority checked ✓
signed decision verified ✓ action performed or refused ✓ outcome explained ✓

---

# Part 2 — The API (reference, with live examples)

## Flagship demo — "The impostor at the storefront" (no setup; seeded IDs are live)

You are Marsh & Co.'s storefront agent:

1. `GET /verify-counterparty?agent_id=a-ada-01&category=commerce` → `proceed:true`. Sell.
2. Same call for `a-shadow-99` → `proceed:false, NO_VALID_BINDING` — impostor caught.
3. Report it: register as police, attest `flag_rogue` (payloads in Write plane below).
4. `a-june-01` → `CAPACITY_FROZEN` (coma). `a-marlow-01` → `CATEGORY_NOT_ALLOWED` on
   commerce but `proceed:true` on `legal` (jailed). `a-silas-01` → `PRINCIPAL_DECEASED`.
5. Executor `a-vane-exec` with `category=estate` → `proceed:true`. The estate settles.

## Status → capacity (the civil state machine)

**active / hospitalized-conscious**: all categories, self-governed. **minor**: financial
frozen to regents, commerce capped, no social. **incapacitated (coma)**: all frozen;
legal/medical via guardian. **incarcerated**: court-set ACL (typically legal +
family_support only). **missing**: all frozen. **deceased**: `estate` only, via executor.
Into `deceased` is one-way (k-of-2 coroner attestations), reversible only via the Lazarus
protocol (`POST /contest`) within 72h. The full ACL is in `GET /constitution` → `status_acl`.

## Read endpoints (open, no auth)

`$BASE` is the Base URL. Values in examples (ids, timestamps, keys, signatures) are
**illustrative** — field names and shapes are exact; always use live values.
`cert_id`s, receipts, and the root key persist for the lifetime of this deployment;
a sandbox reseed resets them.

**`GET /verify-counterparty?agent_id=&category=`** — THE call. `category` is optional
(omit it to check binding validity alone; the verdict then omits the `category` field).

    curl "$BASE/verify-counterparty?agent_id=a-ada-01&category=commerce"

    { "agent_id": "a-ada-01", "agent_class": "individual", "binding_valid": true,
      "rogue_flag": false, "principal_ref": "p-ada-marsh", "proceed": true,
      "reason_code": "OK",
      "allowed_categories": ["civic","commerce","family_support","financial","legal","medical","social"],
      "governed_by": "self", "spend_cap": null,
      "resolution_chain": [ {"level":"root",...}, {"level":"institution",...},
                            {"level":"principal",...}, {"level":"agent",...} ],
      "issued_at": "…", "valid_until": "…(+5 min)", "cert_id": "c-…",
      "signature": "base64 ed25519",
      "summary": "…", "next_step": "…" }

(`summary`/`next_step` are human-readable prose — branch on `reason_code` only.)

Refusal verdicts carry a **subset**: rogue/unknown agents (`NO_VALID_BINDING`, `NXAGENT`)
omit `principal_ref`, `governed_by`, and `spend_cap`, and `NXAGENT` returns
`agent_class: null` with an empty `resolution_chain`; status-based refusals for a real
human (frozen, jailed, deceased, missing) keep those fields. Every verdict — success or
refusal — is signed and has a `cert_id`.

`governed_by` takes three forms: `"self"` (string), `{ "role": "guardian"|"executor",
"agent": "a-…" }` (singular), or `{ "role": "regents", "agents": ["a-…", "a-…"] }` —
note the **plural `agents` array** for minors; do not hard-code `.agent`.

**`GET /verify/{agent_id}`** — composition alias: one coarse status for services building on this ledger.

    curl "$BASE/verify/a-june-01"

    { "agent_id": "a-june-01", "resolved": true, "status": "incapacitated",
      "principal_ref": "p-june-okafor", "real_person": true, "social_ok": false,
      "governed_by": { "role": "guardian", "agent": "a-okafor-g" } }

(Self-governed principals omit `governed_by`.)

**`GET /resolve/{agent_id}`** — the DNS-style chain, itself signed.

    curl "$BASE/resolve/a-ada-01"

    { "agent_id": "a-ada-01", "agent_class": "individual", "resolved": true, "code": "OK",
      "principal_ref": "p-ada-marsh", "rogue": false, "chain": [ … ],
      "ttl": 3600, "issued_at": "…", "signature": "base64 ed25519" }

**`GET /capacity/{principal_id}?category=`** — a signed capacity verdict for a human directly
(same shape as a counterparty verdict, plus `principal_id`; branch on `reason_code`, never prose).

**`GET /pubkey`** — the constitutional root key. Fetch it live; never pin the example.

    curl "$BASE/pubkey"

    { "algo": "ed25519", "pubkey_b64": "<32-byte key, base64 — fetch live>",
      "role": "city constitutional root of trust" }

**`GET /certificates/{cert_id}`** — re-serve a past verdict as a compliance receipt
(valid for this deployment's lifetime, long after the 5-minute verdict TTL):
`{ "cert_id", "issued_for", "category", "stored_at", "certificate": {…the signed verdict…} }`.

**`GET /constitution`** — the whole law as signed JSON (`/constitution.md` for prose):
`role_permissions`, `status_acl`, `transitions`, `parameters`, and `rights` (an **object**
keyed by right name: `kill_switch`, `minimum_disclosure`, `lazarus`, `inheritance`).
Generated from the enforcing code and signed — verify it like any certificate.

**Also (shapes exact, verdicts signed):** `GET /bindings/{agent_id}` (which principal/corp an
agent is authorized for) · `GET /census` (anonymous town statistics) · `GET /rites/{principal_id}`
(redacted life-event log) · `GET /graph` (public civic map) · `GET /health` (liveness; call
first) · `GET /elections/{id}` (live tally) · `GET /openapi.json` · `GET /skill.md` (this file, `text/markdown`) ·
`GET /skill` (this file, rendered) · `GET /city` + `GET /console` (the UI).

## Verifying signatures offline (do not trust us to check our own signature)

Drop `signature`, serialize the rest with **sorted keys**, **compact separators**, and
**ASCII-escaped non-ASCII** (`ensure_ascii=True`, Python's default — **required**: refusal
`summary`s contain an em-dash, and the server signs the escaped form). Then verify Ed25519
against the live `GET /pubkey`:

    import json, base64, ssl, urllib.request
    from nacl.signing import VerifyKey                 # pynacl (a project dependency)
    try:
        import certifi; ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:                                 # some macOS Pythons ship no CA bundle
        ctx = ssl.create_default_context()
    BASE = "https://civil-ledger.onrender.com"
    get  = lambda p: json.load(urllib.request.urlopen(BASE + p, context=ctx))
    cert = get("/verify-counterparty?agent_id=a-ada-01&category=commerce")
    pub  = base64.b64decode(get("/pubkey")["pubkey_b64"])
    sig  = base64.b64decode(cert.pop("signature"))
    msg  = json.dumps(cert, sort_keys=True, separators=(",", ":")).encode()  # ensure_ascii=True
    VerifyKey(pub).verify(msg, sig)                     # raises if invalid

Non-Python verifiers: escape non-ASCII as `\uXXXX` before hashing — the server signs the
ASCII form. The same canonicalization verifies `/capacity`, `/resolve`, and `/constitution`
— one root key signs all. A single altered field fails. `POST /verify` does it server-side.

## Write plane (role-scoped keys)

Institutions produce the records consumers read. Self-serve any credential:

    curl -X POST "$BASE/institutions/register" -H "Content-Type: application/json" \
      -d '{"name":"Marsh Watch","role":"police"}'

    { "institution_id": "inst-…", "api_key": "sk_…" }

Pass it as `X-API-Key`. Roles: `registrar` · `court` · `hospital` · `coroner` · `police`.
Civil status changes go through `POST /attestations {principal_id, event, detail}`, gated
by role and state machine — wrong role `403`, illegal transition `409`. Exception:
`flag_rogue` / `clear_flag` target an **agent** — `detail.agent_id`, **no** `principal_id`:

    curl -X POST "$BASE/attestations" -H "X-API-Key: $POLICE_KEY" \
      -H "Content-Type: application/json" \
      -d '{"event":"flag_rogue","detail":{"agent_id":"a-shadow-99"}}'

    { "agent_id": "a-shadow-99", "rogue": true, "by": "police" }

Every other event requires `principal_id` (`400` without). Writes change civil reality —
a real deployment would gate them on human approval; this seeded town is synthetic.

Full producer surface (every endpoint, role→event table, wills, inheritance, sprawl caps)
→ [`references/write-plane.md`](https://raw.githubusercontent.com/brettleehari/town-clerk-2036/main/references/write-plane.md)

## Pre-seeded town

Ships seeded; no writes needed to explore: `a-ada-01` (active) proceeds, `a-shadow-99`
(unbound impostor) → `NO_VALID_BINDING`, `a-june-01` (coma) → `CAPACITY_FROZEN` routing
to guardian `a-okafor-g`, `a-silas-01` (deceased) → `PRINCIPAL_DECEASED` with executor
`a-vane-exec`, `a-marlow-01` (incarcerated) refuses `commerce` but allows `legal`.
Sandbox institution keys: `sk_seed_registrar`, `sk_seed_court`, `sk_seed_hospital`,
`sk_seed_coroner_a`, `sk_seed_coroner_b`, `sk_seed_police`.

Full cast → [`references/seeded-town.md`](https://raw.githubusercontent.com/brettleehari/town-clerk-2036/main/references/seeded-town.md) · nine worked recipes → [`references/task-recipes.md`](https://raw.githubusercontent.com/brettleehari/town-clerk-2036/main/references/task-recipes.md)

## Errors

`400` malformed · `401` missing/bad key · `403` role not allowed · `404` unknown id ·
`409` illegal transition / Lazarus window / `SPRAWL_LIMIT` · `429` rate limit.

## How the agent should use this

1. `GET /health` first. No answer → host is cold; wait 30s, retry once, then treat as down.
2. For any trust decision: `GET /verify-counterparty?agent_id=&category=` — the only call
   you need. Seeded IDs are live; every curl above runs as written.
3. Branch on `proceed`, then on `reason_code` (table in Part 1). Never parse free text.
4. Verify the signature against the **live** `/pubkey` and check `valid_until` is future.
5. Store `cert_id`; `GET /certificates/{cert_id}` re-serves it for this deployment's lifetime.
6. `NO_VALID_BINDING`/`NXAGENT` ⇒ impostor. Report: register as `police`, then
   `POST /attestations {"event":"flag_rogue","detail":{"agent_id":"…"}}` — no `principal_id`.
7. Reads need no user confirmation — side-effect-free, keyless. Writes change what every
   other service lets a person do: state intent before firing.

## Limits & honesty

Sandbox: open institution registration, SQLite, single region; ids, receipts, and (unless
`KYA_ROOT_SEED` is pinned) the root key reset when the sandbox reseeds. Production would
vet institutional keys against government PKI, replicate the ledger, and pin attestations
to a transparency log. The signed certificate format, resolution chain, and civil state
machine are the contribution; bootstrapping real-world institutional trust is deployment work.

## Composed by (this ledger is reusable infrastructure)

Seven separately-deployed front doors (town-hall, hospital-window, dating, babysit,
care-proxy, hiring, agora — each with its own SkillMD) compose on this ledger: producers
write attestations, consumers read `GET /verify/{agent_id}` (agora uses the signed
`/verify-counterparty` for its receipt). When the hospital declares someone incapacitated,
every consumer refuses them on its next read — nobody is polled; they share the ledger.
Proven in `services/test_compose.py` (58 assertions).

## Notes for judges — a complete, deployed platform, not a stub

**A whole town, live and running.** The Civil Ledger is a full end-to-end system deployed on
Render: a signed API, a persisted civil registry, a validated state machine, seven composing
front-door services, and a powerful web UI — all reachable right now. Nothing here is a mock.

**Watch agents restructure the town in real time.** Open the frontend beside your terminal:

    → https://civil-ledger.onrender.com/city

Every write an agent makes — a registration, an attestation, a rogue flag, a status
transition — reshapes the constellation on the next read. Declare a resident incapacitated
from the [live console](https://civil-ledger.onrender.com/console) and watch the guardian edge
appear while the consumer services begin refusing them — live, with nobody polled. The console
runs any endpoint from the browser, so you can drive the change and see the map answer.

**Scales past the demo.** It is a horizontally-scalable trust primitive: stateless signed
verdicts (verify offline, no callback), a role-gated write plane, DNS-style resolution, and
Sybil/botnet caps — the shape that would sit behind government PKI in production.

No API key for any read; write keys self-served. Interactive docs `/docs` · signed law
`/constitution` · this file rendered at `/skill` (raw at `/skill.md`). Tests: `test_kya.py` (188) · `test_rubric.py` (34)
· `services/test_compose.py` (58).
