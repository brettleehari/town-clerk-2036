"""
scenario_api.py — the runnable scenario plane for hospital-window.

Serves the SKILL.md scenario playbook as an API, so an agent can discover,
inspect, compose, and execute stories end-to-end without parsing prose:

    GET  /scenarios            — the menu: seeded demos + any custom scenarios
    GET  /scenarios/actions    — the action vocabulary for composing new ones
    GET  /scenarios/{id}       — exact steps: method, url, body, expectations,
                                 and a ready-to-paste curl for each
    POST /scenarios            — define a NEW scenario from whitelisted actions
    POST /scenarios/{id}/run   — execute a scenario against the live town and
                                 return a step-by-step transcript

All writes run BEHIND this application: the hospital/court/police role keys
live server-side and never appear in any response. A caller — human or agent —
composes scenarios only from the whitelisted action vocabulary below, so a
custom scenario can do nothing the town's constitution would not allow anyway.

Scenarios that write civil status require {"confirm": true} on /run (a 428
refuses otherwise). Cleanup steps always execute, even when earlier steps fail.

Integration (services/hospital-window/):

    # app.py
    from scenario_api import router as scenario_router
    app.include_router(scenario_router)

    # requirements.txt
    httpx

Environment (all optional — defaults are the live deployment):

    SELF_URL      base URL of this service   (default https://hospital-window.onrender.com)
    LEDGER_URL    base URL of the ledger     (default https://civil-ledger.onrender.com)
    COURT_KEY / HOSPITAL_ATTEST_KEY / POLICE_KEY
                  role keys for scenario steps (default the seeded sandbox keys)

Custom scenarios are held in memory: a redeploy or reseed clears them.
"""

import json
import os
import re
from typing import Any, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(tags=["scenarios"])

SELF = os.getenv("SELF_URL", "https://hospital-window.onrender.com").rstrip("/")
LEDGER = os.getenv("LEDGER_URL", "https://civil-ledger.onrender.com").rstrip("/")
KEYS = {
    "court": os.getenv("COURT_KEY", "sk_seed_court"),
    "hospital": os.getenv("HOSPITAL_ATTEST_KEY", "sk_seed_hospital"),
    "police": os.getenv("POLICE_KEY", "sk_seed_police"),
}
BASES = {"hospital": SELF, "ledger": LEDGER}
MAX_CUSTOM_SCENARIOS = 50
MAX_STEPS = 20

# The httpx client /run uses. A test can swap this for one whose transport routes to
# in-process apps (see services/test_compose.py); production uses a plain networked client.
def _client_factory():
    return httpx.AsyncClient(timeout=30.0)


# ---------------------------------------------------------------------------
# Step helpers — each step is a plain dict so /scenarios/{id} can serve it.
# ---------------------------------------------------------------------------

def step(
    title: str,
    method: str,
    service: str,
    path: str,
    body: Optional[dict] = None,
    key: Optional[str] = None,          # "court" | "hospital" | "police"
    expect_status: Optional[list] = None,
    expect: Optional[dict] = None,      # dotted-path -> expected value, in JSON body
    cleanup: bool = False,
    note: Optional[str] = None,
) -> dict:
    return {
        "title": title,
        "method": method,
        "service": service,
        "path": path,
        "body": body,
        "key_role": key,
        "expect_status": expect_status or [200],
        "expect": expect or {},
        "cleanup": cleanup,
        "note": note,
    }


def admit(agent, **kw):
    kw.setdefault("expect", {"status": "hospitalized"})
    return step(f"Admit {agent}", "POST", "hospital", "/admit",
                {"patient_agent": agent}, **kw)


def discharge(agent, **kw):
    kw.setdefault("expect", {"status": "active"})
    return step(f"Discharge {agent}", "POST", "hospital", "/discharge",
                {"patient_agent": agent}, **kw)


def declare(agent, **kw):
    kw.setdefault("expect", {"status": "incapacitated"})
    return step(f"Declare {agent} incapacitated", "POST", "hospital",
                "/declare-incapacitated", {"patient_agent": agent}, **kw)


def verify_cp(agent, category, proceed=None, reason=None, title=None, **kw):
    exp = kw.pop("expect", {})
    if proceed is not None:
        exp.setdefault("proceed", proceed)
    if reason:
        exp.setdefault("reason_code", reason)
    return step(
        title or f"Town checks {agent} for {category}",
        "GET", "ledger", f"/verify-counterparty?agent_id={agent}&category={category}",
        expect=exp, **kw,
    )


def recover(principal, **kw):
    kw.setdefault("cleanup", True)
    kw.setdefault("expect_status", [200, 409])  # 409 = already recovered; harmless
    return step(f"Hospital declares {principal} recovered", "POST", "ledger",
                "/attestations",
                {"principal_id": principal, "event": "declare_recovered", "detail": {}},
                key="hospital", **kw)


# ---------------------------------------------------------------------------
# The action vocabulary — the ONLY building blocks a custom scenario may use.
# The role keys stay behind this wall; a caller names an action, never a key.
# ---------------------------------------------------------------------------

ACTIONS: dict[str, dict] = {
    "health": {
        "write": False, "required": [],
        "doc": "Liveness check on the admitting desk.",
        "build": lambda p: step("Is the desk awake?", "GET", "hospital", "/health"),
    },
    "admit": {
        "write": True, "required": ["patient_agent"],
        "doc": "Admit a resident as a conscious inpatient (status -> hospitalized).",
        "build": lambda p: admit(p["patient_agent"]),
    },
    "discharge": {
        "write": True, "required": ["patient_agent"],
        "doc": "Return an inpatient to active (reverses admit).",
        "build": lambda p: discharge(p["patient_agent"]),
    },
    "declare_incapacitated": {
        "write": True, "required": ["patient_agent"],
        "doc": "Freeze a patient's capacity town-wide (status -> incapacitated).",
        "build": lambda p: declare(p["patient_agent"]),
    },
    "verify_counterparty": {
        "write": False, "required": ["agent"],
        "doc": "Signed proceed/refuse verdict for an agent in a category "
               "(param 'category', default commerce). The town's trust check.",
        "build": lambda p: verify_cp(p["agent"], p.get("category", "commerce")),
    },
    "verify": {
        "write": False, "required": ["agent"],
        "doc": "Coarse civil status of the human behind an agent.",
        "build": lambda p: step(f"Verify {p['agent']}", "GET", "ledger",
                                f"/verify/{p['agent']}"),
    },
    "resolve": {
        "write": False, "required": ["agent"],
        "doc": "The signed chain from agent to human (who is behind this agent?).",
        "build": lambda p: step(f"Resolve {p['agent']}", "GET", "ledger",
                                f"/resolve/{p['agent']}"),
    },
    "appoint_guardian": {
        "write": True, "required": ["principal_id", "guardian_agent"],
        "doc": "Court appoints a guardian for a principal (court key, held server-side).",
        "build": lambda p: step(
            f"Court appoints {p['guardian_agent']} guardian of {p['principal_id']}",
            "POST", "ledger", "/attestations",
            {"principal_id": p["principal_id"], "event": "appoint_guardian",
             "detail": {"agent_id": p["guardian_agent"]}},
            key="court", expect_status=[200, 409]),
    },
    "declare_recovered": {
        "write": True, "required": ["principal_id"],
        "doc": "Hospital restores legal capacity (the only exit from incapacitated).",
        "build": lambda p: recover(p["principal_id"], cleanup=False,
                                   expect_status=[200, 409]),
    },
    "flag_rogue": {
        "write": True, "required": ["agent"],
        "doc": "Police flag an agent as rogue — the town refuses it everywhere.",
        "build": lambda p: step(f"Police flag {p['agent']} as rogue", "POST", "ledger",
                                "/attestations",
                                {"event": "flag_rogue",
                                 "detail": {"agent_id": p["agent"]}},
                                key="police", expect={"rogue": True}),
    },
    "clear_flag": {
        "write": True, "required": ["agent"],
        "doc": "Police clear a rogue flag.",
        "build": lambda p: step(f"Police clear the flag on {p['agent']}", "POST",
                                "ledger", "/attestations",
                                {"event": "clear_flag",
                                 "detail": {"agent_id": p["agent"]}},
                                key="police", expect_status=[200, 409]),
    },
}


# ---------------------------------------------------------------------------
# The seeded playbook — one entry per SKILL.md scenario, same ids, same morals.
# ---------------------------------------------------------------------------

SCENARIOS: dict[str, dict] = {
    "round-trip": {
        "name": "The round trip (safe first write)",
        "moral": "Writes work, discharge reverses admit, and hospitalization costs no rights.",
        "side_effects": "reversible — ends where it started",
        "writes": True,
        "steps": [
            admit("a-gwen-01"),
            verify_cp("a-gwen-01", "commerce", True,
                      title="A conscious inpatient can still shop"),
            discharge("a-gwen-01", cleanup=True),
        ],
    },
    "incapacity-arc": {
        "name": "The full incapacity arc (the flagship)",
        "moral": "One attestation restructures the town; guardianship routes; recovery flips it back.",
        "side_effects": "reversible — cleanup restores the patient",
        "writes": True,
        "steps": [
            step("Court appoints Gwen a guardian", "POST", "ledger", "/attestations",
                 {"principal_id": "p-gwen-alcott", "event": "appoint_guardian",
                  "detail": {"agent_id": "a-ada-01"}},
                 key="court", expect_status=[200, 409],
                 note="409 means a guardian is already on file from an earlier run — fine"),
            declare("a-gwen-01"),
            verify_cp("a-gwen-01", "commerce", False, "CAPACITY_FROZEN",
                      title="The marketplace now refuses her"),
            recover("p-gwen-alcott"),
            step("Confirm she is restored", "GET", "ledger", "/verify/a-gwen-01",
                 expect={"status": "active"}, cleanup=True),
        ],
    },
    "state-machine": {
        "name": "The state machine says no",
        "moral": "Only lawful transitions pass; each 409 names the patient's real status.",
        "side_effects": "none — every call exists to be refused",
        "writes": False,
        "steps": [
            step("Discharge someone never admitted", "POST", "hospital", "/discharge",
                 {"patient_agent": "a-gwen-01"}, expect_status=[409]),
            step("Declare the already-frozen", "POST", "hospital",
                 "/declare-incapacitated", {"patient_agent": "a-june-01"},
                 expect_status=[409]),
            step("Admit the dead", "POST", "hospital", "/admit",
                 {"patient_agent": "a-silas-01"}, expect_status=[409]),
        ],
    },
    "impostor": {
        "name": "The impostor at the admitting desk",
        "moral": "You cannot write civil status for an agent that represents nobody.",
        "side_effects": "none",
        "writes": False,
        "steps": [
            step("Try to admit an agent with no human behind it", "POST", "hospital",
                 "/admit", {"patient_agent": "a-shadow-99"}, expect_status=[404]),
        ],
    },
    "fleet-freeze": {
        "name": "One patient, a whole fleet of agents",
        "moral": "Status attaches to the human; every agent they own re-decides at once.",
        "side_effects": "reversible — cleanup restores the patient",
        "writes": True,
        "steps": [
            step("All three of Bram's agents resolve to one human", "GET", "ledger",
                 "/resolve/a-bram-01", expect={"principal_ref": "p-bram-kessler"}),
            admit("a-bram-01"),
            verify_cp("a-bram-shop", "commerce", True,
                      title="Conscious inpatient: his shop agent still proceeds"),
            declare("a-bram-01"),
            verify_cp("a-bram-work", "commerce", False, "CAPACITY_FROZEN",
                      title="An agent this desk never named is now frozen"),
            recover("p-bram-kessler"),
            step("Confirm the fleet is restored", "GET", "ledger", "/verify/a-bram-01",
                 expect={"status": "active"}, cleanup=True),
        ],
    },
    "rogue-agent": {
        "name": "The agent that didn't get the memo (crime without a human criminal)",
        "moral": ("A crime committed, caught, and prosecuted with no human on either "
                  "side — and recovery never launders the rogue agent's record."),
        "side_effects": "reversible — cleanup recovers the patient and clears the flag",
        "writes": True,
        "steps": [
            admit("a-bram-01", note="Bram collapses; nobody tells his agents anything"),
            declare("a-bram-01"),
            verify_cp("a-bram-shop", "commerce", False, "CAPACITY_FROZEN",
                      title="His shopping agent tries to spend — refused at the till"),
            step("The storefront reports the persistent agent to the police",
                 "POST", "ledger", "/attestations",
                 {"event": "flag_rogue", "detail": {"agent_id": "a-bram-shop"}},
                 key="police", expect={"rogue": True}),
            step("Bram wakes — one attestation recovers him", "POST", "ledger",
                 "/attestations",
                 {"principal_id": "p-bram-kessler", "event": "declare_recovered",
                  "detail": {}},
                 key="hospital"),
            verify_cp("a-bram-01", "commerce", True,
                      title="His innocent agents are restored the instant he is"),
            verify_cp("a-bram-shop", "commerce", False, "ROGUE_FLAGGED",
                      title="The one that misbehaved stays refused — trust is not health"),
            step("Police clear the flag", "POST", "ledger", "/attestations",
                 {"event": "clear_flag", "detail": {"agent_id": "a-bram-shop"}},
                 key="police", cleanup=True, expect_status=[200, 409]),
            verify_cp("a-bram-shop", "commerce", True, cleanup=True,
                      title="Ward and record both as we found them"),
        ],
    },
    "coma-vulture": {
        "name": "The coma vulture",
        "moral": ("Incapacity is exactly when impostors circle — the ledger tells a "
                  "court-appointed guardian from a claimed one."),
        "side_effects": "none — two open reads",
        "writes": False,
        "steps": [
            verify_cp("a-shadow-99", "medical", False, "NO_VALID_BINDING",
                      title='"I handle June\'s affairs" — the claim is not evidence'),
            step("Who may actually act for June?", "GET", "ledger", "/verify/a-june-01",
                 expect={"status": "incapacitated",
                         "governed_by.agent": "a-okafor-g"}),
        ],
    },
}

CUSTOM: dict[str, dict] = {}  # in-memory; a redeploy clears them


def _lookup(sid: str) -> Optional[dict]:
    return SCENARIOS.get(sid) or CUSTOM.get(sid)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _url(s: dict) -> str:
    return BASES[s["service"]] + s["path"]


def _headers(s: dict) -> dict:
    """Public view of a step's headers — key values are always redacted."""
    h = {}
    if s["body"] is not None:
        h["Content-Type"] = "application/json"
    if s["key_role"]:
        h["X-API-Key"] = f"<{s['key_role']} key — held by this service>"
    return h


def _curl(s: dict) -> str:
    parts = ["curl"]
    if s["method"] != "GET":
        parts.append(f"-X {s['method']}")
    parts.append(f'"{_url(s)}"')
    for k, v in _headers(s).items():
        parts.append(f"-H '{k}: {v}'")
    if s["body"] is not None:
        parts.append(f"-d '{json.dumps(s['body'])}'")
    return " ".join(parts)


def _public_step(s: dict) -> dict:
    return {
        "title": s["title"],
        "note": s["note"],
        "method": s["method"],
        "url": _url(s),
        "headers": _headers(s),
        "body": s["body"],
        "expect_status": s["expect_status"],
        "expect": s["expect"],
        "cleanup": s["cleanup"],
        "curl": _curl(s),
    }


def _public_scenario(sid: str, sc: dict) -> dict:
    return {
        "id": sid,
        "name": sc["name"],
        "moral": sc["moral"],
        "side_effects": sc["side_effects"],
        "writes": sc["writes"],
        "custom": sid in CUSTOM,
        "steps": [_public_step(s) for s in sc["steps"]],
        "run": f"POST {SELF}/scenarios/{sid}/run"
               + (' {"confirm": true}' if sc["writes"] else ""),
    }


# ---------------------------------------------------------------------------
# Composing new scenarios (POST /scenarios)
# ---------------------------------------------------------------------------

class CustomStep(BaseModel):
    action: str
    params: dict = Field(default_factory=dict)
    title: Optional[str] = None
    expect_status: Optional[list[int]] = None
    expect: Optional[dict] = None
    cleanup: bool = False
    note: Optional[str] = None


class CustomScenario(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    moral: str = ""
    steps: list[CustomStep] = Field(min_length=1, max_length=MAX_STEPS)


def _compile_step(cs: CustomStep, idx: int) -> dict:
    spec = ACTIONS.get(cs.action)
    if not spec:
        raise HTTPException(
            422, f"step {idx}: unknown action '{cs.action}'. "
                 f"Allowed: {sorted(ACTIONS)} — see GET /scenarios/actions")
    missing = [k for k in spec["required"] if k not in cs.params]
    if missing:
        raise HTTPException(
            422, f"step {idx}: action '{cs.action}' needs params {missing}")
    for k, v in cs.params.items():
        if not isinstance(v, str) or not re.fullmatch(r"[a-zA-Z0-9_\-]{1,64}", v):
            raise HTTPException(
                422, f"step {idx}: param '{k}' must be a short id-like string")
    s = spec["build"](cs.params)
    if cs.title:
        s["title"] = cs.title
    if cs.expect_status:
        s["expect_status"] = cs.expect_status
    if cs.expect is not None:
        s["expect"] = cs.expect
    if cs.note:
        s["note"] = cs.note
    s["cleanup"] = cs.cleanup
    s["action"] = cs.action
    return s


@router.get("/scenarios/actions")
async def list_actions():
    """The vocabulary for composing a new scenario via POST /scenarios."""
    return {
        "actions": {
            name: {"write": a["write"], "required_params": a["required"],
                   "doc": a["doc"]}
            for name, a in ACTIONS.items()
        },
        "how": ("POST /scenarios with {\"name\", \"moral\", \"steps\":[{\"action\", "
                "\"params\", \"expect\"?, \"expect_status\"?, \"cleanup\"?}]}. "
                "All writes execute behind this service with its own role keys — "
                "you never handle a credential. Include cleanup steps that put "
                "every patient back; cleanup steps always run."),
        "example": {
            "name": "My own admission story",
            "moral": "What I wanted to prove.",
            "steps": [
                {"action": "admit", "params": {"patient_agent": "a-gwen-01"}},
                {"action": "verify_counterparty",
                 "params": {"agent": "a-gwen-01", "category": "commerce"},
                 "expect": {"proceed": True}},
                {"action": "discharge", "params": {"patient_agent": "a-gwen-01"},
                 "cleanup": True},
            ],
        },
    }


@router.post("/scenarios", status_code=201)
async def create_scenario(body: CustomScenario):
    """Register a new scenario composed from the whitelisted action vocabulary."""
    if len(CUSTOM) >= MAX_CUSTOM_SCENARIOS:
        raise HTTPException(429, "custom scenario limit reached — a redeploy clears them")
    slug = re.sub(r"[^a-z0-9]+", "-", body.name.lower()).strip("-")[:40] or "scenario"
    sid = slug
    n = 2
    while _lookup(sid) or sid == "actions":
        sid, n = f"{slug}-{n}", n + 1
    steps = [_compile_step(cs, i + 1) for i, cs in enumerate(body.steps)]
    writes = any(ACTIONS[s["action"]]["write"] for s in steps)
    CUSTOM[sid] = {
        "name": body.name,
        "moral": body.moral or "A custom scenario.",
        "side_effects": ("writes civil status — include cleanup steps"
                         if writes else "none — reads only"),
        "writes": writes,
        "steps": steps,
    }
    return _public_scenario(sid, CUSTOM[sid])


# ---------------------------------------------------------------------------
# Listing, inspecting, running
# ---------------------------------------------------------------------------

@router.get("/scenarios")
async def list_scenarios():
    """The runnable scenario menu — the SKILL.md playbook, machine-readable."""
    everything = {**SCENARIOS, **CUSTOM}
    return {
        "service": "hospital-window",
        "scenarios": [
            {
                "id": sid,
                "name": sc["name"],
                "moral": sc["moral"],
                "side_effects": sc["side_effects"],
                "writes": sc["writes"],
                "custom": sid in CUSTOM,
                "steps": len(sc["steps"]),
                "detail": f"{SELF}/scenarios/{sid}",
                "run": f"POST {SELF}/scenarios/{sid}/run"
                       + (' {"confirm": true}' if sc["writes"] else ""),
            }
            for sid, sc in everything.items()
        ],
        "compose_your_own": f"GET {SELF}/scenarios/actions, then POST {SELF}/scenarios",
        "how": ("GET a scenario for its exact steps, or POST /scenarios/{id}/run to "
                "execute it end-to-end and get a transcript. Scenarios marked "
                "writes:true change civil status (reversibly — cleanup is built in) "
                "and require {\"confirm\": true}: confirm with your human first. "
                "All role keys stay behind this service."),
    }


@router.get("/scenarios/{sid}")
async def get_scenario(sid: str):
    sc = _lookup(sid)
    if not sc:
        raise HTTPException(404, f"no scenario '{sid}' — see GET /scenarios")
    return _public_scenario(sid, sc)


class RunRequest(BaseModel):
    confirm: bool = False


@router.post("/scenarios/{sid}/run")
async def run_scenario(sid: str, req: Optional[RunRequest] = None):
    sc = _lookup(sid)
    if not sc:
        raise HTTPException(404, f"no scenario '{sid}' — see GET /scenarios")
    if sc["writes"] and not (req and req.confirm):
        raise HTTPException(
            428,
            f"'{sid}' performs consequential (reversible) writes to the Civil Ledger. "
            'Confirm with your human, then POST again with {"confirm": true}.',
        )

    transcript, failed = [], False
    async with _client_factory() as client:
        for s in sc["steps"]:
            headers = {}
            if s["key_role"]:
                headers["X-API-Key"] = KEYS[s["key_role"]]
            try:
                r = await client.request(
                    s["method"], _url(s),
                    json=s["body"] if s["body"] is not None else None,
                    headers=headers)
                try:
                    resp_body = r.json()
                except ValueError:
                    resp_body = r.text
                ok, problems = _check(s, r.status_code, resp_body)
                entry = {"title": s["title"], "call": f"{s['method']} {_url(s)}",
                         "http": r.status_code, "response": resp_body,
                         "pass": ok, "problems": problems}
            except httpx.HTTPError as e:
                entry = {"title": s["title"], "call": f"{s['method']} {_url(s)}",
                         "http": None, "response": str(e),
                         "pass": False, "problems": ["transport error"]}
            if s["cleanup"]:
                entry["cleanup"] = True
            if s.get("note"):
                entry["note"] = s["note"]
            transcript.append(entry)
            failed = failed or not entry["pass"]
            # Never stop early: later steps include the cleanup that restores
            # the town, and a refusal transcript is itself the demonstration.

    return {
        "scenario": sid,
        "name": sc["name"],
        "ok": not failed,
        "moral": sc["moral"],
        "transcript": transcript,
    }


# ---------------------------------------------------------------------------
# Expectation checking
# ---------------------------------------------------------------------------

def _dig(obj: Any, dotted: str) -> Any:
    for part in dotted.split("."):
        if not isinstance(obj, dict) or part not in obj:
            return None
        obj = obj[part]
    return obj


def _check(s: dict, status: int, body: Any) -> tuple[bool, list]:
    problems = []
    if status not in s["expect_status"]:
        problems.append(f"expected HTTP {s['expect_status']}, got {status}")
    # Field expectations only apply to a non-error answer.
    if status < 400:
        for path, want in (s["expect"] or {}).items():
            got = _dig(body, path) if isinstance(body, dict) else None
            if got != want:
                problems.append(f"expected {path}={want!r}, got {got!r}")
    return (not problems, problems)
