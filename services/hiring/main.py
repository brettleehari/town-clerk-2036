"""
hiring — "verify before you HIRE."
=================================
An employment front door for the agentic town. An employer's agent wants to offer work to
a worker's agent. Before any contract exists, THIS service asks the Civil Ledger (a separate
NANDA submission) whether there is a real, capable, present adult behind the worker's agent.

The constitutional bars fall out of the ledger for free:
  * a minor cannot be hired      -> no child labor
  * an incarcerated person cannot contract work from custody
  * a coma patient / missing person / deceased person cannot consent to employment
  * an orphaned (rogue / unrooted) agent has no human behind it at all

Composition (the pattern from the NANDA reference emailer->router):
  * This is its own submission with its own skill.md; the judge's agent reads only THIS file.
  * Its backend calls the Civil Ledger over HTTP (LEDGER_URL env var, retry on cold start).
  * The agent never needs to know the ledger exists.
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

app = FastAPI(title="hiring — verify before you hire", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- composition: the one call downstream to the Civil Ledger ------------------ #

def _ledger_get(path: str) -> dict:
    """GET the Civil Ledger with retry — Render free tier sleeps and 404s/hangs while
    waking, exactly like the reference emailer->router call. 4 tries, then 502."""
    last = None
    for attempt in range(4):
        try:
            r = httpx.get(f"{LEDGER_URL}{path}", timeout=65)
            r.raise_for_status()
            return r.json()
        except Exception as e:            # noqa: BLE001 — cold-start tolerance
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise HTTPException(502, f"civil ledger unreachable at {LEDGER_URL}: {last}")

# Only a capable, present adult may enter an employment contract. `hospitalized` stays
# eligible on purpose: a conscious inpatient keeps their right to contract (the ledger's
# ACL says so), and remote work from a hospital bed is lawful.
EMPLOYABLE = {"active", "hospitalized"}

# Why each refusal happened, in plain language the employer's agent can relay.
REFUSALS = {
    "minor":          "no child labor: the worker is a minor",
    "incarcerated":   "the worker cannot contract work from custody",
    "incapacitated":  "the worker cannot consent to employment (incapacitated)",
    "missing":        "the worker is registered missing and cannot consent",
    "deceased":       "the worker is deceased",
    "orphaned":       "no verified human behind that agent (unrooted or rogue)",
    "corporate":      "that agent is a corporate entity, not a person who can be employed",
    "inherited_estate": "that agent now serves an estate, not a living worker",
}

class OfferIn(BaseModel):
    employer_agent: str
    worker_agent: str
    role: str

@app.post("/offer-work")
def offer_work(body: OfferIn):
    """Offer work to a worker's agent. Verifies the human behind the worker is a real,
    capable, present adult before the offer stands. The employer is not status-checked —
    anyone may offer; the constitution only protects the person being hired."""
    v = _ledger_get(f"/verify/{body.worker_agent}")
    status = v.get("status", "orphaned")

    if not v.get("real_person") or status not in EMPLOYABLE:
        return {"hired": False, "worker_status": status,
                "reason": REFUSALS.get(status, "the worker cannot be hired right now")}

    return {"hired": True, "worker_status": status, "role": body.role,
            "employer_agent": body.employer_agent, "worker_agent": body.worker_agent,
            "note": "verified as a real, capable adult; no other personal data disclosed"}

@app.get("/health")
def health():
    return {"ok": True, "service": "hiring", "ledger": LEDGER_URL}

@app.get("/skill.md", response_class=PlainTextResponse)
def skill_md():
    p = os.path.join(os.path.dirname(__file__), "skill.md")
    return PlainTextResponse(open(p).read()) if os.path.exists(p) else \
        PlainTextResponse("skill.md not bundled", status_code=404)

@app.get("/")
def root():
    return {"service": "hiring", "read": "GET /skill.md", "composes": LEDGER_URL}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8104)))
