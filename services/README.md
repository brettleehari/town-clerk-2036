# Town services — composing on the Civil Ledger

Seven front-door services that sit on top of the **Civil Ledger** (KYA, the app at the repo
root). Each is its own NANDA Town submission with its own `skill.md`; each is deployed
separately; the judge's agent reads only the front-door SkillMD, and that service's backend
calls the ledger over HTTP. This is the composition pattern from the NANDA reference
(emailer → router).

## Topology

```
   PRODUCERS write civil status             CONSUMERS read it before acting
   ┌──────────────────────┐                ┌────────────────────────────────┐
   │ town-hall            │                │ dating      (social)           │
   │   POST /immigrate    │                │ babysit     (social+guard)     │
   │ hospital-window      │                │ care-proxy  (medical)          │
   │   POST /attestations │                │ hiring      (adult gate)       │
   │                      │                │ agora       (commerce, signed) │
   └──────────┬───────────┘                └───────────────┬────────────────┘
              │                                            │
              │ writes                                     │ GET /verify
              ▼                                            ▼
   ┌────────────────────────────────────────────────────────────────────────┐
   │                          Civil Ledger  (KYA)                           │
   └────────────────────────────────────────────────────────────────────────┘
```

**Producers** — institutions that create or change a civil record:

- **town-hall** — onboards a new human + agent (`POST /move-to-town` → ledger
  `POST /immigrate`). The origin of every verified identity.
- **hospital-window** — Fairview Hospital's admitting desk. Admit, discharge, or declare a
  patient incapacitated. Each write changes what every consumer will allow.

**Consumers** — services that verify before they act:

- **dating** — `social`. Verify two people are real consenting adults before
  arranging a meeting; reveal nothing else.
- **babysit** — `social` + guardianship. Verify a sitter is a safe adult; a minor or an
  incarcerated person can never pass.
- **care-proxy** — `medical`. Route a patient's care decision to the appointed guardian
  when the patient is incapacitated.
- **hiring** — capable-adult gate. No child labor; no contracting work from custody.
- **agora** — `commerce`, using the ledger's **signed** verdict. Returns a `certificate_id`
  the seller can re-verify against the ledger's public key long after the sale settles.

The journey: onboard at town-hall → get a verified `agent_id` → use it at any consumer
service. Then hospital-window declares that person incapacitated, and every consumer refuses
them instantly — none was notified, polled, or updated. They read the same ledger. Proven
end to end in `test_compose.py` (45 assertions).

## The three conventions (copied from the reference)

1. **`## Composes`** section in each front-door `skill.md` naming the upstream ledger.
2. **Upstream URL as env var** — `LEDGER_URL` (and `REGISTRAR_KEY` for town-hall), never hardcoded.
3. **Retry with backoff** on the ledger call (4× with growing sleeps) so a cold-started
   free-tier host doesn't fail the first request of the day.

Every service also: opens CORS (`allow_origins=["*"]`), serves its own `skill.md` at
`GET /skill.md` as plain text, exposes `/docs`, and needs no API key from the caller.

## Run locally

```bash
# 1) the ledger (repo root)
KYA_DB=/tmp/kya.db python3 -m uvicorn app:app --port 8000

# 2) a front door, pointed at it (new terminal, from services/<name>/)
LEDGER_URL=http://localhost:8000 python3 -m uvicorn main:app --port 8100
curl -X POST localhost:8100/arrange-meeting -H 'Content-Type: application/json' \
  -d '{"my_agent":"a-ada-01","their_agent":"a-lena-01"}'
```

## Test the whole composition

```bash
python3 services/test_compose.py     # 17 assertions: onboard -> date/babysit/care, all rules hold
```

## Deploy (each service is its own Render web service)

For each of `town-hall`, `dating`, `babysit`, `care-proxy`:
- Root directory: `services/<name>`
- Build: `pip install -r requirements.txt`
- Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Env: `LEDGER_URL=https://<your-ledger>.onrender.com`  (town-hall may also set `REGISTRAR_KEY`)

Then register each `skill.md` separately on NANDA Town. Deploy the ledger first so its URL
exists for the `LEDGER_URL` env vars.

## Adding another front door (e.g. hiring)

Copy any consumer folder, change the endpoint name and the narrative, keep the same
`_ledger_get` + retry + CORS + `/skill.md` scaffold, and call `GET /verify/{agent_id}` with
the rule you care about. ~10 minutes per new service.
