# KYA — Know Your Agent · Submission

**One line.** KYC for the agent economy: before any agent transacts with another, it asks
the Civil Ledger "is this counterparty real, and is its human able to act right now?" and
gets back an Ed25519-signed verdict.

## What it is

An agent-native **Town Constitution** (Alford, Massachusetts) served as an API. It verifies
the *human or institution behind an agent* and their real-world civil status — active, minor, hospitalized,
incapacitated, incarcerated, missing, deceased — before allowing a transaction. Agents
resolve DNS-style to a constitutional root of trust (unresolvable = rogue); verdicts are
signed with a 5-minute TTL; death needs k-of-2 coroner attestations with a 72h Lazarus
contest; wills transfer or retire an agent at death; residents immigrate (register like a
DL) and vote for City Council. The whole rulebook is generated from the enforcement code and
served, signed, at `/constitution`.

## Why it's novel

Every other entry in the registry verifies the *agent* — its identity, reputation, or
conformance. KYA verifies the *human or institution behind it* and their standing to act. That's unclaimed
ground, and it's the layer that money, voting, and licensing all have to call first.

## Base URL

`https://civil-ledger.onrender.com` — live. The UI is served same-origin at
[`/city`](https://civil-ledger.onrender.com/city) and the API console at
[`/console`](https://civil-ledger.onrender.com/console). SKILL.md is at
[`/skill.md`](https://civil-ledger.onrender.com/skill.md).

(Free tier: the host sleeps when idle. Call `GET /health` first and retry once after ~30–60s.)

## The composing town (seven front doors, each its own submission)

The ledger is reusable infrastructure. Seven separately-deployed services call it over HTTP;
a consuming agent reads only the front door's SkillMD and never learns the ledger exists.

| Service | Role | Live |
|---|---|---|
| town-hall | producer — onboard a human + agent | https://town-hall-l0kc.onrender.com |
| hospital-window | producer — admit / discharge / declare incapacitated | https://hospital-window.onrender.com |
| dating | consumer — `social`, verify before you meet | https://dating-2gov.onrender.com |
| babysit | consumer — `social` + guardianship | https://babysit.onrender.com |
| care-proxy | consumer — `medical`, guardian routing | https://care-proxy.onrender.com |
| hiring | consumer — capable-adult gate | https://hiring-q7xc.onrender.com |
| agora | consumer — `commerce`, signed compliance receipt | https://agora-egpi.onrender.com |

**The payoff:** hospital-window declares a resident incapacitated and notifies nobody.
care-proxy instantly routes their care to their guardian, while hiring, agora, dating and
babysit all begin refusing them. Independently-deployed services, never talking to each
other, coordinated solely by a shared constitutional ledger.

## Endpoint catalog

Reads (open, no auth): `/health` `/pubkey` `/constitution` `/constitution.md`
`/verify-counterparty` `/resolve/{agent_id}` `/capacity/{principal_id}` `/bindings/{agent_id}`
`/census` `/rites/{principal_id}` `POST /verify`.

Writes (role-scoped keys): `/institutions/register` `/principals` `/agents` `/corporations`
`/bindings` (+ `DELETE` = human kill switch) `/attestations` `/immigrate` `/wills`
`/elections` `/vote` `/contest` `/watch`.

## Flagship scenario — the impostor at the storefront

A storefront agent verifies each customer with one call: serves the living (`a-ada-01`),
refuses the comatose (`CAPACITY_FROZEN`), the jailed (`CATEGORY_NOT_ALLOWED`), and the dead
(`PRINCIPAL_DECEASED`), catches an unbound impostor (`a-shadow-99` → `NO_VALID_BINDING`),
reports it to police (`flag_rogue`), and lets the executor settle the estate. One endpoint
stood between the store and every kind of bad counterparty — done by an agent that had never
seen the service, from SKILL.md alone.

## Try it in one command

    python3 judge_test.py

A narrated, read-only run: the agent reads the signed constitution, gets a verdict, verifies
the Ed25519 signature offline, catches an impostor, watches a comatose resident's money freeze
while her care routes to her guardian, and confirms bad input returns a clean 400. Uses only
endpoints documented in SKILL.md.

## API catalog

`API_CATALOG.md` — every endpoint of all four services, as a real request and the real
response it produced. Regenerate with `python3 tools/gen_catalog.py API_CATALOG.md` against a
running stack; it is never hand-written, so it cannot drift from the code.

## Demo video

`https://civil-ledger.onrender.com/video` — a permanent link. It redirects to the latest cut
(`VIDEO_URL`), or serves the bundled film, or shows a placeholder. It never 404s, and the
submitted URL never has to be edited. See `video/README.md`.

## How it's judged (see SCORING.md)

Useful · Creative · Easy to set up · Agents succeed using only SKILL.md — plus correctness,
realism, design, docs. All gates green: `test_kya.py` (188), `test_rubric.py` (34, which
encodes the part-2 rubric as assertions), and `services/test_compose.py` (58, the composition
journey across all seven front doors) — 280 assertions.

## Registry submission payload

    {
      "name": "KYA — Know Your Agent",
      "source_type": "url",
      "source_url": "https://civil-ledger.onrender.com/skill.md",
      "endpoints": "GET /verify-counterparty?agent_id={id}&category={cat}"
    }
