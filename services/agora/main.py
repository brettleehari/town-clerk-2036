"""
agora — "verify before you SELL."
=================================
A marketplace/escrow front door for the agentic town. A seller's agent is about to ship
goods or release escrow to a buyer's agent. Before value moves, THIS service asks the Civil
Ledger (a separate NANDA submission) for a SIGNED, category-scoped verdict on the buyer:
"may the human behind this agent transact in `commerce`?"

Unlike the other consumers, agora uses the ledger's cryptographically signed verdict
(`GET /verify-counterparty`) rather than the coarse status alias — because money is moving
and the merchant wants a receipt it can re-verify later against the ledger's public key.
The verdict's `certificate_id` is returned to the caller for exactly that reason.

The constitutional bars fall out of the ledger for free:
  * a deceased principal cannot buy                      -> PRINCIPAL_DECEASED
  * an incarcerated person has no `commerce` right       -> CATEGORY_NOT_ALLOWED
  * a coma patient's capacity is frozen                  -> CAPACITY_FROZEN
  * an orphaned/rogue agent resolves to no human at all  -> NO_VALID_BINDING / NXAGENT

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
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel

LEDGER_URL = os.environ.get("LEDGER_URL", "http://localhost:8000")
if "://" not in LEDGER_URL:            # Render fromService gives a bare host; add scheme
    LEDGER_URL = "https://" + LEDGER_URL

app = FastAPI(title="agora — verify before you sell", version="1.0.0")
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

def verify_commerce(agent_id: str) -> dict:
    """The signed verdict — a compliance receipt the merchant can re-verify any time
    against the ledger's `/pubkey`, long after the sale settles."""
    return _ledger_get(f"/verify-counterparty?agent_id={agent_id}&category=commerce")

# Plain-language gloss on the ledger's machine reason codes, for the seller's agent.
GLOSS = {
    "PRINCIPAL_DECEASED":  "the buyer is deceased; their estate must transact instead",
    "CATEGORY_NOT_ALLOWED": "the buyer's civil status does not permit commerce",
    "CAPACITY_FROZEN":     "the buyer cannot presently consent to a purchase",
    "NO_VALID_BINDING":    "no verified human behind the buyer's agent",
    "NXAGENT":             "no such agent exists in the town",
    "ROGUE_FLAGGED":       "the buyer's agent has been flagged rogue by the police",
    "BINDING_REVOKED":     "the buyer's agent has been disowned by its human",
}

class SellIn(BaseModel):
    seller_agent: str
    buyer_agent: str
    amount: float

@app.post("/can-i-sell")
def can_i_sell(body: SellIn):
    """Ask whether the seller may complete a sale to this buyer. Returns the ledger's signed
    verdict id on success so the sale carries a re-verifiable compliance receipt."""
    v = verify_commerce(body.buyer_agent)
    code = v.get("reason_code", "REFUSED")

    if not v.get("proceed"):
        return {"sell": False, "reason_code": code,
                "reason": GLOSS.get(code, "the buyer may not transact in commerce"),
                "buyer_agent": body.buyer_agent}

    # `proceed` means "may transact in commerce at all" — it does NOT mean "for any amount".
    # A minor's agent is permitted commerce but carries a spend cap set by their regents, and
    # the ledger returns it. Honouring it is the front door's job: the ledger authorises the
    # category, the marketplace enforces the amount. Without this, agora happily sells a
    # $100,000 item to a fourteen-year-old.
    cap = v.get("spend_cap")
    if cap is not None and body.amount > cap:
        gov = v.get("governed_by") or {}
        who = gov.get("agents") or ([gov["agent"]] if gov.get("agent") else [])
        return {"sell": False, "reason_code": "SPEND_CAP_EXCEEDED",
                "reason": f"the buyer's spend cap is {cap:g}; this sale is {body.amount:g}",
                "buyer_agent": body.buyer_agent, "spend_cap": cap, "amount": body.amount,
                "route_to": who,
                "next_step": ("Ask one of the buyer's regents to authorise the purchase, or "
                              "reduce the amount to the cap.") if who else
                             "Reduce the amount to the cap."}

    return {"sell": True, "reason_code": code, "amount": body.amount,
            "seller_agent": body.seller_agent, "buyer_agent": body.buyer_agent,
            "certificate_id": v.get("cert_id"),
            "note": "signed verdict from the Civil Ledger; re-verify against its /pubkey"}

@app.get("/health")
def health():
    return {"ok": True, "service": "agora", "ledger": LEDGER_URL}

@app.get("/skill.md")
def skill_md():
    """Raw skill, served as text/markdown (RFC 7763) — correct for machines and the registry;
    browsers show it inline. A human who wants a rendered view goes to GET /skill."""
    p = os.path.join(os.path.dirname(__file__), "skill.md")
    return PlainTextResponse(open(p).read(), media_type="text/markdown; charset=utf-8") \
        if os.path.exists(p) else PlainTextResponse("skill.md not bundled", status_code=404)

@app.get("/skill")
def skill_rendered():
    """A rendered, human-readable view of skill.md — fetches the raw /skill.md same-origin and
    renders it client-side, so the one file stays the source of truth. Agents use /skill.md."""
    p = os.path.join(os.path.dirname(__file__), "skill.html")
    return HTMLResponse(open(p).read()) if os.path.exists(p) else \
        HTMLResponse("<h1>skill.html not bundled</h1>", status_code=404)

@app.get("/")
def root():
    return {"service": "agora", "read": "GET /skill.md", "rendered": "GET /skill",
            "composes": LEDGER_URL}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8105)))
