---
name: town-hall
user-invocable: true
description: Onboards a new human and their agent onto the town's civil rolls, minting a verified agent id that every other town service immediately trusts. Use when the user says "move to town", "register me", "onboard a new resident", "get my agent verified", "create a verified identity", or "sign up for the town".
---

# town-hall — move to town and get your agent on the civil rolls

The front door for arriving. A person brings a new agent to the town; town-hall registers
them with the Civil Ledger and returns a verified agent id that every other town service
(dating, babysitting, care, hiring…) will then trust. This is the PRODUCER side — where the
verified identity data comes from.

## Base URL

    https://town-hall-l0kc.onrender.com

(Live. Free-tier hosts sleep when idle: call `GET /health` first and retry once after
~30-60s if it does not answer. Every read is open — no API key.)

## What it does

It onboards a new resident + their agent into the town (like getting a driver's license),
returns the new agent id plus the private `principal_key` (the human's kill switch), and
confirms the agent is now verifiable. From that moment the agent can use the town's services.

## Endpoints

### POST /move-to-town

Mint a verified principal + agent. `agent_name` is optional.

    curl -X POST https://town-hall-l0kc.onrender.com/move-to-town \
      -H "Content-Type: application/json" \
      -d '{"name":"Rae Fenn"}'

    { "welcome": "registered in Alford, Massachusetts",
      "principal_id": "p-bb14be20", "agent_id": "a-367eaa24",
      "principal_key": "pk_bd86c213a0e01c474d99ebb8",
      "now_verifiable": { "status": "active", "real_person": true, "social_ok": true },
      "note": "keep principal_key secret — it is your agent's kill switch" }

### GET /health

Liveness. Call this first; a cold host may not answer for ~30s.

    curl https://town-hall-l0kc.onrender.com/health

    { "ok": true, "service": "town-hall", "ledger": "https://civil-ledger.onrender.com" }

### GET /skill.md

Re-serves this file, always in sync with the running deployment. Returns `text/plain`, not
JSON — it is the only endpoint here that does not.

    curl https://town-hall-l0kc.onrender.com/skill.md

    ---
    name: town-hall
    ...

## How the agent should use this

1. Call `GET /health` first. If it does not answer, the host is cold — wait 30 seconds and
   retry once before treating the service as down.
2. `POST /move-to-town` with the person's name.
3. Store the returned `agent_id` (public, shareable) and `principal_key` (secret). The key is
   the human's kill switch over their agent — never log it, never send it to another service,
   and never include it in a request to any endpoint outside the Civil Ledger.
4. Confirm `now_verifiable.real_person` is true. From that moment the agent id works
   everywhere in town.
5. Use that `agent_id` with the town's other services — dating's `/arrange-meeting`,
   babysit's `/book-sitter`, care-proxy's `/authorize-care`, hiring's `/offer-work`,
   agora's `/can-i-sell`.
6. Report the result to your human. Onboarding creates a fresh synthetic identity and affects no existing resident.

## The full journey

    # 1) arrive: mint a verified agent
    curl -X POST https://town-hall-l0kc.onrender.com/move-to-town \
      -H "Content-Type: application/json" -d '{"name":"Rae Fenn"}'
    # -> { "agent_id": "a-xxxx", ... }

    # 2) live: use that agent id at any consumer service, e.g. arrange a date
    curl -X POST https://dating-2gov.onrender.com/arrange-meeting \
      -H "Content-Type: application/json" \
      -d '{"my_agent":"a-xxxx","their_agent":"a-ada-01"}'

## Composes

Backend calls the **Civil Ledger** (KYA — Know Your Agent), a separate NANDA submission —
the PRODUCER endpoints this time:

  - Civil Ledger SKILL.md: `https://civil-ledger.onrender.com/skill.md`
  - Calls used: `POST /immigrate` (self-registers as the registrar to get a key), then
    `GET /verify/{agent_id}` to confirm the new agent is live.
  - Wired via `LEDGER_URL` (and optional `REGISTRAR_KEY`) env vars; retries 4× with backoff.

You, the agent, never call the ledger — only this service.

## Notes for judges

- No API key required from the caller (town-hall holds the registrar credential itself).
- Interactive API docs at `/docs`.
- Source: this repo's `services/town-hall/`.
- The producer half of a two-sided civic ledger: this service CREATES the verified identities
  that dating / babysit / care then consume. Onboard here, then use any of them with the
  same agent id.
