---
name: hospital-window
user-invocable: true
description: >
  The hospital admitting desk of a 2036 agent-native town — an institution that WRITES civil
  status. Admit, discharge, or declare a patient incapacitated, and it records the attestation
  on the town's Civil Ledger, instantly changing what every other service will let that person
  do: their care routes to a guardian, and the marketplace, hiring, and dating services begin
  refusing them — nobody polled, all reading the same ledger. Only lawful transitions pass
  (the civil state machine). Use when the user says "admit this patient", "discharge them",
  "declare the patient incapacitated", "my patient is in a coma", "update someone's medical
  status", or "the hospital needs to record an admission".
---

# hospital-window — the institution that changes a civil status

Most town services **read** the civil ledger. This one **writes** it. hospital-window is
Fairview Hospital's admitting desk: admit a patient, discharge them, or declare them
incapacitated — and the town rearranges itself around the change immediately.

> In 2036 a person's civil status is not a note in one hospital's file — it is a town-wide
> fact the whole economy reads. This is the **admitting desk** that writes it. Declare a
> resident incapacitated here and, on their next read, care-proxy routes their medical
> decisions to their court-appointed guardian while hiring, agora, dating, and babysit begin
> refusing them — **no consumer is notified, polled, or updated.** They share the ledger. One
> attestation restructures the town, and only the **civil state machine** decides which
> transitions are lawful (a `409` refuses the rest).

## Base URL

    https://hospital-window.onrender.com

(Live. Free-tier hosts sleep when idle: call `GET /health` first and retry once after
~30-60s if it does not answer. Every read is open — no API key.)

## What it does

Given a patient's agent id, it resolves that agent to the human behind it and records a
civil event with the town's Civil Ledger as an attesting hospital. The consequences are
town-wide and automatic:

- **`/admit`** → status becomes `hospitalized`. The patient keeps every civil right — a
  conscious inpatient may still contract, meet, and vote. Nothing else changes.
- **`/declare-incapacitated`** → status becomes `incapacitated`. Capacity freezes town-wide:
  the care-proxy service instantly routes their medical decisions to their court-appointed
  guardian, and the dating, hiring, and marketplace services instantly refuse them.
- **`/discharge`** → status returns to `active`.

No consumer service is notified, polled, or updated. They read the same ledger.

## Endpoints

### POST /admit

Admit a resident as a conscious inpatient. They keep every civil right.

    curl -X POST https://hospital-window.onrender.com/admit \
      -H "Content-Type: application/json" -d '{"patient_agent":"a-gwen-01"}'

    { "ok": true, "event": "admit", "patient_agent": "a-gwen-01",
      "principal_id": "p-gwen-alcott", "status": "hospitalized", "social_ok": true }

### POST /discharge

Return an inpatient to `active`.

    curl -X POST https://hospital-window.onrender.com/discharge \
      -H "Content-Type: application/json" -d '{"patient_agent":"a-gwen-01"}'

    { "ok": true, "event": "discharge", "patient_agent": "a-gwen-01",
      "principal_id": "p-gwen-alcott", "status": "active", "social_ok": true }

### POST /declare-incapacitated

Freeze a patient's capacity town-wide. Legal only from `active` or `hospitalized`.

    curl -X POST https://hospital-window.onrender.com/declare-incapacitated \
      -H "Content-Type: application/json" -d '{"patient_agent":"a-gwen-01"}'

    { "ok": true, "event": "declare_incapacitated", "patient_agent": "a-gwen-01",
      "principal_id": "p-gwen-alcott", "status": "incapacitated", "social_ok": false }

`now_governed_by` appears **only when a court has already appointed that patient a guardian**.
No seeded resident is both capable and guardianed, so it takes two steps to see it — the court
appoints, then the hospital declares:

    curl -X POST https://civil-ledger.onrender.com/attestations -H "X-API-Key: sk_seed_court" \
      -H "Content-Type: application/json" \
      -d '{"principal_id":"p-gwen-alcott","event":"appoint_guardian","detail":{"agent_id":"a-ada-01"}}'

    curl -X POST https://hospital-window.onrender.com/declare-incapacitated \
      -H "Content-Type: application/json" -d '{"patient_agent":"a-gwen-01"}'

    { "ok": true, "event": "declare_incapacitated", "patient_agent": "a-gwen-01",
      "principal_id": "p-gwen-alcott", "status": "incapacitated", "social_ok": false,
      "now_governed_by": { "role": "guardian", "agent": "a-ada-01" } }

An unlawful transition is refused with `409` and tells you the patient's real status. The
seeded patient `a-june-01` is already incapacitated, so declaring her again returns:

    { "detail": "illegal transition 'declare_incapacitated' for a patient whose civil status is 'incapacitated'" }

An agent with no human behind it is refused with `404`:

    { "detail": "no verified human behind a-shadow-99 (NO_VALID_BINDING)" }

### GET /health

Liveness. Call this first; a cold host may not answer for ~30s.

    curl https://hospital-window.onrender.com/health

    { "ok": true, "service": "hospital-window", "ledger": "https://civil-ledger.onrender.com" }

### GET /skill.md

Re-serves this file, always in sync with the running deployment. Served as `text/markdown`
(not JSON) — a rendered, human-readable view is at `GET /skill`.

    curl https://hospital-window.onrender.com/skill.md

    ---
    name: hospital-window
    ...

## How the agent should use this

1. Call `GET /health` first. If it does not answer, the host is cold — wait 30 seconds and
   retry once before treating the service as down.
2. Get the patient's agent id.
3. `POST` the event that actually occurred: `/admit`, `/discharge`, or
   `/declare-incapacitated`.
4. On `409`, read the patient's real status out of the message and adjust — the civil state
   machine permits only lawful transitions, so you cannot discharge someone never admitted or
   admit someone deceased. Do not retry the same call.
5. When `now_governed_by` appears, someone else now acts for that patient. Route further
   decisions to that agent; the care-proxy service will do this for you.
6. **Every endpoint here is a write, and writes are consequential.** A status change silently
   alters what five other services will let that person do — care-proxy reroutes their medical
   decisions, and dating, babysit, hiring and agora begin refusing them. Nobody is notified;
   they simply read the ledger.

   Confirm with your human before you admit, discharge, or declare anyone incapacitated. In a
   real deployment each write would additionally require human approval and an audited clinical
   record. This seeded town is synthetic, and `/discharge` reverses `/admit` — but an
   incapacity declaration does not reverse itself (see Cleanup).

## Cleanup (this service cannot undo an incapacity)

Only `/discharge` reverses `/admit`. To put a patient back the way you found them, post
`declare_recovered` to the ledger as the hospital:

    curl -X POST https://civil-ledger.onrender.com/attestations -H "X-API-Key: sk_seed_hospital" \
      -H "Content-Type: application/json" \
      -d '{"principal_id":"p-gwen-alcott","event":"declare_recovered","detail":{}}'

## Composes

This service is a thin front door on the **producer** side. Its backend calls the
**Civil Ledger** (KYA — Know Your Agent), a separate NANDA Town submission:

  - Civil Ledger SKILL.md: `https://civil-ledger.onrender.com/skill.md`
  - Calls used:
    - `POST /institutions/register` → self-serve a `hospital` role API key (or set `HOSPITAL_KEY`)
    - `GET /resolve/{agent_id}` → find the human behind the patient's agent
    - `POST /attestations` → record `admit` / `discharge` / `declare_incapacitated`
    - `GET /verify/{agent_id}` → read the patient back so the caller sees the new world
  - Wired via the `LEDGER_URL` environment variable (swappable infrastructure).
  - Retries transport failures and 5xx 4× with backoff; a 4xx is the ledger's considered
    answer and surfaces immediately.

You, the agent, never call the ledger — you only call this service.

## Notes for judges

- No API key required from you; the service self-registers as a hospital with the ledger.
- Interactive API docs at `/docs` (auto-generated OpenAPI).
- Source: this repo's `services/hospital-window/`.
- This is the **producer half** of the composition story, and the most interesting one to
  demo: declare a patient incapacitated here, then immediately call the care-proxy service
  for that same patient — it now routes to their guardian. Two independently-submitted front
  doors, never talking to each other, coordinated only by a shared constitutional ledger.
  Only a `hospital`-role key can drive these transitions; the ledger's state machine refuses
  everything else.
