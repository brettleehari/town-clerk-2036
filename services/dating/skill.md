---
name: dating
user-invocable: true
description: Arranges a real-world date between two matched agents' humans after verifying both are real, living, consenting adults, disclosing nothing else about either person. Use when the user says "set up a date", "arrange a meeting with my match", "is my match a real person", "verify someone before I meet them", "schedule a first date", or "check this match for a catfish".
---

# dating — verify before you meet

Arrange a real-world date between two matched people, safely. When two agents want to put
their humans in a room together, this service verifies BOTH are real, living, consenting
adults before proposing a time — and reveals nothing else about either person.

## Base URL

    https://dating-2gov.onrender.com

(Live. Free-tier hosts sleep when idle: call `GET /health` first and retry once after
~30-60s if it does not answer. Every read is open — no API key.)

## What it does

Given your agent id and your match's agent id, it checks both with the town's Civil Ledger
on the `social` category (real, living, consenting adult — not a minor, not incarcerated,
not an orphaned/rogue agent), then has the two agents exchange calendars and proposes a
mutually free time. If either party can't consent to meet, it refuses without saying why.

## Endpoints

### POST /arrange-meeting

Verify both humans and propose a mutually free time.

    curl -X POST https://dating-2gov.onrender.com/arrange-meeting \
      -H "Content-Type: application/json" \
      -d '{"my_agent":"a-ada-01","their_agent":"a-owen-01"}'

    { "arranged": true, "both_verified": true, "proposed_time": "Sat 12pm",
      "note": "both agents verified as real consenting adults; nothing else disclosed" }

On refusal the reason is deliberately generic — minimum disclosure protects the other person:

    { "arranged": false, "reason": "the other party cannot meet right now", "who": "match" }

### GET /health

Liveness. Call this first; a cold host may not answer for ~30s.

    curl https://dating-2gov.onrender.com/health

    { "ok": true, "service": "dating", "ledger": "https://civil-ledger.onrender.com" }

### GET /skill.md

Re-serves this file, always in sync with the running deployment. Returns `text/plain`, not
JSON — it is the only endpoint here that does not.

    curl https://dating-2gov.onrender.com/skill.md

    ---
    name: dating
    ...

## How the agent should use this

1. Call `GET /health` first. If it does not answer, the host is cold — wait 30 seconds and
   retry once before treating the service as down.
2. Collect your human's agent id and the match's agent id.
3. `POST /arrange-meeting` with both ids.
4. If `arranged` is true, tell your human the `proposed_time`.
5. If `arranged` is false, tell your human it could not be arranged. Do not speculate about
   the other person — the service withholds the reason on purpose. Do not retry with the
   same pair; the refusal is about civil status, not timing.
6. Report the result to your human. Arranging a meeting is a verification plus a proposed time — nothing is booked on
   anyone's behalf, so an agent can call this freely.

## Try it (seeded town)

    curl -X POST https://dating-2gov.onrender.com/arrange-meeting \
      -H "Content-Type: application/json" \
      -d '{"my_agent":"a-ada-01","their_agent":"a-owen-01"}'      # two active adults -> arranged
    # a-lena-01 is also an active adult, but her calendar never overlaps Ada's:
    #   -> { "arranged": false, "reason": "no mutually free time this week", "both_verified": true }
    # a-tam-01 (a minor) or a-marlow-01 (incarcerated) -> refused, no reason given

## Composes

This service is a thin front door. Its backend calls the **Civil Ledger** (KYA — Know Your
Agent), a separate NANDA Town submission, to verify the humans behind the agents:

  - Civil Ledger SKILL.md: `https://civil-ledger.onrender.com/skill.md`
  - Call used: `GET /verify/{agent_id}` → `{ status, real_person, social_ok, ... }`
  - Wired via the `LEDGER_URL` environment variable (swappable infrastructure).
  - Retries the ledger 4× with backoff to tolerate a cold-started host.

You, the agent, never call the ledger — you only call this service.

## Notes for judges

- No API key required.
- Interactive API docs at `/docs` (auto-generated OpenAPI).
- Source: this repo's `services/dating/`.
- Demonstrates the composition pattern: a catchy front door over reusable civic
  infrastructure, with minimum-disclosure privacy preserved at the app layer.
