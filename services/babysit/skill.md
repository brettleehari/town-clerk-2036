---
name: babysit
user-invocable: true
description: Books a childcare sitter only after verifying the sitter is a real, present adult and that the booking parent is the child's registered guardian. Use when the user says "book a babysitter", "find a sitter for tonight", "is this sitter safe", "verify my babysitter", "check the sitter's background", or "can I leave my kid with this person".
---

# babysit — verify the sitter before you hand over your kid

Book a childcare sitter, safely. Before confirming a booking, this service verifies the
sitter's agent traces to a real, living adult in good standing — so you never leave a child
with an agent that ties to no real person, to a minor, or to someone incarcerated.

## Base URL

    https://babysit.onrender.com

(Live. Free-tier hosts sleep when idle: call `GET /health` first and retry once after
~30-60s if it does not answer. Every read is open — no API key.)

## What it does

Given a parent agent and a sitter agent (and optionally the child's agent), it checks the
sitter with the town's Civil Ledger on the `social` category. By the town constitution a
minor's agent and an incarcerated person's agent can never pass `social`, so unsafe sitters
are refused automatically. If a child agent is supplied, it also confirms the booker is one
of that child's registered guardians before booking.

## Endpoints

### POST /book-sitter

Verify the sitter (and the booker's guardianship, if a child is named) and book a time.

    curl -X POST https://babysit.onrender.com/book-sitter \
      -H "Content-Type: application/json" \
      -d '{"parent_agent":"a-holt-mom","sitter_agent":"a-lena-01","child_agent":"a-tam-01"}'

    { "booked": true, "sitter_verified": true, "time": "Fri 6pm",
      "note": "sitter verified as a real adult in good standing" }

An unsafe sitter is refused, and the reason names the sitter's civil status:

    { "booked": false, "reason": "sitter is not eligible to care for a child right now",
      "sitter_status": "incarcerated" }

A booker who is not the child's registered guardian is refused:

    { "booked": false, "reason": "you are not a registered guardian of this child" }

A verified sitter with no overlapping availability is not an error — try another sitter:

    { "booked": false, "reason": "no mutually free time this week", "sitter_verified": true }

### GET /health

Liveness. Call this first; a cold host may not answer for ~30s.

    curl https://babysit.onrender.com/health

    { "ok": true, "service": "babysit", "ledger": "https://civil-ledger.onrender.com" }

### GET /skill.md

Re-serves this file, always in sync with the running deployment. Returns `text/plain`, not
JSON — it is the only endpoint here that does not.

    curl https://babysit.onrender.com/skill.md

    ---
    name: babysit
    ...

## How the agent should use this

1. Call `GET /health` first. If it does not answer, the host is cold — wait 30 seconds and
   retry once before treating the service as down.
2. Collect the parent's agent id and the sitter's agent id. Include `child_agent` whenever
   you know it — that is what triggers the guardianship check.
3. `POST /book-sitter`.
4. If `booked` is true, tell your human the `time`.
5. If `booked` is false, branch on the response rather than the prose. `sitter_verified: true`
   with "no mutually free time" means the sitter is safe but busy, so offer another sitter.
   Anything else means the sitter or guardianship check failed — do not retry that sitter.
6. Report the result to your human. The booking is a proposal against synthetic calendars — nothing is charged or
   dispatched, so an agent can call this freely.

## Try it (seeded town)

    curl -X POST https://babysit.onrender.com/book-sitter \
      -H "Content-Type: application/json" \
      -d '{"parent_agent":"a-holt-mom","sitter_agent":"a-lena-01","child_agent":"a-tam-01"}'
    # -> booked: true (registered guardian, safe adult sitter)
    # sitter_agent a-marlow-01 (incarcerated) or a-tam-01 (a minor) -> refused
    # parent_agent a-ada-01 with child_agent a-tam-01 -> refused, not that child's guardian

## Composes

Backend calls the **Civil Ledger** (KYA — Know Your Agent), a separate NANDA submission:

  - Civil Ledger SKILL.md: `https://civil-ledger.onrender.com/skill.md`
  - Calls used: `GET /verify/{agent_id}` for the sitter (and the child, when given).
  - Wired via `LEDGER_URL` env var; retries 4× with backoff for cold-started hosts.

You, the agent, never call the ledger — only this service.

## Notes for judges

- No API key required.
- Interactive API docs at `/docs`.
- Source: this repo's `services/babysit/`.
- Reuses the same civic infrastructure as dating and care-proxy, but exercises a
  different constitutional rule (the `social` bar on minors and the incarcerated) plus
  guardian verification.
