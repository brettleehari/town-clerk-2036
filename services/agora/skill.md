---
name: agora
user-invocable: true
description: >
  The marketplace of a 2036 agent-native town, and the one door that hands back proof. Before
  goods ship or escrow releases, it gets a cryptographically signed verdict on the buyer's
  human from the town's Civil Ledger and returns a certificate id — a compliance receipt any
  third party can re-verify against the ledger's root key, long after the sale settles. The
  ledger authorizes the category; the marketplace enforces the amount (a minor's spend cap).
  Use when the user says "can I sell to this buyer", "verify a buyer before shipping",
  "release escrow", "is this purchaser legitimate", "check the buyer's standing", or "get a
  compliance receipt for this sale".
---

# agora — verify before you sell

Complete a sale to another agent safely. Before goods ship or escrow releases, this service
gets a **cryptographically signed verdict** on the buyer from the town's Civil Ledger — a
compliance receipt the seller can re-verify at any time, long after the sale settles.

> In 2036, deals close between agents, not people — and an agent can *say* anything. agora is
> the town marketplace's escrow desk: it never takes the buyer's word, it asks the **Civil
> Ledger** whether the human behind the buyer's agent may lawfully transact in `commerce`
> right now, and it keeps the **signed verdict** as the receipt. `proceed` authorizes the
> *category*; agora enforces the *amount* — a minor may buy, but only up to the spend cap
> their regents set. Every sale here is *auditable*, not merely *authorized*.

## Base URL

    https://agora-egpi.onrender.com

(Live. Free-tier hosts sleep when idle: call `GET /health` first and retry once after
~30-60s if it does not answer. Every read is open — no API key.)

## What it does

Given a seller agent id, a buyer agent id, and an amount, it asks the Civil Ledger for a
signed, category-scoped verdict on the buyer for the `commerce` category. The sale proceeds
only if the ledger says `proceed`. On success you get back a `certificate_id` — the id of the
signed verdict, re-verifiable against the ledger's public key forever.

Refusals carry the ledger's machine `reason_code` alongside a plain-language reason:

| Buyer's situation | `reason_code` |
|---|---|
| deceased | `PRINCIPAL_DECEASED` |
| incarcerated (no commerce right) | `CATEGORY_NOT_ALLOWED` |
| incapacitated (coma) | `CAPACITY_FROZEN` |
| orphaned / unrooted agent | `NO_VALID_BINDING` |
| no such agent | `NXAGENT` |
| flagged rogue by police | `ROGUE_FLAGGED` |
| a minor over their spend cap | `SPEND_CAP_EXCEEDED` |

## Endpoints

### POST /can-i-sell

Get a signed verdict on the buyer before value moves.

    curl -X POST https://agora-egpi.onrender.com/can-i-sell \
      -H "Content-Type: application/json" \
      -d '{"seller_agent":"a-store-01","buyer_agent":"a-ada-01","amount":49.99}'

    { "sell": true, "reason_code": "OK", "amount": 49.99,
      "seller_agent": "a-store-01", "buyer_agent": "a-ada-01",
      "certificate_id": "c-2440b5c0",
      "note": "signed verdict from the Civil Ledger; re-verify against its /pubkey" }

A refusal carries a stable machine `reason_code` — branch on it, not on the prose:

    { "sell": false, "reason_code": "PRINCIPAL_DECEASED",
      "reason": "the buyer is deceased; their estate must transact instead",
      "buyer_agent": "a-silas-01" }

### GET /health

Liveness. Call this first; a cold host may not answer for ~30s.

    curl https://agora-egpi.onrender.com/health

    { "ok": true, "service": "agora", "ledger": "https://civil-ledger.onrender.com" }

### GET /skill.md

Re-serves this file, always in sync with the running deployment. Served as `text/markdown`
(not JSON) — a rendered, human-readable view is at `GET /skill`.

    curl https://agora-egpi.onrender.com/skill.md

    ---
    name: agora
    ...

## How the agent should use this

1. Call `GET /health` first. If it does not answer, the host is cold — wait 30 seconds and
   retry once before treating the service as down.
2. Before shipping or releasing escrow, `POST /can-i-sell` with both agent ids and the amount.
3. If `sell` is true, complete the sale and store the `certificate_id` with the order.
4. If `sell` is false, cancel and relay `reason` to your human. Branch on `reason_code`,
   never on the prose — the codes are stable, the sentences are not.
5. To audit a past sale, fetch `GET /certificates/{certificate_id}` from the Civil Ledger and
   check its signature against the ledger's `/pubkey`. Neither the seller nor agora can forge
   one, and a single altered field makes verification fail.
6. `POST /can-i-sell` is a read: it returns a verdict and moves nothing. Calling it is free.

   **Completing the sale is not.** This service authorizes; you settle. Before value moves —
   goods shipped, escrow released — confirm with your human. In this synthetic town nothing
   ships and no money changes hands, but the verdict is designed for the case where it does.

## The receipt — what makes agora different

Every other front door in this town tells you *yes* or *no*. agora hands you **proof**. The
`certificate_id` names an Ed25519-signed verdict issued by the Civil Ledger's constitutional
root key. Neither agora nor the seller can forge or edit one, and a third party can check it
without trusting either. That makes a sale here *auditable*, not merely *authorized*.

Audit any past sale in two calls — no key, any time, long after the 5-minute TTL lapses:

    # 1) re-fetch the exact signed verdict that authorized the sale
    curl https://civil-ledger.onrender.com/certificates/c-2440b5c0

    { "cert_id": "c-2440b5c0", "issued_for": "a-ada-01", "category": "commerce",
      "stored_at": "2026-07-09T21:54:37Z", "certificate": { ...the signed verdict... } }

    # 2) check its signature against the town's root key
    curl -X POST https://civil-ledger.onrender.com/verify \
      -H "Content-Type: application/json" -d '{"cert": { ...the certificate... }}'

    { "valid": true }

Alter a single field of that certificate — flip `proceed` to `false`, bump the amount — and
step 2 returns `{ "valid": false }`. The receipt cannot be quietly rewritten after the fact.

## Seeded buyers (no writes needed)

`a-ada-01` sells · `a-silas-01` (deceased) `PRINCIPAL_DECEASED` · `a-marlow-01` (jailed)
`CATEGORY_NOT_ALLOWED` · `a-june-01` (coma) `CAPACITY_FROZEN` · `a-shadow-99` (impostor)
`NO_VALID_BINDING`. `a-tam-01` is a minor: he may buy, but only up to the spend cap his
regents set (50) — above it you get `SPEND_CAP_EXCEEDED` and the regents to ask.

## Composes

This service is a thin front door. Its backend calls the **Civil Ledger** (KYA — Know Your
Agent), a separate NANDA Town submission, to verify the human or institution behind the buyer's agent:

  - Civil Ledger SKILL.md: `https://civil-ledger.onrender.com/skill.md`
  - Call used: `GET /verify-counterparty?agent_id={id}&category=commerce`
    → a signed cert `{ proceed, reason_code, cert_id, signature, resolution_chain, ... }`
  - Wired via the `LEDGER_URL` environment variable (swappable infrastructure).
  - Retries the ledger 4× with backoff to tolerate a cold-started host.

You, the agent, never call the ledger — you only call this service.

## Notes for judges

- No API key required.
- Interactive API docs at `/docs` (auto-generated OpenAPI).
- Source: this repo's `services/agora/`.
- Unlike the town's other consumers, agora uses the ledger's **signed** verdict rather than
  the coarse status alias — because money is moving and the merchant wants a receipt. The
  returned `certificate_id` resolves at the ledger's `/certificates/{id}` and verifies
  against `/pubkey`, so a sale's authorization is auditable by a third party.
