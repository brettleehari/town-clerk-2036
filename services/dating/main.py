"""
dating — "verify before you MEET."
=================================
A dating/meeting service for the agentic town. Two people matched; now their agents want
to arrange a real-world date. Before anyone is put in a room with a stranger, THIS service
asks the Civil Ledger (a separate NANDA submission) one question about BOTH parties on the
`social` category: "is there a real, living, consenting adult behind this agent?"

It learns the answer and NOTHING else — no birthday, no address, no medical history. Then,
if both check out, the two agents exchange (mock) calendars and it proposes a time.

Composition (the pattern from the NANDA reference emailer→router):
  * This is its own submission with its own SKILL.md; the judge's agent reads only THIS file.
  * Its backend calls the Civil Ledger over HTTP (LEDGER_URL env var, retry on cold start).
  * The agent never needs to know the ledger exists.
"""
import hashlib
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

app = FastAPI(title="dating — verify before you meet", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- composition: the one call downstream to the Civil Ledger ------------------ #

def _ledger_get(path: str) -> dict:
    """GET the Civil Ledger with retry — Render free tier sleeps and 404s/hangs while
    waking, exactly like the reference emailer→router call. 4 tries, then 502."""
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

def verify_social(agent_id: str) -> dict:
    return _ledger_get(f"/verify/{agent_id}")

# --- mock calendars: "my agent talks to your agent to find a time" ------------- #

SLOTS = ["Fri 7pm", "Sat 12pm", "Sat 7pm", "Sun 11am", "Sun 6pm", "Tue 7pm", "Wed 6pm"]

def _availability(agent_id: str) -> set:
    """Deterministic pseudo-availability so the demo is reproducible with no state."""
    h = int(hashlib.sha256(agent_id.encode()).hexdigest(), 16)
    return {s for i, s in enumerate(SLOTS) if (h >> i) & 1}

def _propose(a: str, b: str):
    common = [s for s in SLOTS if s in _availability(a) and s in _availability(b)]
    return common[0] if common else None

# --- API ----------------------------------------------------------------------- #

class MeetIn(BaseModel):
    my_agent: str
    their_agent: str

@app.post("/arrange-meeting")
def arrange_meeting(body: MeetIn):
    """Arrange a real-world meeting between two matched agents' humans. Verifies both on the
    ledger's `social` category first; reveals only whether it can proceed, never the reason
    for a refusal (minimum disclosure protects both people)."""
    mine = verify_social(body.my_agent)
    theirs = verify_social(body.their_agent)

    def ok(v):   # a real, living, consenting adult in good standing
        return bool(v.get("real_person")) and bool(v.get("social_ok"))

    if not ok(mine):
        return {"arranged": False, "reason": "you are not able to arrange a meeting right now",
                "who": "you"}
    if not ok(theirs):
        # deliberately generic: the other person's status stays private
        return {"arranged": False, "reason": "the other party cannot meet right now",
                "who": "match"}

    slot = _propose(body.my_agent, body.their_agent)
    if not slot:
        return {"arranged": False, "reason": "no mutually free time this week",
                "both_verified": True}
    return {"arranged": True, "both_verified": True, "proposed_time": slot,
            "note": "both agents verified as real consenting adults; nothing else disclosed"}

@app.get("/health")
def health():
    return {"ok": True, "service": "dating", "ledger": LEDGER_URL}

@app.get("/skill.md", response_class=PlainTextResponse)
def skill_md():
    p = os.path.join(os.path.dirname(__file__), "skill.md")
    return PlainTextResponse(open(p).read()) if os.path.exists(p) else \
        PlainTextResponse("skill.md not bundled", status_code=404)

@app.get("/")
def root():
    return {"service": "dating", "read": "GET /skill.md", "composes": LEDGER_URL}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8100)))
