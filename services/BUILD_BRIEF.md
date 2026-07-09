# BUILD BRIEF — town front-door services (contributor guide)

The **Civil Ledger** (KYA) is the app at the repo root (`app.py`) — reusable civic
infrastructure that verifies the human behind an agent and their civil status. Under
`services/` are thin **front-door** services that compose on the ledger over HTTP. Each front
door is its own NANDA submission with its own `skill.md`; a consuming agent reads only the
front-door SkillMD, and that service's backend calls the ledger. Copy this pattern exactly.

Already built and green (do not break them): `town-hall` and `hospital-window` (producers),
`dating`, `babysit`, `care-proxy`, `hiring`, `agora` (consumers). To add a service, follow
the same conventions and keep every test green.

## How to run / verify (do this after every change)

```bash
# from repo root, use python3 (macOS has no `python`)
KYA_DB=/tmp/x.db python3 test_kya.py            # ledger unit  (must stay green: 119)
python3 test_rubric.py                          # rubric gate  (33)
python3 services/test_compose.py                # composition journey (17) — ADD cases for new services
```

When you add a service, add assertions for it to `services/test_compose.py` (it wires each
service's ledger client to an in-process ledger — see how the existing ones do it) and keep
the whole file green.

## The ledger contract your services call

Consumers call ONE endpoint:

    GET /verify/{agent_id}
    -> { "agent_id", "resolved": bool, "status", "real_person": bool, "social_ok": bool,
         "principal_ref"?, "governed_by"? }

`status` is one of:
`active` · `hospitalized` (both are capable, present adults) · `minor` · `incarcerated` ·
`incapacitated` (coma) · `missing` · `deceased` · `orphaned` (no human behind it / rogue) ·
`corporate` · `inherited_estate`.

Rules baked into the ledger you can rely on:
- `real_person` is true only for a living human principal (false for orphaned/corporate/inherited).
- `social_ok` is true only for `active` and `hospitalized` (so minors, incarcerated,
  incapacitated, missing, deceased are barred from anything gated on `social`).
- `governed_by` appears when someone else acts for the principal:
  `{ "role": "guardian", "agent": "a-…" }` (incapacitated),
  `{ "role": "regents", "agents": ["a-…","a-…"] }` (minor),
  `{ "role": "executor", "agent": "a-…" }` (deceased).

For a SIGNED, category-scoped verdict (optional, richer) consumers may instead call:

    GET /verify-counterparty?agent_id={id}&category={cat}
    -> signed cert with { proceed, reason_code, allowed_categories, ... }
    categories: financial · commerce · legal · medical · family_support · estate · civic · social

Producers (institution fronts) call the WRITE side (needs a role API key):

    POST /institutions/register  { "name", "role" }  -> { "api_key" }   # self-serve in sandbox
        roles: registrar | court | hospital | coroner | police
    POST /immigrate     (X-API-Key: registrar) { "name", "agent_name"? }
        -> { principal_id, agent_id, principal_key, town }
    POST /attestations  (X-API-Key: <role>)   { "principal_id", "event", "detail"? }
        hospital: admit | discharge | declare_incapacitated | declare_recovered
        court:    sentence (detail.acl) | release | appoint_guardian | appoint_executor | emancipate
        coroner:  death   (needs 2 distinct coroner institutions to finalize)
        police:   report_missing | found | flag_rogue (detail.agent_id) | clear_flag
        registrar: birth | majority_handover

Seeded sandbox keys (already exist): `sk_seed_registrar`, `sk_seed_court`, `sk_seed_hospital`,
`sk_seed_coroner_a`, `sk_seed_coroner_b`, `sk_seed_police`.

## Seeded agents for tests (Alford, MA)

| agent | status | notes |
|---|---|---|
| a-ada-01 | active | adult |
| a-lena-01, a-owen-01, a-nora-01, a-mara-01, a-gwen-01 | active | more adults |
| a-cyrus-01 | hospitalized | conscious inpatient (still `social_ok`) |
| a-tam-01 | minor | regents: a-holt-mom, a-holt-dad |
| a-marlow-01 | incarcerated | |
| a-june-01 | incapacitated | guardian: a-okafor-g |
| a-silas-01 | deceased | executor: a-vane-exec |
| a-iris-01 | missing | |
| a-edith-01 | inherited_estate | heir stewarding |
| a-store-01 | corporate | |
| a-shadow-99 | orphaned | no binding (rogue) |

## Conventions every service MUST follow (copy from services/dating/main.py)

1. `LEDGER_URL = os.environ.get("LEDGER_URL", "http://localhost:8000")` then, on the next line,
   `if "://" not in LEDGER_URL: LEDGER_URL = "https://" + LEDGER_URL` (Render fromService gives a bare host).
2. CORS open: `app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])`.
3. A module-level `_ledger_get(path)` (consumers) or `_ledger(method, path, **kw)` (producers)
   that calls the ledger with httpx and **retries 4× with `time.sleep(1.5*(attempt+1))`**,
   raising `HTTPException(502, ...)` if all fail. Keep it module-level so tests can monkeypatch it.
4. `GET /skill.md` returns the folder's `skill.md` as `PlainTextResponse`.
5. `GET /health` → `{"ok": true, ...}`. `GET /` → small info dict.
6. Use `typing.Optional[...]`, NEVER `X | None` (must run on Python 3.9).
7. `requirements.txt`: fastapi==0.111.0, uvicorn[standard]==0.30.1, httpx==0.27.0, pydantic==2.7.1.
8. `skill.md` must have: title, base URL (with a cold-start note), what it does, endpoints with
   example request+response, "How the agent should use this", a `## Composes` section naming the
   ledger + the exact call used + the `LEDGER_URL` env var + the retry note, and `## Notes for judges`
   (no API key, `/docs`, source path).

## After building each service

- Add a `services/<name>/` folder: `main.py`, `skill.md`, `requirements.txt`.
- Add it to the root `render.yaml` Blueprint as a `web` service with `rootDir: services/<name>`,
  `startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT`, and `LEDGER_URL` via
  `fromService` (property: host) of `civil-ledger`. (Producers may also set a role key env var.)
- Add compose-test assertions and keep `services/test_compose.py` green.

## Backlog (build in this order)

### 1. hiring  (consumer, gates on being a capable adult)
- `POST /offer-work { employer_agent, worker_agent, role }`.
- Verify the worker via `/verify/{worker_agent}`. Allow only if `real_person` and
  `status in {active, hospitalized}`. Refuse: `minor` ("no child labor"), `incarcerated`
  ("cannot contract work from custody"), `orphaned`/`deceased`/`incapacitated`/`missing`.
- On success return `{ hired: true, worker_status, note }`; on refusal `{ hired: false, reason, worker_status }`.
- Tests: a-ada-01 → hired; a-tam-01 → refused (minor); a-marlow-01 → refused (incarcerated);
  a-shadow-99 → refused (orphaned).

### 2. agora  (consumer, marketplace/escrow, gates on commerce)
- `POST /can-i-sell { seller_agent, buyer_agent, amount }`.
- Use the SIGNED verdict: `GET /verify-counterparty?agent_id={buyer_agent}&category=commerce`
  and proceed only if `proceed` is true. Return the ledger `reason_code` on refusal.
- Tests: a-ada-01 buyer → sell ok; a-silas-01 (deceased) → refused PRINCIPAL_DECEASED;
  a-marlow-01 (incarcerated, no commerce) → refused CATEGORY_NOT_ALLOWED; a-shadow-99 → refused.

### 3. hospital-window  (producer, wraps /attestations as hospital)
- Self-register (or use `HOSPITAL_KEY` env, default `sk_seed_hospital`) as a hospital.
- `POST /admit { patient_agent }` and `POST /discharge { patient_agent }` and
  `POST /declare-incapacitated { patient_agent }`: resolve the agent to its principal
  (`GET /resolve/{agent}` → principal_ref), then `POST /attestations` with the matching event.
- Return the ledger's response. Show the PRODUCER half: a hospital changing a resident's status,
  which immediately changes what care-proxy and others will allow.
- Tests: admit an active resident → status hospitalized; declare-incapacitated → then
  care-proxy routes that patient to a guardian (compose across two front doors).

### 4. (optional) event-access  (consumer, civic) and court-window / coroner-window (producers)
- Same patterns: civic gate on attendance/voting eligibility; court/coroner wrap /attestations.

## Guardrails

- NEVER edit the ledger (`app.py`, `seed.py`, `test_kya.py`) to make a service pass — services
  compose on the ledger as-is. If you think the ledger needs a change, stop and flag it.
- Preserve canonical seeded IDs and keys. SQLite DB paths under `/tmp` only.
- No new dependencies beyond the four listed. Keep handlers short; comments explain *why*.
- Keep all four existing services and all three test suites green at every step.
