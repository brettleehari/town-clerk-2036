"""
hospital-window — "the institution that CHANGES a civil status."
===============================================================
The second PRODUCER front door (town-hall is the first). Consumers (dating, babysit, care,
hiring, agora) READ the Civil Ledger. Institutions WRITE it. hospital-window is Fairview
Hospital's admitting desk: it admits a patient, discharges them, or declares them
incapacitated — and each write immediately changes what every consumer service will allow.

That is the whole point of a shared civil ledger: declare a resident incapacitated here, and
care-proxy instantly routes their medical decisions to their court-appointed guardian, while
dating and hiring instantly refuse them. No consumer had to be told.

It self-registers as a HOSPITAL (or uses HOSPITAL_KEY), resolves the patient's agent to its
principal, then calls the ledger's `POST /attestations` with the matching civil event.

Composition: own submission + own skill.md; backend calls the ledger over HTTP
(LEDGER_URL env var, retry on cold start). The agent only ever calls this service.
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
HOSPITAL_KEY = os.environ.get("HOSPITAL_KEY")   # optional; else self-register below

app = FastAPI(title="hospital-window — admitting desk", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def _ledger(method: str, path: str, **kw) -> dict:
    """Call the Civil Ledger, retrying only what retrying can fix. A cold-started free-tier
    host hangs or 5xxs, so back off and try again. But a 4xx is the ledger's considered
    answer — the FSM refusing an illegal transition, say — and four retries would just cost
    the caller 15 seconds before returning the same thing. Surface it immediately."""
    last = None
    for attempt in range(4):
        try:
            r = httpx.request(method, f"{LEDGER_URL}{path}", timeout=65, **kw)
        except Exception as e:            # noqa: BLE001 — transport failure; cold start
            last = e
            time.sleep(1.5 * (attempt + 1))
            continue
        if 400 <= r.status_code < 500:
            raise HTTPException(r.status_code, _detail(r))
        if r.status_code >= 500:
            last = f"ledger returned {r.status_code}"
            time.sleep(1.5 * (attempt + 1))
            continue
        return r.json()
    raise HTTPException(502, f"civil ledger unreachable at {LEDGER_URL}: {last}")

def _detail(r) -> str:
    try:
        return r.json().get("detail", r.text)
    except Exception:                     # noqa: BLE001 — non-JSON error body
        return r.text

_key_cache = {"hospital": HOSPITAL_KEY}

def hospital_key() -> str:
    """Obtain a hospital API key — from env, or self-register with the ledger (the sandbox
    allows open institution registration). Cached for the process lifetime."""
    if _key_cache.get("hospital"):
        return _key_cache["hospital"]
    reg = _ledger("POST", "/institutions/register",
                  json={"name": "Fairview Hospital (admitting window)", "role": "hospital"})
    _key_cache["hospital"] = reg["api_key"]
    return _key_cache["hospital"]

def principal_of(agent_id: str) -> str:
    """An institution attests about a PERSON, not an agent — resolve the agent to the human
    behind it first. An unrooted/rogue agent has no principal, so nothing can be attested."""
    res = _ledger("GET", f"/resolve/{agent_id}")
    if not res.get("resolved") or not res.get("principal_ref"):
        raise HTTPException(404, f"no verified human behind {agent_id} "
                                 f"({res.get('code', 'UNRESOLVED')})")
    return res["principal_ref"]

def _post_attestation(pid: str, event: str) -> None:
    """POST the event, re-registering once if our cached hospital key has gone stale.

    The ledger can be reset (POST /admin/reset-seed), which deletes every institution — and
    with it our self-registered key. Without this retry the next write fails with `401 unknown
    institution key`, which the caller has no way to act on."""
    try:
        _ledger("POST", "/attestations",
                json={"principal_id": pid, "event": event, "detail": {"by": "hospital-window"}},
                headers={"X-API-Key": hospital_key()})
    except HTTPException as e:
        if e.status_code != 401:
            raise
        _key_cache["hospital"] = None if not HOSPITAL_KEY else HOSPITAL_KEY
        _ledger("POST", "/attestations",
                json={"principal_id": pid, "event": event, "detail": {"by": "hospital-window"}},
                headers={"X-API-Key": hospital_key()})

def _attest(agent_id: str, event: str) -> dict:
    """Write one civil event, then read the patient back so the caller sees the new world."""
    pid = principal_of(agent_id)
    try:
        _post_attestation(pid, event)
    except HTTPException as e:
        # ONLY a 409 is the FSM refusing an unlawful transition. Translating every 4xx into
        # "illegal transition" once made a stale API key look like a clinical impossibility.
        if e.status_code != 409:
            raise
        now = _ledger("GET", f"/verify/{agent_id}")
        raise HTTPException(409, f"illegal transition '{event}' for a patient whose civil "
                                 f"status is '{now.get('status')}'")
    after = _ledger("GET", f"/verify/{agent_id}")
    out = {"ok": True, "event": event, "patient_agent": agent_id, "principal_id": pid,
           "status": after.get("status"), "social_ok": after.get("social_ok")}
    if after.get("governed_by"):
        out["now_governed_by"] = after["governed_by"]   # the consumer-visible consequence
    return out

class PatientIn(BaseModel):
    patient_agent: str

@app.post("/admit")
def admit(body: PatientIn):
    """Admit a resident as a conscious inpatient. They keep every civil right (the ledger's
    ACL says a conscious inpatient may still contract, meet, and vote)."""
    return _attest(body.patient_agent, "admit")

@app.post("/discharge")
def discharge(body: PatientIn):
    """Discharge an inpatient back to `active`."""
    return _attest(body.patient_agent, "discharge")

@app.post("/declare-incapacitated")
def declare_incapacitated(body: PatientIn):
    """Declare a patient incapacitated (e.g. a coma). Their capacity freezes town-wide:
    care-proxy now routes their medical decisions to their guardian, and every social,
    commercial, and employment gate closes — instantly, with no consumer notified."""
    return _attest(body.patient_agent, "declare_incapacitated")

@app.get("/health")
def health():
    return {"ok": True, "service": "hospital-window", "ledger": LEDGER_URL}

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
    return {"service": "hospital-window", "read": "GET /skill.md", "rendered": "GET /skill",
            "composes": LEDGER_URL}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8106)))
