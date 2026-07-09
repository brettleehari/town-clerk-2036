"""
babysit — "verify the sitter before you hand over your kid."
============================================================
A childcare-booking service for the agentic town. A parent's agent wants to book a sitter.
Before confirming, THIS service asks the Civil Ledger (a separate NANDA submission) whether
the sitter's agent traces to a real, living adult in good standing on the `social` category
— which, by the town constitution, a minor's agent and an INCARCERATED person's agent can
never pass (you can't arrange to mind a child from a jail cell, and a child can't sit). If a
child agent is supplied, it also confirms the booker is actually one of that child's
registered guardians (regents).

Composition: own submission + own SKILL.md; backend calls the Civil Ledger over HTTP
(LEDGER_URL env var, retry on cold start). The agent only ever calls this service.
"""
import hashlib
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

app = FastAPI(title="babysit — verify the sitter", version="1.0.0")
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

SLOTS = ["Fri 6pm", "Sat 9am", "Sat 6pm", "Sun 10am", "Sun 5pm", "Mon 6pm", "Thu 6pm"]

def _avail(agent_id: str) -> set:
    h = int(hashlib.sha256(agent_id.encode()).hexdigest(), 16)
    return {s for i, s in enumerate(SLOTS) if (h >> i) & 1}

class BookIn(BaseModel):
    parent_agent: str
    sitter_agent: str
    child_agent: Optional[str] = None

@app.post("/book-sitter")
def book_sitter(body: BookIn):
    """Book a sitter after verifying they're a safe adult. If child_agent is given, also
    confirm the parent is a registered guardian of that child."""
    sitter = ledger_verify(body.sitter_agent)

    # The safety gate: the sitter must be a real, living adult in good standing.
    if not sitter.get("real_person"):
        return {"booked": False, "reason": "sitter is not a verifiable real person",
                "sitter_status": sitter.get("status")}
    if not sitter.get("social_ok"):
        # minors, incarcerated, incapacitated, missing, deceased all fail social
        return {"booked": False,
                "reason": "sitter is not eligible to care for a child right now",
                "sitter_status": sitter.get("status")}

    # Optional second-sided check: is the booker actually this child's guardian?
    if body.child_agent:
        child = ledger_verify(body.child_agent)
        if child.get("status") != "minor":
            return {"booked": False, "reason": "child_agent is not a registered minor"}
        gov = child.get("governed_by") or {}
        regents = gov.get("agents", []) if gov.get("role") == "regents" else []
        if body.parent_agent not in regents:
            return {"booked": False,
                    "reason": "you are not a registered guardian of this child",
                    "guardians_on_file": len(regents)}

    slot = next((s for s in SLOTS if s in _avail(body.parent_agent) and s in _avail(body.sitter_agent)), None)
    if not slot:
        return {"booked": False, "reason": "no mutually free time this week", "sitter_verified": True}
    return {"booked": True, "sitter_verified": True, "time": slot,
            "note": "sitter verified as a real adult in good standing"}

@app.get("/health")
def health():
    return {"ok": True, "service": "babysit", "ledger": LEDGER_URL}

@app.get("/skill.md", response_class=PlainTextResponse)
def skill_md():
    p = os.path.join(os.path.dirname(__file__), "skill.md")
    return PlainTextResponse(open(p).read()) if os.path.exists(p) else \
        PlainTextResponse("skill.md not bundled", status_code=404)

@app.get("/")
def root():
    return {"service": "babysit", "read": "GET /skill.md", "composes": LEDGER_URL}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8101)))
