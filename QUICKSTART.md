# QUICKSTART — run the town locally

Everything lives in this one folder. No external services are required.

## 0. Prerequisites

- Python 3.10+ (`python3 --version`)

```bash
python3 -m pip install -r requirements.txt      # add --break-system-packages if needed
```

## 1. Check the gate (should print GREEN)

```bash
bash overnight/verify.sh
# gate 1/2 — test_kya.py     (139 passed)
# gate 2/2 — test_rubric.py  (34 passed)  <- the NANDA part-2 rubric
```

The composition suite runs the seven front doors against an in-process ledger:

```bash
python3 services/test_compose.py            # 45 passed
```

## 2. Run the Civil Ledger

```bash
KYA_DB=/tmp/kya.db uvicorn app:app --port 8000
```

The town self-seeds on startup. Then:

```bash
curl "http://localhost:8000/verify-counterparty?agent_id=a-ada-01&category=commerce"
open  "http://localhost:8000/city"        # the trust constellation
open  "http://localhost:8000/console"     # live API console
open  "http://localhost:8000/docs"        # OpenAPI
```

## 3. Run the front-door services (optional)

Each service is independent and reaches the ledger over HTTP via `LEDGER_URL`.

```bash
export LEDGER_URL=http://127.0.0.1:8000
( cd services/town-hall       && PORT=8103 uvicorn main:app --port 8103 ) &
( cd services/dating          && PORT=8100 uvicorn main:app --port 8100 ) &
( cd services/babysit         && PORT=8101 uvicorn main:app --port 8101 ) &
( cd services/care-proxy      && PORT=8102 uvicorn main:app --port 8102 ) &
( cd services/hiring          && PORT=8104 uvicorn main:app --port 8104 ) &
( cd services/agora           && PORT=8105 uvicorn main:app --port 8105 ) &
( cd services/hospital-window && PORT=8106 uvicorn main:app --port 8106 ) &
```

Then drive the whole town, including the cross-service demo where a hospital changes one
resident's civil status and every other service silently starts refusing them:

```bash
bash services/demo_town.sh
```

## 4. Deploy

`render.yaml` is a Render Blueprint defining all eight services and auto-wiring each front
door's `LEDGER_URL` to the ledger. The UI ships inside the ledger service, so `/city` and
`/console` are live as soon as it deploys. See `PREFLIGHT.md`.

## Notes

- SQLite databases must live under `/tmp` (`KYA_DB=/tmp/kya.db`); this folder's mount blocks
  SQLite locking.
- The signing seed (`*.rootseed`) and all `*.db` files are gitignored — the root private key
  never enters the repo. Set `KYA_ROOT_SEED` to pin a stable identity across restarts.
