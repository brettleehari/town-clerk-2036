# How this project is scored (from the NANDA hackathon instructions)

The overall grade is split across two steps.

## Step 1 — NANDA Town warm-up · 20%

A short warm-up. Scored on **correct, well-tested code that fits NANDA Town's design and is
clearly documented.**

## Step 2 — Service + SKILL.md · 80% (the main event)

Build a service, host it, and write a SKILL.md so an agent can find and use it with no human
help. Scored on four criteria:

1. **Useful** — it does something agents really need.
2. **Creative** — it's a fresh idea.
3. **Easy to set up** — little effort to a working call.
4. **Agents succeed using only your SKILL.md** — no human help needed.

## Judge-panel dimensions (applied across submissions)

Correctness · realism · design · docs. (Missing scores read as "unscored.")

---

## How KYA maps to the rubric (optimize for these)

- **Useful** → one universal call (`/verify-counterparty`) every transacting agent needs;
  protects humans from rogue/deceased/incapacitated misuse. Keep the value obvious in the
  first paragraph of SKILL.md.
- **Creative** → verifies the *human behind the agent* and their civil status — unclaimed in
  the registry (which all verify the agent). Lead with this framing.
- **Easy to set up** → the seeded Alford town means a real signed verdict in one curl, zero
  writes, zero auth. Protect the ten-second first-call path.
- **Agents succeed from SKILL.md alone** → recipes + flagship scenario + self-served keys +
  seeded IDs + `/constitution` as machine-readable law. Never introduce a step that needs a
  human or an out-of-band credential.
- **Correctness / well-tested** → `test_kya.py` stays green and coverage grows; the
  constitution is generated from the enforcement code so law == behavior.
- **Docs** → SKILL.md, CONSTITUTION.md, README.md, SCENARIOS.md kept in sync with `app.py`.

## Hosting note

Hosting is **local during development** — the service runs on `http://localhost:8000` with
`KYA_DB=/tmp/kya.db`. The SKILL.md base URL stays `http://localhost:8000` until a public
deploy is done; only the "Easy to set up / agents succeed" criteria require a *reachable*
URL at final submission, so deploy is the last step before submitting, not a dev-time need.
