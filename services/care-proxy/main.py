"""
care-proxy — "who may make a care decision for this patient?"
=============================================================
A medical-authorization service for the agentic town. An agent (a hospital's, a family
member's) wants to act on behalf of a patient — approve a procedure, release records. Before
authorizing, THIS service asks the Civil Ledger (a separate NANDA submission) who is
lawfully allowed to act for that patient:

  * patient is `active`          -> only the patient's OWN agent may act.
  * patient is `incapacitated`   -> the decision ROUTES to the appointed GUARDIAN agent.
  * patient is deceased/orphaned  -> no care authorization (estate/none).

This is the guardian-routing case the town constitution already encodes — care-proxy just
surfaces it as a clean yes/route/deny for agents.

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

LEDGER_URL = os.environ.get("LEDGER_URL", "http://localhost:8000")
if "://" not in LEDGER_URL:            # Render fromService gives a bare host; add scheme
    LEDGER_URL = "https://" + LEDGER_URL

app = FastAPI(title="care-proxy — who may act for a patient", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def _ledger_get(path: str) -> dict:
    last = None
    for attempt in range(4):
        try:
            r = httpx.get(f"{LEDGER_URL}{path}", timeout=65)
            r.raise_for_status()
            return r.json()
        except Exception as e:            # noqa: BLE001
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise HTTPException(502, f"civil ledger unreachable at {LEDGER_URL}: {last}")

def ledger_verify(agent_id: str) -> dict:
    return _ledger_get(f"/verify/{agent_id}")

class CareIn(BaseModel):
    requesting_agent: str      # the agent asking to make the decision
    patient_agent: str         # the patient it wants to act for

@app.post("/authorize-care")
def authorize_care(body: CareIn):
    """Decide whether `requesting_agent` may make a care decision for `patient_agent`."""
    patient = ledger_verify(body.patient_agent)
    status = patient.get("status")

    if not patient.get("real_person"):
        return {"authorized": False, "reason": "patient is not a verifiable real person",
                "patient_status": status}

    if status in ("deceased", "missing"):
        return {"authorized": False, "reason": f"no care authorization for a {status} patient",
                "patient_status": status}

    # Anyone the ledger says is governed by someone else — a comatose adult with a court
    # guardian, OR a minor under regents — has their care routed to that proxy. Reading only
    # `role == "guardian"` here meant a 14-year-old authorised his own surgery while his
    # parents were refused. The ledger already names the proxies; trust it.
    gov = patient.get("governed_by") or {}
    proxies = gov.get("agents") or ([gov["agent"]] if gov.get("agent") else [])
    if proxies:
        role = gov.get("role", "proxy")
        if body.requesting_agent in proxies:
            return {"authorized": True, "acting_as": role, "patient_status": status,
                    "note": f"patient is governed by {role}; you are one of them"}
        return {"authorized": False, "patient_status": status,
                "reason": f"patient is governed by {role}; only they may authorize care",
                "route_to": proxies[0] if len(proxies) == 1 else proxies}

    # active / hospitalized (conscious), governed by self: only their own agent may authorize.
    if body.requesting_agent == body.patient_agent:
        return {"authorized": True, "acting_as": "self", "patient_status": status,
                "note": "patient is capable and is acting for themselves"}
    return {"authorized": False, "patient_status": status,
            "reason": "patient is capable; only their own agent may authorize care"}

@app.get("/health")
def health():
    return {"ok": True, "service": "care-proxy", "ledger": LEDGER_URL}

@app.get("/skill.md", response_class=PlainTextResponse)
def skill_md():
    p = os.path.join(os.path.dirname(__file__), "skill.md")
    return PlainTextResponse(open(p).read()) if os.path.exists(p) else \
        PlainTextResponse("skill.md not bundled", status_code=404)

@app.get("/")
def root():
    return {"service": "care-proxy", "read": "GET /skill.md", "composes": LEDGER_URL}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8102)))
