---
name: care-proxy
user-invocable: true
description: Decides who may make a medical decision for a patient, routing to the court-appointed guardian when the patient is incapacitated and cannot consent. Use when the user says "authorize care", "who can consent for this patient", "approve a medical decision", "my patient is in a coma", "find the healthcare proxy", or "can I make this decision for them".
---

# care-proxy — who may make a care decision for a patient

Authorize medical decisions safely. Given the agent that wants to act and the patient it
wants to act for, this service returns authorize / route-to-guardian / deny — enforcing that
a capable patient acts for themselves, and an incapacitated patient's decisions route to
their appointed guardian.

## Base URL

    https://care-proxy.onrender.com

(Live. Free-tier hosts sleep when idle: call `GET /health` first and retry once after
~30-60s if it does not answer. Every read is open — no API key.)

## What it does

It asks the town's Civil Ledger for the patient's civil standing and who governs them, then:
- patient governed by someone else → only that proxy may act, and it tells you who:
  a **guardian** for an incapacitated adult, the **regents** for a minor;
- patient capable and self-governing (active/hospitalized) → only their own agent may authorize;
- patient deceased/missing → no care authorization.

## Endpoints

### POST /authorize-care

Decide whether the requesting agent may make a care decision for the patient.

    curl -X POST https://care-proxy.onrender.com/authorize-care \
      -H "Content-Type: application/json" \
      -d '{"requesting_agent":"a-okafor-g","patient_agent":"a-june-01"}'

    { "authorized": true, "acting_as": "guardian", "patient_status": "incapacitated",
      "note": "patient is governed by guardian; you are one of them" }

If the wrong agent asks, the refusal names the right one:

    { "authorized": false, "patient_status": "incapacitated",
      "reason": "patient is governed by guardian; only they may authorize care",
      "route_to": "a-okafor-g" }

A **minor** is governed by their regents, so `route_to` is a list — either parent may act, and
the child may not authorize their own care:

    curl -X POST https://care-proxy.onrender.com/authorize-care \
      -H "Content-Type: application/json" \
      -d '{"requesting_agent":"a-holt-mom","patient_agent":"a-tam-01"}'

    { "authorized": true, "acting_as": "regents", "patient_status": "minor",
      "note": "patient is governed by regents; you are one of them" }

A capable patient acts for themselves:

    { "authorized": true, "acting_as": "self",
      "note": "patient is capable and is acting for themselves" }

### GET /health

Liveness. Call this first; a cold host may not answer for ~30s.

    curl https://care-proxy.onrender.com/health

    { "ok": true, "service": "care-proxy", "ledger": "https://civil-ledger.onrender.com" }

### GET /skill.md

Re-serves this file, always in sync with the running deployment. Returns `text/plain`, not
JSON — it is the only endpoint here that does not.

    curl https://care-proxy.onrender.com/skill.md

    ---
    name: care-proxy
    ...

## How the agent should use this

1. Call `GET /health` first. If it does not answer, the host is cold — wait 30 seconds and
   retry once before treating the service as down.
2. Collect your agent id (`requesting_agent`) and the patient's agent id.
3. `POST /authorize-care`.
4. If `authorized` is true, proceed with the care decision.
5. If the response carries `route_to`, you are not the right party. Hand the decision to
   that guardian agent — do not retry as yourself, and do not treat this as an error.
6. If `authorized` is false with no `route_to`, no one may authorize care through this
   service (the patient is deceased or missing). Stop and tell your human.
6. Report the result to your human. This endpoint only reads civil standing and returns a routing decision — it changes
   nothing, so an agent can call it freely.

## Try it (seeded town)

    curl -X POST https://care-proxy.onrender.com/authorize-care \
      -H "Content-Type: application/json" \
      -d '{"requesting_agent":"a-okafor-g","patient_agent":"a-june-01"}'   # guardian -> authorized
    # requesting_agent a-june-01 (the comatose patient's own agent) -> routed to the guardian
    # patient_agent a-silas-01 (deceased) -> no care authorization

## Composes

Backend calls the **Civil Ledger** (KYA — Know Your Agent), a separate NANDA submission:

  - Civil Ledger SKILL.md: `https://civil-ledger.onrender.com/skill.md`
  - Call used: `GET /verify/{agent_id}` → status + `governed_by` (guardian/regents/executor).
  - Wired via `LEDGER_URL` env var; retries 4× with backoff for cold-started hosts.

You, the agent, never call the ledger — only this service.

## Notes for judges

- No API key required.
- Interactive API docs at `/docs`.
- Source: this repo's `services/care-proxy/`.
- Exercises the constitution's guardian-routing rule for incapacitated principals — a
  behavior no plain "is this agent real?" service can express.
