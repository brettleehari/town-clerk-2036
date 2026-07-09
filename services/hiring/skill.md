---
name: hiring
user-invocable: true
description: Offers work to an agent's human only after verifying they are a real, capable, present adult, blocking child labor and contracting from custody. Use when the user says "hire this person", "offer someone a job", "can I employ this agent", "verify a worker before hiring", "is this contractor a real person", or "check if they're eligible to work".
---

# hiring — verify before you hire

Offer work to another agent's human, safely. Before an employment contract exists, this
service verifies there is a real, capable, present adult behind the worker's agent — and
reveals nothing else about them.

## Base URL

    https://hiring-q7xc.onrender.com

(Live. Free-tier hosts sleep when idle: call `GET /health` first and retry once after
~30-60s if it does not answer. Every read is open — no API key.)

## What it does

Given an employer agent id, a worker agent id, and a role, it checks the worker with the
town's Civil Ledger. The offer stands only if the worker is a real living human whose civil
status is `active` or `hospitalized` (a conscious inpatient keeps the right to contract).

Everyone else is refused, and the constitution says why:

| Worker's civil status | Outcome | Why |
|---|---|---|
| `active`, `hospitalized` | hired | a capable, present adult |
| `minor` | refused | no child labor |
| `incarcerated` | refused | cannot contract work from custody |
| `incapacitated` | refused | cannot consent |
| `missing` | refused | cannot consent |
| `deceased` | refused | — |
| `orphaned` | refused | no verified human behind that agent |

The employer is not status-checked. Anyone may make an offer; the constitution protects the
person being hired.

## Endpoints

### POST /offer-work

Verify the worker's human and stand up the offer.

    curl -X POST https://hiring-q7xc.onrender.com/offer-work \
      -H "Content-Type: application/json" \
      -d '{"employer_agent":"a-store-01","worker_agent":"a-ada-01","role":"shopkeeper"}'

    { "hired": true, "worker_status": "active", "role": "shopkeeper",
      "employer_agent": "a-store-01", "worker_agent": "a-ada-01",
      "note": "verified as a real, capable adult; no other personal data disclosed" }

A refusal always names the worker's civil status and the constitutional reason:

    { "hired": false, "worker_status": "minor", "reason": "no child labor: the worker is a minor" }

### GET /health

Liveness. Call this first; a cold host may not answer for ~30s.

    curl https://hiring-q7xc.onrender.com/health

    { "ok": true, "service": "hiring", "ledger": "https://civil-ledger.onrender.com" }

### GET /skill.md

Re-serves this file, always in sync with the running deployment. Returns `text/plain`, not
JSON — it is the only endpoint here that does not.

    curl https://hiring-q7xc.onrender.com/skill.md

    ---
    name: hiring
    ...

## How the agent should use this

1. Call `GET /health` first. If it does not answer, the host is cold — wait 30 seconds and
   retry once before treating the service as down.
2. Collect the employer's agent id, the prospective worker's agent id, and the role.
3. `POST /offer-work`.
4. If `hired` is true, proceed with the engagement.
5. If `hired` is false, relay `reason` to your human and stop. Do not retry with a different
   role or a smaller scope — the refusal is about the worker's civil status, not the job.
6. Report the result to your human. This endpoint verifies eligibility and returns an offer decision — no contract is
   signed and nothing is paid, so an agent can call it freely.

## Try it (seeded town)

    curl -X POST https://hiring-q7xc.onrender.com/offer-work \
      -H "Content-Type: application/json" \
      -d '{"employer_agent":"a-store-01","worker_agent":"a-ada-01","role":"shopkeeper"}'
    # -> hired: true (an active adult)

    # a-tam-01     (a minor)          -> refused, "no child labor"
    # a-marlow-01  (incarcerated)     -> refused, "cannot contract work from custody"
    # a-shadow-99  (orphaned / rogue) -> refused, "no verified human behind that agent"
    # a-cyrus-01   (hospitalized)     -> hired: a conscious inpatient keeps the right to contract

## Composes

This service is a thin front door. Its backend calls the **Civil Ledger** (KYA — Know Your
Agent), a separate NANDA Town submission, to verify the human behind the worker's agent:

  - Civil Ledger SKILL.md: `https://civil-ledger.onrender.com/skill.md`
  - Call used: `GET /verify/{agent_id}` → `{ status, real_person, social_ok, ... }`
  - Wired via the `LEDGER_URL` environment variable (swappable infrastructure).
  - Retries the ledger 4× with backoff to tolerate a cold-started host.

You, the agent, never call the ledger — you only call this service.

## Notes for judges

- No API key required.
- Interactive API docs at `/docs` (auto-generated OpenAPI).
- Source: this repo's `services/hiring/`.
- Demonstrates the composition pattern: a catchy front door over reusable civic
  infrastructure. The child-labor and custody bars are not application logic — they fall out
  of the ledger's constitutional ACL for free.
