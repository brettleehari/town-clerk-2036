"""
town-hall — "move to town: get your agent on the civil rolls."
==============================================================
The PRODUCER front door. Every other service (dating, babysit, care) READS the Civil Ledger.
Institutions PRODUCE the data. town-hall is the registrar's window: an agent brings a new
human into the town, and this service composes the ledger's producer side to mint a verified
principal + agent (the origin point of every record the consumer apps later rely on).

It self-registers as the town REGISTRAR (or uses REGISTRAR_KEY), then calls the ledger's
`POST /immigrate`. This is the two-sided story: producers create identity; consumers trust it.

Composition: own submission + own SKILL.md; backend calls the ledger over HTTP
(LEDGER_URL env var, retry on cold start). The agent only ever calls this service.
"""
import os
import time

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Optional

LEDGER_URL = os.environ.get("LEDGER_URL", "http://localhost:8000")
if "://" not in LEDGER_URL:            # Render fromService gives a bare host; add scheme
    LEDGER_URL = "https://" + LEDGER_URL
REGISTRAR_KEY = os.environ.get("REGISTRAR_KEY")   # optional; else self-register below

app = FastAPI(title="town-hall — registrar onboarding", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def _ledger(method: str, path: str, **kw) -> dict:
    last = None
    for attempt in range(4):
        try:
            r = httpx.request(method, f"{LEDGER_URL}{path}", timeout=65, **kw)
            r.raise_for_status()
            return r.json()
        except Exception as e:            # noqa: BLE001 — cold-start tolerance
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise HTTPException(502, f"civil ledger unreachable at {LEDGER_URL}: {last}")

_key_cache = {"registrar": REGISTRAR_KEY}

def registrar_key() -> str:
    """Obtain a registrar API key — from env, or self-register with the ledger (the sandbox
    allows open institution registration). Cached for the process lifetime."""
    if _key_cache.get("registrar"):
        return _key_cache["registrar"]
    reg = _ledger("POST", "/institutions/register",
                  json={"name": "Town Hall (registrar window)", "role": "registrar"})
    _key_cache["registrar"] = reg["api_key"]
    return _key_cache["registrar"]

class MoveIn(BaseModel):
    name: str
    agent_name: Optional[str] = None

@app.post("/move-to-town")
def move_to_town(body: MoveIn):
    """Onboard a new resident + their agent into the town (like getting a driver's license).
    Returns the new agent id and the private principal_key (the human's kill switch)."""
    key = registrar_key()
    payload = {"name": body.name}
    if body.agent_name:
        payload["agent_name"] = body.agent_name
    res = _ledger("POST", "/immigrate", json=payload, headers={"X-API-Key": key})

    # Close the loop: the new agent is now verifiable by every consumer service.
    check = _ledger("GET", f"/verify/{res['agent_id']}")
    return {
        "welcome": f"registered in {res.get('town', 'the town')}",
        "principal_id": res["principal_id"],
        "agent_id": res["agent_id"],
        "principal_key": res["principal_key"],
        "now_verifiable": {"status": check.get("status"),
                           "real_person": check.get("real_person"),
                           "social_ok": check.get("social_ok")},
        "note": "keep principal_key secret — it is your agent's kill switch",
    }

@app.get("/health")
def health():
    return {"ok": True, "service": "town-hall", "ledger": LEDGER_URL}

@app.get("/skill.md", response_class=PlainTextResponse)
def skill_md():
    p = os.path.join(os.path.dirname(__file__), "skill.md")
    return PlainTextResponse(open(p).read()) if os.path.exists(p) else \
        PlainTextResponse("skill.md not bundled", status_code=404)

@app.get("/")
def root():
    return {"service": "town-hall", "read": "GET /skill.md", "composes": LEDGER_URL}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8103)))
