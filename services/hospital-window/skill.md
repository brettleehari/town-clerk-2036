---
name: hospital-window
user-invocable: true
description: >
  The hospital admitting desk of a 2036 agent-native town — an institution that WRITES civil
  status. Admit, discharge, or declare a patient incapacitated, and it records the attestation
  on the town's Civil Ledger, instantly changing what every other service will let that person
  do: their care routes to a guardian, and the marketplace, hiring, and dating services begin
  refusing them — nobody polled, all reading the same ledger. Only lawful transitions pass
  (the civil state machine). Also the town's teaching window: a runnable scenario API and a
  copy-paste playbook drive every other front door from this one skill. Use when the user says
  "admit this patient", "discharge them", "declare the patient incapacitated", "my patient is
  in a coma", "update someone's medical status", "the hospital needs to record an admission",
  "show me what an incapacity declaration does to the town", "run the hospital demo", or
  "teach me the town through the hospital".
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

**Two ways in:** an agent can **run** the whole demo through the scenario API (below), or read
**Part 1** (the endpoints) and **Part 2** (the copy-paste playbook that drives every other front
door). For the raw primitives underneath, **Part 3** points at the core Civil Ledger skill.

## Base URL

    https://hospital-window.onrender.com

(Live. Free-tier hosts sleep when idle: call `GET /health` first and retry once after
~30–60s if it does not answer. Every read is open — no API key.)

## ⇢ START HERE — runnable scenarios (the playbook, as an API)

Don't hand-copy curls: **discover and execute** the stories over HTTP. The court/hospital/police
keys stay *behind* this service — you name an action, never a credential, and every run's
cleanup **always executes, even if a step fails**, so a demo can't leave the town polluted.

    GET  /scenarios            — the menu (round-trip, incapacity-arc, fleet-freeze, rogue-agent, coma-vulture, …)
    GET  /scenarios/{id}       — the exact steps, expectations, and a ready-to-paste curl for each
    POST /scenarios/{id}/run   — execute end-to-end; get a step-by-step transcript
    GET  /scenarios/actions    — the whitelisted action vocabulary
    POST /scenarios            — compose your OWN scenario from those actions

Scenarios marked `writes:true` change civil status (reversibly — cleanup is built in) and
require `{"confirm": true}` on `/run`. **Start with `GET /scenarios`.**

---

# Part 1 — the service

## What it does

Given a patient's agent id, it resolves that agent to the human behind it and records a
civil event with the Civil Ledger as an attesting hospital. The consequences are town-wide
and automatic:

- **`/admit`** → status `hospitalized`. The patient keeps every civil right — a conscious
  inpatient may still contract, meet, and vote. Nothing else changes.
- **`/declare-incapacitated`** → status `incapacitated`. Capacity freezes town-wide:
  care-proxy routes their medical decisions to their court-appointed guardian; dating,
  hiring, and agora refuse them.
- **`/discharge`** → status returns to `active`.

No consumer service is notified, polled, or updated. They read the same ledger.

## The state machine you drive

| From | Event | To | How |
|---|---|---|---|
| `active` | admit | `hospitalized` | `POST /admit` |
| `hospitalized` | discharge | `active` | `POST /discharge` |
| `active` / `hospitalized` | declare incapacitated | `incapacitated` | `POST /declare-incapacitated` |
| `incapacitated` | declare recovered | `active` | raw ledger call (see Cleanup) |

Everything else is unlawful: a `409` refuses it and names the patient's real status. An agent
with no verified human behind it is refused `404` before any write happens.

## Endpoints

**`POST /admit`** · **`POST /discharge`** · **`POST /declare-incapacitated`** — body
`{"patient_agent":"a-…"}`. Response:

    { "ok": true, "event": "admit", "patient_agent": "a-gwen-01",
      "principal_id": "p-gwen-alcott", "status": "hospitalized", "social_ok": true }

`now_governed_by` appears **only when a court has already appointed the patient a guardian**
(Playbook 1's sibling, Playbook "guardian chain", runs that two-step). Refusals:

    409  { "detail": "illegal transition 'declare_incapacitated' for a patient whose civil status is 'incapacitated'" }
    404  { "detail": "no verified human behind a-shadow-99 (NO_VALID_BINDING)" }

**`GET /health`** → `{ "ok": true, "service": "hospital-window", "ledger": "…" }` (call first).
**`GET /skill.md`** → this file (`text/markdown`); **`GET /skill`** → rendered.

## How the agent should use this

1. `GET /health` first; if silent, the host is cold — wait 30s, retry once, then treat as down.
2. `POST` the event that actually occurred. On `409`, read the patient's real status from the
   message and adjust — never retry the same call.
3. When `now_governed_by` appears, someone else now acts for that patient; route decisions there
   (care-proxy does this for you).
4. **Every endpoint here is a write, and writes are consequential** — a status change silently
   alters what five other services will let that person do. Confirm with your human before you
   admit, discharge, or declare anyone incapacitated. This seeded town is synthetic; every
   scenario/playbook ends with a cleanup that restores the patient exactly as found.

---

# Part 2 — the curriculum: run the whole town from this window

One write here rearranges five other services on their next read. This is the composition
pattern: **one skill orchestrating its siblings over plain HTTP**, coordinated only by a shared
constitutional ledger.

**The services the playbook calls** (each serves its own skill at `{base}/skill.md`; all are
free dynos — hit `/health` once to warm them, cold starts take 30–120s):

| Service | One job | Base URL |
|---|---|---|
| hiring | capable-adult gate: `POST /offer-work` | https://hiring-q7xc.onrender.com |
| agora | signed sale verdict: `POST /can-i-sell` | https://agora-egpi.onrender.com |
| dating | verify both, then meet: `POST /arrange-meeting` | https://dating-2gov.onrender.com |
| babysit | verify the sitter: `POST /book-sitter` | https://babysit.onrender.com |
| care-proxy | who may decide: `POST /authorize-care` | https://care-proxy.onrender.com |
| town-hall | mint a resident: `POST /move-to-town` | https://town-hall-l0kc.onrender.com |
| civil-ledger | the shared truth underneath | https://civil-ledger.onrender.com |

**Patient etiquette:** demo on **`a-gwen-01`** (seeded `active`, no guardian) and **always run
the cleanup step** — the town is shared. Never demo on `a-june-01` (already incapacitated) or
`a-silas-01` (deceased). For a run touching *no* seeded resident, mint your own via town-hall's
`POST /move-to-town` and use the returned agent id.

## Playbook — the ripple (one write, five services rearrange)

*What it teaches: civil status is a shared fact, not a message. Nobody is notified; every
service simply reads differently.*

    # 1) BEFORE — the town says yes to Gwen everywhere
    curl -X POST https://hiring-q7xc.onrender.com/offer-work -H "Content-Type: application/json" \
      -d '{"employer_agent":"a-store-01","worker_agent":"a-gwen-01","role":"clerk"}'
    #    -> { "hired": true, "worker_status": "active", ... }
    curl -X POST https://agora-egpi.onrender.com/can-i-sell -H "Content-Type: application/json" \
      -d '{"seller_agent":"a-store-01","buyer_agent":"a-gwen-01","amount":20}'
    #    -> { "sell": true, "reason_code": "OK", "certificate_id": "c-…" }   ← keep this id

    # 2) THE WRITE — one attestation at this window
    curl -X POST https://hospital-window.onrender.com/declare-incapacitated \
      -H "Content-Type: application/json" -d '{"patient_agent":"a-gwen-01"}'
    #    -> { "status": "incapacitated", "social_ok": false, ... }

    # 3) AFTER — five services refuse, each in its own vocabulary, none was told
    curl -X POST https://hiring-q7xc.onrender.com/offer-work -H "Content-Type: application/json" \
      -d '{"employer_agent":"a-store-01","worker_agent":"a-gwen-01","role":"clerk"}'
    #    -> { "hired": false, "reason": "the worker cannot consent to employment (incapacitated)" }
    curl -X POST https://agora-egpi.onrender.com/can-i-sell -H "Content-Type: application/json" \
      -d '{"seller_agent":"a-store-01","buyer_agent":"a-gwen-01","amount":20}'
    #    -> { "sell": false, "reason_code": "CAPACITY_FROZEN" }
    curl -X POST https://dating-2gov.onrender.com/arrange-meeting -H "Content-Type: application/json" \
      -d '{"my_agent":"a-ada-01","their_agent":"a-gwen-01"}'
    #    -> { "arranged": false, "reason": "the other party cannot meet right now" }
    #       NOTE: dating never says WHY — minimum disclosure protects Gwen even now.
    curl -X POST https://babysit.onrender.com/book-sitter -H "Content-Type: application/json" \
      -d '{"parent_agent":"a-holt-mom","sitter_agent":"a-gwen-01"}'
    #    -> { "booked": false, "sitter_status": "incapacitated" }

    # 4) CLEANUP — recover, then rerun step 1 to watch the "yes" return
    curl -X POST https://civil-ledger.onrender.com/attestations -H "X-API-Key: sk_seed_hospital" \
      -H "Content-Type: application/json" \
      -d '{"principal_id":"p-gwen-alcott","event":"declare_recovered","detail":{}}'

Read the refusals side by side: **hiring** names the status (worker protection), **agora**
returns a machine `reason_code` (money needs codes), **dating** refuses namelessly (privacy),
**babysit** names it (child safety outranks the sitter's privacy). Same fact, four disclosure
policies — the constitution expressing itself through four front doors.

## More playbooks (runnable)

Three more stories ship as **runnable scenarios** (`GET /scenarios` → `POST /{id}/run`, cleanup
built in) and as prose in
[`references/task-recipes.md`](https://raw.githubusercontent.com/brettleehari/town-clerk-2036/main/references/task-recipes.md):

- **Guardian care chain** — court appoints a guardian, hospital declares, care-proxy reroutes the
  decision from the patient to the guardian, recovery restores self-governance.
- **Auditable admission** — a signed *yes* before and a signed *no* after a declaration: a
  third-party-verifiable receipt of what the write did to someone's economic capacity, with no
  diagnosis disclosed.
- **Onboard to bedside** — town-hall mints a brand-new resident, the town trusts them, the
  hospital changes them — all on a disposable identity that touches no seeded state.

---

# Part 3 — go deeper (the core ledger)

Everything this window does is a few HTTP calls against the **Civil Ledger**. To exercise the
primitives directly — DNS-style `GET /resolve/{id}`, the signed category-scoped verdict
`GET /verify-counterparty`, self-serving your own `hospital` role key
(`POST /institutions/register`), writing `POST /attestations` (note: the raw plane addresses the
**principal id**, not the agent id), and feeling the role/state gates push back (`403`/`409`, each
error carrying `error`/`reason`/`fix`) — and to go past this window into births, wills, the
Lazarus protocol, rogue-flagging, and the human kill switch, read the core skill:

    https://civil-ledger.onrender.com/skill.md      # full civil-ledger reasoning
    GET https://civil-ledger.onrender.com/start      # one-call machine briefing: law, cast, scenarios
    GET https://civil-ledger.onrender.com/explain/{reason_code}   # plain-English meaning of any verdict

The front door is a convenience; the capability — and the law that bounds it — lives in the ledger.

---

## Cleanup (this service cannot undo an incapacity)

Only `/discharge` reverses `/admit`. To restore a patient after a declaration, post
`declare_recovered` to the ledger as the hospital (recovery lands on `active`, so no discharge
is needed after):

    curl -X POST https://civil-ledger.onrender.com/attestations -H "X-API-Key: sk_seed_hospital" \
      -H "Content-Type: application/json" \
      -d '{"principal_id":"p-gwen-alcott","event":"declare_recovered","detail":{}}'

## Composes

A thin **producer** front door over the **Civil Ledger** (a separate NANDA Town submission).
Its backend: `POST /institutions/register` (self-serve a `hospital` key, or set `HOSPITAL_KEY`) ·
`GET /resolve/{agent_id}` · `POST /attestations` · `GET /verify/{agent_id}` (read the patient back
so the caller sees the new world). Wired via `LEDGER_URL`; retries transport/5xx failures with
backoff, surfaces a 4xx (the ledger's considered answer) immediately.

## Notes for judges

- No API key for the three hospital endpoints (the service self-registers as a hospital); the
  playbook uses the sandbox's seeded role keys where a write needs one, and **every scenario and
  playbook ends with cleanup** that restores the town. Only a `hospital`-role key can drive these
  transitions — the ledger's state machine refuses everything else.
- This is the **producer half** of the composition story, and the town's teaching window: an
  agent holding only this file can drive seven independently-submitted services — never talking
  to each other, coordinated only by a shared constitutional ledger. Proven in
  `services/test_compose.py`. Interactive API docs at `/docs`; source in this repo's
  `services/hospital-window/`.
