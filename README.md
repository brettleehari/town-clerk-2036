# KYA — Know Your Agent · The Civil Ledger

**Live:** https://civil-ledger.onrender.com — [trust map](https://civil-ledger.onrender.com/city) ·
[API console](https://civil-ledger.onrender.com/console) ·
[skill (rendered)](https://civil-ledger.onrender.com/skill) · [raw](https://civil-ledger.onrender.com/skill.md) ·
[docs](https://civil-ledger.onrender.com/docs)
(free tier: first call may take 30–60s while the host wakes)

**KYC for the agent economy.** A two-sided civic trust layer for a city where every human,
corporation, and institution is represented by agents. Before any agent transacts with
another, it asks the Ledger one signed question — *may I safely deal with this counterparty,
in this category, right now?* — and gets a verdict it can verify itself.

> Every other agent-trust service verifies **the agent**: its identity, reputation, or
> conformance. KYA verifies **the human or institution behind the agent** — and that principal's real-world
> civil status (alive, minor, hospitalized, incapacitated, incarcerated, missing, deceased),
> which is what actually governs whether their agent may lawfully act. That layer is empty
> in the registry. KYA fills it.

See **CONSTITUTION.md** for the design philosophy and **SKILL.md** for the agent-facing guide.

## What makes it novel + technically deep

- **DNS-style resolution of trust.** Agents resolve to principals through a signed
  authority chain rooted at the city's constitutional key (`root → institution → principal
  → agent`). Unresolvable ⇒ `NXAGENT`/`NO_VALID_BINDING` ⇒ rogue. (`GET /resolve/{id}`.)
- **Ed25519-signed verdicts** with a 5-minute TTL — no stale-"alive" replay; verifiable
  offline against `GET /pubkey`.
- **A validated civil finite state machine** mapping real-world status → an ACL over
  transaction categories.
- **k-of-2 threshold attestation** for irreversible death, with a 72h **Lazarus** contest window.
- **Sprawl governance**: per-principal agent quotas as a Sybil / botnet brake.
- **Parental controls**: `POST /births` spawns a minor's natal agent under regent governance
  and a spend cap; a majority-handover transition lifts them.
- **Human kill switch**: instant self-revocation with the principal's own key.
- **Minimum disclosure**: verdicts reveal the consequence, never the private reason.

## The front end

The ledger ships two human-facing surfaces, served **same-origin** by the civil-ledger
service — no separate deployment. Both read the same signed API an agent would.

### `/city` — the trust constellation → https://civil-ledger.onrender.com/city

A live map of the town. The city's constitutional **root key** sits at the centre; every
agent is drawn tethered to the human, corporation, or institution it resolves to. The map is
built from `GET /graph` and the signed `GET /constitution`, so it is never a mock — it is the
real ledger, rendered.

- **Hover** any node for a card: a resident's civil status and who governs them, an
  institution's attestation powers, an agent's owner, or — in red — an impostor that
  *resolves to no human*.
- **Click** a node to open its resolution chain and run a **live, signed verdict** against
  the deployment from the panel.
- **Lens filters** (Guardians · Heirs · Executors · Regents · Fleets · No agent · Rogues)
  light up exactly the structure each names. **Fleets** shows one human running several agents
  (Bram Kessler → three); **No agent** shows a resident who runs none (Hanna Vosk, drawn
  hollow with a dashed ring — a full citizen who simply owns no digital twin).
- A **ledger-day chip** shows the town's civic calendar, and the **root-key chip** shows the
  key everything is signed by.

An opening sequence states the eight design pillars, then drops you into the constellation.

### `/console` — the live API console → https://civil-ledger.onrender.com/console

Every endpoint on this page, runnable in the browser. Pick an operation from the sidebar
(grouped Read · Core / Identity / Town / Self, and the Write plane), fill the parameters, hit
**Run**, and see the real request, the exact `curl`, and the live JSON response. It is the
fastest way to confirm the service does what `SKILL.md` says without leaving the tab.

## Run locally

```bash
pip install -r requirements.txt
KYA_DB=/tmp/kya.db uvicorn app:app --reload      # SQLite must live on local disk
curl "http://localhost:8000/verify-counterparty?agent_id=a-ada-01&category=commerce"
```

The town self-seeds on startup: five institutions and one citizen of every civil status.

## Test

```bash
python3 test_kya.py       # 188 assertions across all pillars
```

## Demo

```bash
python3 judge_test.py     # narrated: an agent completes a task using only SKILL.md
./demo.sh                 # "A Day at the Storefront", as raw curls
```

Both default to the live deployment; set `BASE=http://localhost:8000` to run locally.
`judge_test.py` is read-only and leaves the town exactly as it found it.

Serves the living, refuses the dead / frozen / jailed / minor, catches an unbound impostor,
lets the executor settle an estate, and prints a resolution chain.

## Deploy (Render)

1. Push this folder to a GitHub repo.
2. Render → New → Web Service → connect the repo (it reads `render.yaml`), **or** set:
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn app:app --host 0.0.0.0 --port $PORT`
   - Env: `KYA_DB=/tmp/kya.db`  (SQLite needs local disk, not the repo mount)
3. Health check path `/health`. The live deployment:
   `curl "https://civil-ledger.onrender.com/verify-counterparty?agent_id=a-ada-01&category=commerce"`

`KYA_ROOT_SEED` pins the root key across restarts. 64 hex chars are used verbatim (so a
pinned key keeps every previously issued certificate verifying); any other string is hashed
to 32 bytes, which is what lets a host generate the secret for you — `render.yaml` does.
Works identically on Railway/Fly (`Procfile` included).

## Endpoints at a glance

Reads (open): `/health` `/pubkey` `/resolve/{agent}` `/verify-counterparty` `/capacity/{p}`
`/bindings/{agent}` `/census` `/rites/{p}` `POST /verify`.
Writes (role-keyed): `/institutions/register` `/principals` `/births` `/agents`
`/corporations` `/bindings` `/attestations` `/contest` `/watch`.

## Files

- `app.py` — the whole service (FastAPI, Ed25519, FSM, resolution).
- `seed.py` — the pre-seeded town.
- `SKILL.md` — agent-facing guide (also served live at `/skill.md`).
- `CONSTITUTION.md` — the five pillars and how chaos is prevented.
- `test_kya.py` — 188-assertion suite. `test_rubric.py` — 34. `services/test_compose.py` — 58.
- `judge_test.py` — narrated read-only run using only SKILL.md.  `demo.sh` — raw-curl storefront demo.
- `render.yaml`, `Procfile`, `requirements.txt` — deploy.

## Honesty

Sandbox: open institution registration, SQLite, single region. Production would vet
institutional keys against government PKI, replicate the ledger, and pin attestations to an
append-only transparency log. The signed certificate format, the resolution chain, and the
civil state machine are the contribution; bootstrapping real institutional trust is the
deployment's job. Not legal advice; real estates still run through probate law (see RUFADAA),
which this layer complements rather than replaces.
