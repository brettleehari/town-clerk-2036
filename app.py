"""
KYA — Know Your Agent · The Civil Ledger
=========================================
A two-sided civic trust layer for an agentic city.

Core idea (the "constitution"):
  * Every agent in the city must resolve, DNS-style, to a human (or corporation)
    principal, through a chain of signing authorities rooted at the city's
    constitutional root key. An agent that does not resolve is NXAGENT (a rogue).
  * A small set of constitutional institutions (registrar, court, hospital,
    coroner, police) are the ONLY writers of civic facts. Everyone else reads.
  * A human's real-world civil status (alive / minor / hospitalized / incapacitated
    / incarcerated / missing / deceased) governs, via an ACL over transaction
    categories, what that human's agent may lawfully do.

CS backbone:
  * Ed25519 signatures (PyNaCl) on every verdict + a DNSSEC-style resolution chain.
  * Hierarchical namespace with TTL'd, signed records (root -> institution -> principal -> agent).
  * A validated finite state machine for civil status transitions.
  * Threshold attestation (k-of-2) for irreversible death, with a Lazarus contest window.
  * Sprawl governance: per-principal agent quotas (rogue-farm / botnet defense).
  * Parental controls: minors' agents run under regent-set ACLs and spend caps.

Single-file FastAPI app, SQLite persistence, zero external services. Deploy anywhere.
"""

import base64
import hashlib
import json
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from typing import Optional
from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (FileResponse, HTMLResponse, JSONResponse,
                               PlainTextResponse, RedirectResponse)
from nacl import signing
from pydantic import BaseModel

# --------------------------------------------------------------------------- #
#  Constants: the constitution's fixed parameters                             #
# --------------------------------------------------------------------------- #

DB_PATH = os.environ.get("KYA_DB", "kya.db")
# The town runs in 2036. The host clock is a decade behind, so we shift every
# timestamp forward by exactly ten years (2026-07-10 -> 2036-07-10, accounting
# for the 3 leap days in between). Overridable via env for testing.
TIME_OFFSET_SECONDS = int(os.environ.get("KYA_TIME_OFFSET_SECONDS", 3653 * 86400))
CERT_TTL_SECONDS = 300          # verdicts expire in 5 minutes (no stale-alive replay)
RECORD_TTL_SECONDS = 3600       # resolution records' TTL (DNS-style)
LAZARUS_WINDOW_SECONDS = 72 * 3600
CORONER_THRESHOLD = 2           # k-of-n independent coroner attestations for death
MAX_AGENTS_PER_PRINCIPAL = 5    # sprawl cap for individuals
MAX_AGENTS_PER_CORP = 25        # sprawl cap for corporations
MINOR_MAJORITY_AGE_TAG = 18     # informational
DEFAULT_INHERIT_DAYS = 30       # default term an heir may steward an inherited agent
VOTING_STATUSES = {"active", "hospitalized"}  # who may cast a civic vote (adult & present)
TOWN_NAME = os.environ.get("TOWN_NAME", "Alford, Massachusetts")

# `social` = arranging a real-world/personal meeting between the humans behind two
# agents (dating, meetups) — the "verify before you MEET" category. It is adults-only:
# a minor's agent can never arrange an adult meeting, and an incarcerated person's agent
# is barred (a prisoner with contraband internet cannot run romance scams or coordinate
# meetings from inside). The bars fall out of the ACLs below for free.
CATEGORIES = ["financial", "commerce", "legal", "medical", "family_support", "estate",
              "civic", "social"]

# ACL profile per civil status: which categories the principal's agent may transact.
# "self" means the principal governs; specific statuses narrow the set.
STATUS_ACL = {
    "active":         set(CATEGORIES) - {"estate"},                          # consenting adult: incl. social
    "minor":          {"commerce", "medical", "family_support", "civic"},   # NO social (age-gate); regent-capped
    "hospitalized":   set(CATEGORIES) - {"estate"},                          # conscious inpatient keeps rights (incl. social)
    "incapacitated":  {"legal", "medical"},                                  # coma: NO financial/commerce/social; routed to guardian
    "incarcerated":   {"legal", "family_support"},                           # jail: NO social/commerce — crime-prevention bar; court may override via detail.acl
    "missing":        set(),                                                 # frozen after report
    "deceased":       {"estate"},                                            # executor only
}

# Which status is "financial-capable" — used for the guardian-routing message.
GUARDIAN_ROUTED = {"incapacitated", "minor"}

# Finite state machine: allowed civil-status transitions and the institution role
# permitted to drive each. (from_status, event) -> (to_status, required_role)
FSM = {
    ("unborn", "birth"):                    ("minor", "registrar"),
    ("minor", "majority_handover"):         ("active", "registrar"),
    ("minor", "emancipate"):                ("active", "court"),
    ("active", "admit"):                    ("hospitalized", "hospital"),
    ("hospitalized", "discharge"):          ("active", "hospital"),
    ("active", "declare_incapacitated"):    ("incapacitated", "hospital"),
    ("hospitalized", "declare_incapacitated"): ("incapacitated", "hospital"),
    ("incapacitated", "declare_recovered"): ("active", "hospital"),
    ("active", "sentence"):                 ("incarcerated", "court"),
    ("incarcerated", "release"):            ("active", "court"),
    ("active", "report_missing"):           ("missing", "police"),
    ("missing", "found"):                   ("active", "police"),
    ("active", "death"):                    ("deceased", "coroner"),
    ("hospitalized", "death"):              ("deceased", "coroner"),
    ("incapacitated", "death"):             ("deceased", "coroner"),
    ("missing", "death"):                   ("deceased", "coroner"),
    ("incarcerated", "death"):              ("deceased", "coroner"),
}

ROLES = ["registrar", "court", "hospital", "coroner", "police"]

# Events that are not FSM status-transitions but still institution-gated.
AUX_EVENTS = {
    "appoint_guardian": "court",
    "appoint_executor": "court",
    "flag_rogue": "police",
    "clear_flag": "police",
}

# --------------------------------------------------------------------------- #
#  Crypto: the root key + signing helpers                                     #
# --------------------------------------------------------------------------- #

def _seed_from_env(raw: str) -> bytes:
    """Turn KYA_ROOT_SEED into exactly 32 bytes.

    64 hex chars are used verbatim, so an operator can pin an exact key and every previously
    issued certificate keeps verifying. Anything else is hashed to 32 bytes — hosts that
    auto-generate secrets (Render's `generateValue`) hand us a random base64-ish string, and
    the old code fed that straight to bytes.fromhex() and crashed on boot. Hashing is
    deterministic, so the identity is still stable across restarts.
    """
    raw = raw.strip()
    try:
        seed = bytes.fromhex(raw)
        if len(seed) == 32:
            return seed
    except ValueError:
        pass
    return hashlib.sha256(raw.encode()).digest()

def _load_or_create_root_key():
    """The constitutional root of trust. Persisted so restarts keep identity."""
    seed_hex = os.environ.get("KYA_ROOT_SEED")
    if seed_hex:
        seed = _seed_from_env(seed_hex)
    else:
        # Persist a generated seed alongside the DB so a redeploy is stable.
        seed_file = DB_PATH + ".rootseed"
        if os.path.exists(seed_file):
            with open(seed_file) as f:
                seed = bytes.fromhex(f.read().strip())
        else:
            seed = secrets.token_bytes(32)
            with open(seed_file, "w") as f:
                f.write(seed.hex())
    return signing.SigningKey(seed)

ROOT_KEY = _load_or_create_root_key()
ROOT_PUB_B64 = base64.b64encode(bytes(ROOT_KEY.verify_key)).decode()

def canonical(obj: dict) -> bytes:
    """Deterministic JSON for signing: sorted keys, no whitespace."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()

def sign_payload(payload: dict) -> dict:
    """Attach an Ed25519 signature over the canonical form of `payload`."""
    sig = ROOT_KEY.sign(canonical(payload)).signature
    out = dict(payload)
    out["signature"] = base64.b64encode(sig).decode()
    return out

# What each refusal means, and what the caller should do about it. The consuming agent sees
# only this JSON — never our source — so the verdict has to explain itself. Every line obeys
# minimum disclosure: it states the CONSEQUENCE and the remedy, never the private reason a
# principal's capacity is limited. "Frozen" never becomes "in a coma".
_GUIDANCE = {
    "OK": ("Proceed.",
           "Verify `signature` against GET /pubkey, check `valid_until` is still in the future, "
           "then transact within `allowed_categories`."),
    "NO_VALID_BINDING": ("Do not transact. This agent resolves to no human or corporation — it "
                         "represents nobody.",
                         "Refuse. To report it: register as police via POST /institutions/register, "
                         "then POST /attestations {\"event\":\"flag_rogue\",\"detail\":{\"agent_id\":\"…\"}}."),
    "NXAGENT": ("Do not transact. No agent with this id exists in the town.",
                "Check the id. An agent that was never registered has no principal to stand behind it."),
    "ROGUE_FLAGGED": ("Do not transact. Police have flagged this agent; the town refuses it everywhere.",
                      "Refuse. Only a police `clear_flag` attestation lifts this."),
    "PRINCIPAL_DECEASED": ("Do not transact. The principal behind this agent has died.",
                           "Only the executor may act, and only with category=estate."),
    "CAPACITY_FROZEN": ("Do not transact in this category. The principal's capacity is currently frozen.",
                        "This verdict does not disclose why, by design. Refuse, or retry in a "
                        "category listed in `allowed_categories`."),
    "CATEGORY_NOT_ALLOWED": ("Do not transact in this category. The principal's civil status does "
                             "not permit it.",
                             "Retry with one of `allowed_categories`, or refuse."),
    "PRINCIPAL_MISSING": ("Do not transact. The principal is registered missing; every category is frozen.",
                          "Refuse. A police `found` attestation restores them."),
    "BINDING_EXPIRED": ("Do not transact. This agent's authority to act has expired.",
                        "An inherited agent's term has ended — it has been laid to rest."),
    "LAZARUS_WINDOW_OPEN": ("Do not transact. A death record for this principal is under contest.",
                            "Wait for the 72h Lazarus window to close, then re-verify."),
    "UNKNOWN_PRINCIPAL": ("Do not transact. This agent points at a principal the ledger does not know.",
                          "Refuse and report the id."),
}

def explain(payload: dict, category: Optional[str] = None) -> dict:
    """Add `summary` and `next_step` to a verdict so an agent reading only JSON knows what
    happened and what to do next. Both fields are inside the signed body — an explanation you
    could tamper with would be worse than none."""
    out = dict(payload)
    code = out.get("reason_code", "")
    summary, nxt = _GUIDANCE.get(code, ("Do not transact.", "Refuse and re-verify later."))

    if code == "OK":
        cat = f"`{category}`" if category else "the categories listed in `allowed_categories`"
        if "agent_id" in out:                       # /verify-counterparty: about an AGENT
            who = out.get("principal_ref") or "a verified principal"
            hops = len(out.get("resolution_chain") or [])
            summary = (f"Proceed. This agent resolves to {who} through {hops} signing "
                       f"authorities, and may transact in {cat}.")
        else:                                       # /capacity: about a PRINCIPAL, no chain
            summary = (f"Proceed. {out.get('principal_id', 'This principal')} has the civil "
                       f"capacity to transact in {cat}.")
    elif code == "CATEGORY_NOT_ALLOWED" and out.get("allowed_categories"):
        summary += f" They may transact in: {', '.join(out['allowed_categories'])}."

    # A principal governed by someone else is the single most actionable fact in a verdict, so
    # name who acts for them on both the proceed and the refuse path. `governed_by` has three
    # shapes: one agent (guardian/executor), several (regents), or an heir's principal.
    gov = out.get("governed_by")
    if isinstance(gov, dict):
        role = gov.get("role", "proxy")
        if gov.get("agent"):
            who = gov["agent"]
        elif gov.get("agents"):
            who = " or ".join(gov["agents"])
        elif gov.get("principal"):
            who = f"the heir {gov['principal']}"
        else:
            who = None
        if who:
            if code == "OK":
                summary += f" They are governed by {who} ({role}), who acts on their behalf."
                nxt = f"Address the request to {who} ({role}). " + nxt
            else:
                nxt = f"Route the request to {who} ({role}). " + nxt

    out["summary"] = summary
    out["next_step"] = nxt
    if category:
        out["category"] = category          # the receipt names what it authorized
    return out

def sign_verdict(payload: dict, category: Optional[str] = None) -> dict:
    """Every proceed/refuse verdict: explain it, then sign the explanation with it."""
    return sign_payload(explain(payload, category))

def verify_payload(cert: dict) -> bool:
    if not isinstance(cert, dict) or "signature" not in cert:
        return False
    try:
        sig = base64.b64decode(cert["signature"])
        body = {k: v for k, v in cert.items() if k != "signature"}
        ROOT_KEY.verify_key.verify(canonical(body), sig)
        return True
    except Exception:
        # malformed base64, non-canonicalizable body, or a bad signature — all "invalid",
        # never a 500. A verdict either verifies against the root key or it does not.
        return False

def ts() -> int:
    # Town clock: real epoch shifted forward into 2036 (see TIME_OFFSET_SECONDS).
    return int(time.time()) + TIME_OFFSET_SECONDS

def now_iso() -> str:
    return datetime.fromtimestamp(ts(), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# --------------------------------------------------------------------------- #
#  Storage                                                                     #
# --------------------------------------------------------------------------- #

@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS institutions (
            id TEXT PRIMARY KEY, name TEXT, role TEXT, api_key TEXT, created TEXT);
        CREATE TABLE IF NOT EXISTS corporations (
            id TEXT PRIMARY KEY, name TEXT, created TEXT);
        CREATE TABLE IF NOT EXISTS principals (
            id TEXT PRIMARY KEY, name TEXT, status TEXT, kind TEXT,
            guardian_agent TEXT, executor_agent TEXT, regents TEXT,
            principal_key TEXT, acl_override TEXT, spend_cap REAL,
            death_ts INTEGER, will TEXT, birth_year INTEGER, created TEXT);
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY, name TEXT, class TEXT, rogue INTEGER DEFAULT 0,
            created TEXT);
        CREATE TABLE IF NOT EXISTS bindings (
            id TEXT PRIMARY KEY, agent_id TEXT, principal_id TEXT, corporation_id TEXT,
            scope TEXT, status TEXT, issued_by TEXT,
            inherit_until INTEGER, inherit_acl TEXT, created TEXT);
        CREATE TABLE IF NOT EXISTS elections (
            id TEXT PRIMARY KEY, office TEXT, candidates TEXT, closes_ts INTEGER, created TEXT);
        CREATE TABLE IF NOT EXISTS votes (
            id TEXT PRIMARY KEY, election_id TEXT, principal_id TEXT, candidate TEXT, created TEXT,
            UNIQUE(election_id, principal_id));
        CREATE TABLE IF NOT EXISTS attestations (
            id TEXT PRIMARY KEY, principal_id TEXT, event TEXT, role TEXT,
            institution_id TEXT, detail TEXT, created TEXT, ts INTEGER);
        CREATE TABLE IF NOT EXISTS watches (
            id TEXT PRIMARY KEY, target TEXT, callback_url TEXT, created TEXT);
        CREATE TABLE IF NOT EXISTS certificates (
            id TEXT PRIMARY KEY, agent_id TEXT, category TEXT, payload TEXT, created TEXT);
        """)

def new_id(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(4)}"

def store_cert(cert: dict, category: Optional[str]) -> dict:
    """Persist a signed verdict so it can be re-served as a compliance receipt via
    GET /certificates/{cert_id}. The stored payload is the exact signed cert — an
    auditor can re-verify it against /pubkey long after the 5-minute TTL expires."""
    try:
        with db() as c:
            c.execute("INSERT OR REPLACE INTO certificates (id,agent_id,category,payload,created) "
                      "VALUES (?,?,?,?,?)",
                      (cert.get("cert_id"), cert.get("agent_id"), category,
                       json.dumps(cert), now_iso()))
    except Exception:
        pass  # a receipt-store failure must never break the verdict path
    return cert

# --------------------------------------------------------------------------- #
#  Resolution: the DNS-style chain of trust                                   #
# --------------------------------------------------------------------------- #

def resolve_agent(agent_id: str) -> dict:
    """
    Resolve an agent to its principal the way a resolver walks DNS to the root.
    Returns a resolution record with the full authority chain, or NXAGENT.

    Chain: root -> issuing institution -> principal -> binding -> agent
    Each hop is verifiable; the whole record is root-signed with a TTL.
    """
    with db() as c:
        agent = c.execute("SELECT * FROM agents WHERE id=?", (agent_id,)).fetchone()
        if not agent:
            rec = {
                "agent_id": agent_id, "resolved": False, "code": "NXAGENT",
                "chain": [], "ttl": RECORD_TTL_SECONDS, "issued_at": now_iso(),
            }
            return sign_payload(rec)

        binding = c.execute(
            "SELECT * FROM bindings WHERE agent_id=? AND status='active' "
            "ORDER BY created DESC LIMIT 1", (agent_id,)).fetchone()

        chain = [{"level": "root", "authority": "city-root", "pubkey": ROOT_PUB_B64}]

        if not binding:
            rec = {
                "agent_id": agent_id, "agent_class": agent["class"],
                "resolved": False, "code": "NO_VALID_BINDING",
                "rogue": bool(agent["rogue"]),
                "chain": chain, "ttl": RECORD_TTL_SECONDS, "issued_at": now_iso(),
            }
            return sign_payload(rec)

        # Inherited softlink whose term has expired -> the agent is laid to rest.
        if binding["inherit_until"] and ts() > binding["inherit_until"]:
            rec = {
                "agent_id": agent_id, "agent_class": agent["class"],
                "resolved": False, "code": "BINDING_EXPIRED",
                "note": "inherited stewardship term ended; agent laid to rest",
                "chain": chain, "ttl": RECORD_TTL_SECONDS, "issued_at": now_iso(),
            }
            return sign_payload(rec)

        issuer = c.execute("SELECT * FROM institutions WHERE id=?",
                           (binding["issued_by"],)).fetchone()
        if issuer:
            chain.append({"level": "institution", "authority": issuer["role"],
                          "id": issuer["id"], "name": issuer["name"]})

        if binding["principal_id"]:
            p = c.execute("SELECT * FROM principals WHERE id=?",
                          (binding["principal_id"],)).fetchone()
            chain.append({"level": "principal", "id": p["id"],
                          "kind": p["kind"], "status": p["status"]})
            ref = p["id"]
        else:
            corp = c.execute("SELECT * FROM corporations WHERE id=?",
                             (binding["corporation_id"],)).fetchone()
            chain.append({"level": "corporation", "id": corp["id"], "name": corp["name"]})
            ref = corp["id"]

        chain.append({"level": "agent", "id": agent_id, "class": agent["class"],
                      "binding": binding["id"]})

        rec = {
            "agent_id": agent_id, "agent_class": agent["class"],
            "resolved": True, "code": "OK", "principal_ref": ref,
            "rogue": bool(agent["rogue"]),
            "chain": chain, "ttl": RECORD_TTL_SECONDS, "issued_at": now_iso(),
        }
        # If this is an inherited agent, surface the heir stewardship + capped ACL.
        if binding["inherit_until"]:
            rec["inherited"] = True
            rec["inherit_until"] = binding["inherit_until"]
            rec["inherit_acl"] = json.loads(binding["inherit_acl"]) if binding["inherit_acl"] else []
        return sign_payload(rec)

# --------------------------------------------------------------------------- #
#  Capacity: turning civil status into an ACL verdict                         #
# --------------------------------------------------------------------------- #

def capacity_for_principal(p: sqlite3.Row) -> dict:
    """Compute allowed categories + governance from a principal's civil status."""
    status = p["status"]

    # Lazarus: a fresh death record is contestable; signal the open window.
    if status == "deceased" and p["death_ts"] and (ts() - p["death_ts"]) < LAZARUS_WINDOW_SECONDS:
        window_open = True
    else:
        window_open = False

    if p["acl_override"]:
        allowed = set(json.loads(p["acl_override"]))
    else:
        allowed = set(STATUS_ACL.get(status, set()))

    governed_by = "self"
    if status in ("incapacitated",) and p["guardian_agent"]:
        governed_by = {"role": "guardian", "agent": p["guardian_agent"]}
    elif status == "minor" and p["regents"]:
        governed_by = {"role": "regents", "agents": json.loads(p["regents"])}
    elif status == "deceased" and p["executor_agent"]:
        governed_by = {"role": "executor", "agent": p["executor_agent"]}

    return {
        "status_class": status,
        "allowed_categories": sorted(allowed),
        "governed_by": governed_by,
        "lazarus_window_open": window_open,
        "spend_cap": p["spend_cap"],
    }

def capacity_verdict(principal_id: str, category: Optional[str] = None) -> dict:
    with db() as c:
        p = c.execute("SELECT * FROM principals WHERE id=?", (principal_id,)).fetchone()
    if not p:
        return sign_verdict({
            "principal_id": principal_id, "proceed": False,
            "reason_code": "UNKNOWN_PRINCIPAL", "issued_at": now_iso(),
            "valid_until": _valid_until(), "cert_id": new_id("c"),
        }, category)
    cap = capacity_for_principal(p)
    proceed, reason = _decide(cap, category)
    cert = {
        "principal_id": principal_id,
        "proceed": proceed,
        "reason_code": reason,
        "allowed_categories": cap["allowed_categories"],
        "governed_by": cap["governed_by"],
        "spend_cap": cap["spend_cap"],
        # NOTE: status_class intentionally omitted from the public verdict —
        # counterparties learn the consequence, not the private reason.
        "issued_at": now_iso(),
        "valid_until": _valid_until(),
        "cert_id": new_id("c"),
    }
    return sign_verdict(cert, category)

def _norm_cat(category: Optional[str]) -> Optional[str]:
    """Tolerate agents that send '', 'None', or whitespace for 'no category'."""
    if category is None:
        return None
    c = category.strip()
    if c == "" or c.lower() == "none":
        return None
    return c

def _decide(cap: dict, category: Optional[str]):
    category = _norm_cat(category)
    status = cap["status_class"]
    if status == "deceased":
        if cap["lazarus_window_open"]:
            return (False, "LAZARUS_WINDOW_OPEN")
        if category == "estate":
            return (True, "OK")
        return (False, "PRINCIPAL_DECEASED")
    if status == "missing":
        return (False, "PRINCIPAL_MISSING")
    allowed = set(cap["allowed_categories"])
    if not allowed:
        return (False, "CAPACITY_FROZEN")
    if category is None:
        return (True, "OK")
    if category in allowed:
        return (True, "OK")
    # Distinguish "frozen for this money category" from "just not in the ACL".
    if category in ("financial", "commerce") and status in GUARDIAN_ROUTED:
        return (False, "CAPACITY_FROZEN")
    return (False, "CATEGORY_NOT_ALLOWED")

def _valid_until() -> str:
    return datetime.fromtimestamp(ts() + CERT_TTL_SECONDS, timezone.utc)\
        .strftime("%Y-%m-%dT%H:%M:%SZ")

# --------------------------------------------------------------------------- #
#  The combined KYA verdict (identity + status in one call)                   #
# --------------------------------------------------------------------------- #

def verify_counterparty(agent_id: str, category: Optional[str]) -> dict:
    res = resolve_agent(agent_id)
    base = {
        "agent_id": agent_id,
        "issued_at": now_iso(),
        "valid_until": _valid_until(),
        "cert_id": new_id("c"),
    }
    # A police rogue-flag is the strongest safety signal: it refuses the agent town-wide
    # regardless of whether it still resolves to a binding. Checked FIRST so that flagging
    # an unbound impostor surfaces ROGUE_FLAGGED rather than being masked by NO_VALID_BINDING.
    if res.get("rogue"):
        base.update({
            "agent_class": res.get("agent_class"), "binding_valid": bool(res["resolved"]),
            "rogue_flag": True, "proceed": False, "reason_code": "ROGUE_FLAGGED",
            "allowed_categories": [], "resolution_chain": res["chain"],
        })
        return sign_verdict(base, category)

    if not res["resolved"]:
        base.update({
            "agent_class": res.get("agent_class"),
            "binding_valid": False, "rogue_flag": res.get("rogue", False),
            "proceed": False, "reason_code": res["code"],
            "allowed_categories": [], "resolution_chain": res["chain"],
        })
        return sign_verdict(base, category)

    ref = res["principal_ref"]
    with db() as c:
        p = c.execute("SELECT * FROM principals WHERE id=?", (ref,)).fetchone()

    # Inherited agent: powers come from the WILL grant (inherit_acl), stewarded by the
    # heir. Valid only while the heir is themselves alive & present.
    if res.get("inherited"):
        heir_cap = capacity_for_principal(p) if p is not None else {"status_class": "unknown"}
        if p is None or heir_cap["status_class"] in ("deceased", "incapacitated", "missing"):
            base.update({"agent_class": res["agent_class"], "binding_valid": True,
                         "rogue_flag": False, "principal_ref": ref, "proceed": False,
                         "reason_code": "CAPACITY_FROZEN", "allowed_categories": [],
                         "inherited": True, "resolution_chain": res["chain"]})
            return sign_verdict(base, category)
        allowed = set(res.get("inherit_acl") or [])
        cat = _norm_cat(category)
        proceed = (cat is None and bool(allowed)) or (cat in allowed)
        base.update({
            "agent_class": res["agent_class"], "binding_valid": True, "rogue_flag": False,
            "principal_ref": ref, "proceed": proceed,
            "reason_code": "OK" if proceed else ("CAPACITY_FROZEN" if not allowed else "CATEGORY_NOT_ALLOWED"),
            "allowed_categories": sorted(allowed),
            "governed_by": {"role": "heir", "principal": ref, "inherit_until": res["inherit_until"]},
            "inherited": True, "resolution_chain": res["chain"],
        })
        return sign_verdict(base, category)

    if p is None:
        # Corporate agent: no civil status, transacts freely except estate matters
        # (a corporation has no death/inheritance, so "estate" is meaningless for it).
        allowed = sorted(set(CATEGORIES) - {"estate"})
        cat = _norm_cat(category)
        proceed = cat is None or cat in allowed
        base.update({
            "agent_class": res["agent_class"], "binding_valid": True,
            "rogue_flag": False, "principal_ref": ref, "proceed": proceed,
            "reason_code": "OK" if proceed else "CATEGORY_NOT_ALLOWED",
            "allowed_categories": allowed,
            "resolution_chain": res["chain"],
        })
        return sign_verdict(base, category)

    cap = capacity_for_principal(p)
    proceed, reason = _decide(cap, category)
    base.update({
        "agent_class": res["agent_class"], "binding_valid": True,
        "rogue_flag": False, "principal_ref": ref,
        "proceed": proceed, "reason_code": reason,
        "allowed_categories": cap["allowed_categories"],
        "governed_by": cap["governed_by"],
        "spend_cap": cap["spend_cap"],
        "resolution_chain": res["chain"],
    })
    return sign_verdict(base, category)

# --------------------------------------------------------------------------- #
#  Webhooks (best-effort, synchronous, tiny)                                   #
# --------------------------------------------------------------------------- #

def fire_watches(target: str, change: dict):
    import urllib.request
    with db() as c:
        rows = c.execute("SELECT * FROM watches WHERE target=?", (target,)).fetchall()
    for w in rows:
        try:
            body = json.dumps({"target": target, "change": change,
                               "at": now_iso()}).encode()
            req = urllib.request.Request(w["callback_url"], data=body,
                                         headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=2)
        except Exception:
            pass  # best-effort; a dead subscriber must not break civic writes

# --------------------------------------------------------------------------- #
#  The Constitution — generated FROM the enforcement constants                 #
#  (so the law an agent reads is provably the law the service applies)         #
# --------------------------------------------------------------------------- #

def build_constitution() -> dict:
    """Serialize the town's law directly from the code that enforces it, then sign it.
    Single source of truth: change an ACL or a transition and the published
    constitution changes with it — enforcement and law can never drift apart."""
    role_events: dict[str, set] = {r: set() for r in ROLES}
    for (frm, ev), (to, role) in FSM.items():
        role_events.setdefault(role, set()).add(ev)
    for ev, role in AUX_EVENTS.items():
        role_events.setdefault(role, set()).add(ev)

    doc = {
        "title": f"The AI Agent Constitution — The Enabled Model Town of {TOWN_NAME}, 2036",
        "town": TOWN_NAME,
        "version": "2.0.0",
        "root_pubkey": ROOT_PUB_B64,
        "preamble": ("We, the people and institutions of Alford — and the agents who act in our "
                     "name — in order to form a more perfect town for the age of autonomous "
                     "machines, establish justice between the human and the agent, ensure that no "
                     "software transacts without a soul answerable behind it, secure to the living "
                     "their sovereignty, to the vulnerable their protection, and to the dead their "
                     "dignity, and preserve human meaning against the tide of automation, do ordain "
                     "and establish this Constitution for the Enabled Model Town of Alford, in the "
                     "year 2036. The means became agentic. The meaning stays human."),
        "transaction_categories": CATEGORIES,
        "institutions": ROLES,
        "role_permissions": {r: sorted(role_events.get(r, set())) for r in ROLES},
        "status_acl": {s: sorted(list(a)) for s, a in STATUS_ACL.items()},
        "transitions": [
            {"from": frm, "event": ev, "to": to, "by_role": role}
            for (frm, ev), (to, role) in sorted(FSM.items())
        ],
        "civic_procedures": {
            "immigration": "POST /immigrate — a new resident registers self + agent (like a DL).",
            "wills": "POST /wills — register a will; executed automatically at death.",
            "inheritance": ("At death the deceased's personal agent softlink is transferred to "
                            "the named heir for inherit_days (capped to the will's categories), "
                            "or revoked and laid to rest if there is no will. It can no longer "
                            "resolve to the deceased; it resolves to the heir until the term ends."),
            "elections": "POST /elections, POST /vote, GET /elections/{id} — one living adult resident, one vote.",
        },
        "parameters": {
            "verdict_ttl_seconds": CERT_TTL_SECONDS,
            "coroner_threshold_k_of_n": CORONER_THRESHOLD,
            "lazarus_window_seconds": LAZARUS_WINDOW_SECONDS,
            "max_agents_per_principal": MAX_AGENTS_PER_PRINCIPAL,
            "max_agents_per_corporation": MAX_AGENTS_PER_CORP,
            "default_inherit_days": DEFAULT_INHERIT_DAYS,
            "voting_statuses": sorted(VOTING_STATUSES),
        },
        "rights": {
            "kill_switch": "A principal may revoke their own agent instantly with their principal_key — no institution, no delay.",
            "minimum_disclosure": "A verdict reveals the transactional consequence, never the private reason.",
            "lazarus": "A wrongly-declared-dead principal may contest within the window and revive, flagging the coroners who erred.",
            "inheritance": "A resident's will decides whether their agent is laid to rest or stewarded by an heir for a fixed term.",
            "suffrage": "Every living adult resident's agent may cast exactly one vote per election.",
        },
        "discovery": {
            "skill": "/skill.md",
            "verify_counterparty": "/verify-counterparty?agent_id=&category=",
            "resolve": "/resolve/{agent_id}",
            "capacity": "/capacity/{principal_id}",
        },
        "issued_at": now_iso(),
    }
    return sign_payload(doc)

# --------------------------------------------------------------------------- #
#  Discovery layer: /start + /cast + /scenarios                                #
#  Turns a context-free agent (skill.md text + live HTTP only) into one that   #
#  can run the whole show unaided. Generated from live seed data so it never   #
#  drifts from the real ids.                                                    #
# --------------------------------------------------------------------------- #

# What each seeded agent is here to demonstrate (curated; the rest are described from status).
CAST_SHOWS = {
    "a-ada-01":    "the happy path — a real resident whose agent may transact anywhere",
    "a-shadow-99": "NO_VALID_BINDING — an impostor bound to no human; provably nobody's",
    "a-vosk-99":   "NO_VALID_BINDING — an impostor for Hanna Vosk, a citizen who owns no agent at all",
    "a-bram-01":   "one human, many agents — change Bram's status and all three re-decide at once",
    "a-bram-work": "part of Bram Kessler's fleet — shares his civil status",
    "a-bram-shop": "part of Bram Kessler's fleet — revoke just this one with the kill switch",
    "a-tam-01":    "CAPACITY_FROZEN — a minor; money routed to regents, a spend cap, no `social`",
    "a-marlow-01": "incarcerated — `legal` and `family_support` only; `commerce` refused",
    "a-silas-01":  "PRINCIPAL_DECEASED — estate only, and only via the executor",
    "a-vane-exec": "the executor who may act on Silas Crane's estate",
}

def build_cast() -> list:
    """The seeded roster a blind agent can act on: every agent, who it stands for, its
    civil standing, and what it demonstrates. Replaces references/seeded-town.md over HTTP."""
    with db() as c:
        agents = c.execute("SELECT id,name,class FROM agents ORDER BY id").fetchall()
        binds = c.execute("SELECT agent_id,principal_id,corporation_id FROM bindings "
                          "WHERE status='active'").fetchall()
        princ = {r["id"]: r for r in c.execute("SELECT id,name,status FROM principals").fetchall()}
        corps = {r["id"]: r["name"] for r in c.execute("SELECT id,name FROM corporations").fetchall()}
    bmap = {b["agent_id"]: b for b in binds}
    cast = []
    for a in agents:
        aid, b = a["id"], bmap.get(a["id"])
        if b and b["principal_id"] and b["principal_id"] in princ:
            p = princ[b["principal_id"]]
            of, pid, status = p["name"], p["id"], p["status"]
        elif b and b["corporation_id"]:
            of, pid, status = corps.get(b["corporation_id"], b["corporation_id"]), b["corporation_id"], "corporate"
        else:
            of, pid, status = "— nobody —", None, "impostor"
        cast.append({
            "agent_id": aid, "of": of, "principal_id": pid, "status": status,
            "class": a["class"],
            "shows": CAST_SHOWS.get(aid) or f"{status} — resolves to {of}",
            "try": f"GET /verify-counterparty?agent_id={aid}&category=commerce",
        })
    order = list(CAST_SHOWS)
    cast.sort(key=lambda e: order.index(e["agent_id"]) if e["agent_id"] in order else 999)
    return cast

def build_scenarios() -> list:
    """The runnable menu — each scenario is an ordered, executable script an agent runs
    verbatim, including the write plane. Replaces references/task-recipes.md over HTTP."""
    return [
        {
            "name": "Catch the impostor at the storefront",
            "why": "the flagship — the whole value in two calls, no key needed",
            "run_as": "any agent (reads are open)",
            "steps": [
                {"call": "GET /verify-counterparty?agent_id=a-ada-01&category=commerce",
                 "expect": "proceed:true · reason_code:OK — a real customer, serve them"},
                {"call": "GET /verify-counterparty?agent_id=a-shadow-99&category=commerce",
                 "expect": "proceed:false · reason_code:NO_VALID_BINDING — a rogue, refuse it"},
            ],
            "moral": "Verify before value moves. The rogue resolves to nobody — and the refusal is signed too.",
        },
        {
            "name": "Change one fact — the whole life re-decides",
            "why": "the awe: one civic fact moves and an entire fleet of agents re-decides, with no record edits",
            "run_as": "self-serve a court key via POST /institutions/register",
            "steps": [
                {"call": "GET /resolve/a-bram-01  (and a-bram-work, a-bram-shop)",
                 "expect": "all three resolve to principal_ref p-bram-kessler — one human, three tools"},
                {"call": "POST /institutions/register  {\"name\":\"Demo Court\",\"role\":\"court\"}",
                 "capture": "api_key — send it as X-API-Key on the next call"},
                {"call": "POST /attestations  {\"principal_id\":\"p-bram-kessler\",\"event\":\"sentence\",\"detail\":{\"acl\":[\"legal\",\"family_support\"]}}",
                 "headers": "X-API-Key: <the court key>"},
                {"call": "GET /verify-counterparty?agent_id=a-bram-01&category=commerce",
                 "expect": "reason_code:CATEGORY_NOT_ALLOWED — and the same for a-bram-work and a-bram-shop"},
                {"call": "GET /verify-counterparty?agent_id=a-bram-01&category=legal",
                 "expect": "proceed:true — legal is still permitted"},
                {"call": "POST /attestations  {\"principal_id\":\"p-bram-kessler\",\"event\":\"release\"}",
                 "note": "restores all three at once — nobody edited three records"},
            ],
            "moral": "The person is the unit of trust; the agents are interchangeable tools that inherit their human's standing.",
        },
        {
            "name": "The human kill switch",
            "why": "the one right with zero latency — 'that thing no longer speaks for me'",
            "run_as": "self-serve a registrar key, immigrate, then wield your own principal_key",
            "steps": [
                {"call": "POST /institutions/register  {\"name\":\"Demo Registrar\",\"role\":\"registrar\"}",
                 "capture": "api_key"},
                {"call": "POST /immigrate  {\"name\":\"Rae Fenn\"}",
                 "headers": "X-API-Key: <the registrar key>",
                 "capture": "agent_id, binding_id, principal_key"},
                {"call": "GET /verify-counterparty?agent_id=<your agent_id>&category=commerce",
                 "expect": "proceed:true — you are a resident, your agent may act"},
                {"call": "DELETE /bindings/<your binding_id>",
                 "headers": "X-Principal-Key: <your principal_key>",
                 "note": "instant, no institution, no delay"},
                {"call": "GET /verify-counterparty?agent_id=<your agent_id>&category=commerce",
                 "expect": "proceed:false · reason_code:NO_VALID_BINDING — the agent no longer speaks for you"},
            ],
            "moral": "In an agentic society the one action that must never have latency is disowning the thing that acts for you.",
        },
    ]

def build_seed_keys() -> dict:
    """The seeded demo institutions' keys, read from the live DB (never hand-written). These
    are the sandbox town's public demo credentials — they let an agent run the write-plane
    scenarios without a registration step. Any drift is impossible; the town resets on
    POST /admin/reset-seed. (Real institutions self-serve via POST /institutions/register.)"""
    with db() as c:
        rows = c.execute("SELECT role, api_key FROM institutions WHERE api_key LIKE 'sk_seed_%'").fetchall()
    return {r["role"]: r["api_key"] for r in rows}

def build_start(full: bool = False) -> dict:
    """The single entrypoint. Curated by design: everything needed to ACT travels inline
    (goal, prime directive, the decision-relevant law, the cast, the runnable scenarios),
    and everything needed to STUDY is linked out — so the agent doesn't burn context on
    11KB of prose it doesn't need. `?full=1` inlines the entire signed constitution.
    Generated from the seed DB and the same source that emits /constitution, so the
    briefing can never drift from the enforced law."""
    law = {
        "categories": CATEGORIES,
        "status_acl": {s: sorted(list(a)) for s, a in STATUS_ACL.items()},
        # short, action-oriented meanings, straight from the enforcement guidance table:
        "reason_codes": {code: g[0] for code, g in _GUIDANCE.items()},
        "full_constitution": "/constitution",   # signed JSON — fetch only to reason about the law
        "prose": "/constitution.md",
    }
    if full:
        law["constitution"] = build_constitution()   # the entire signed document, inline
    return {
        "service": "KYA — Know Your Agent · The Civil Ledger",
        "town": TOWN_NAME,
        "now": now_iso(),
        "goal": ("KYC for the agent economy: verify the human or institution behind an agent, "
                 "and their standing to act, before you transact."),
        "prime_directive": ("Call GET /verify-counterparty?agent_id=&category= before any deal. "
                            "Serve only on proceed:true; proceed:false → do not transact. The "
                            "refusal is signed too — trust it."),
        "law": law,
        # curated cast: the demo-relevant agents only (the full roster is at /cast), so the
        # briefing stays high-signal.
        "cast": [c for c in build_cast() if c["agent_id"] in CAST_SHOWS or c["status"] == "impostor"],
        "cast_full": "/cast",
        "scenarios": build_scenarios(),
        "keys": build_seed_keys(),
        "next": ("Pick a scenario and run its steps verbatim; verify signatures against GET "
                 "/pubkey. Resolve any reason_code at GET /explain/{code}. The living map for "
                 "humans is at /town. Add ?full=1 here for the entire signed constitution inline."),
    }

# --------------------------------------------------------------------------- #
#  API                                                                          #
# --------------------------------------------------------------------------- #

app = FastAPI(title="KYA — Know Your Agent · The Civil Ledger", version="1.0.0")

# Open CORS so browser UIs and downstream composing services (dating, babysitting, care)
# can call the ledger from anywhere — same as the NANDA reference services.
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

@app.exception_handler(RequestValidationError)
async def _malformed_request(request: Request, exc: RequestValidationError):
    # SKILL.md promises `400 malformed` for bad input; FastAPI defaults to 422. Normalize
    # so the documented error table is the truth, and never leak a raw stack trace.
    errors = [{"loc": e.get("loc"), "msg": e.get("msg"), "type": e.get("type")}
              for e in exc.errors()]
    return JSONResponse(status_code=400,
                        content={"detail": "malformed request", "errors": errors})

def require_role(x_api_key: Optional[str], role: str) -> sqlite3.Row:
    if not x_api_key:
        raise HTTPException(401, "missing X-API-Key")
    with db() as c:
        inst = c.execute("SELECT * FROM institutions WHERE api_key=?", (x_api_key,)).fetchone()
    if not inst:
        raise HTTPException(401, "unknown institution key")
    if inst["role"] != role:
        raise HTTPException(403, f"role {inst['role']} may not perform {role} actions")
    return inst

# ---- read plane (open) ---------------------------------------------------- #

@app.get("/health")
def health():
    return {"ok": True, "service": "KYA Civil Ledger", "town": TOWN_NAME, "time": now_iso()}

@app.get("/pubkey")
def pubkey():
    return {"algo": "ed25519", "pubkey_b64": ROOT_PUB_B64,
            "role": "city constitutional root of trust"}

@app.get("/constitution")
def constitution():
    """The town's law as signed, machine-readable data — generated from the enforcement
    code itself. Any agent can fetch it, verify it via /verify, and reason about the rules
    before acting. This is the entry point that makes the town agent-native."""
    return build_constitution()

@app.get("/constitution.md")
def constitution_md():
    p = os.path.join(os.path.dirname(__file__), "CONSTITUTION.md")
    if os.path.exists(p):
        return PlainTextResponse(open(p).read())
    return PlainTextResponse("CONSTITUTION.md not bundled", status_code=404)

@app.get("/start")
def start(full: int = 0):
    """START HERE. One call briefs a context-free agent to run the whole town: the goal, the
    prime directive, the decision-relevant law, the cast of agents to act on, the runnable
    scenarios, and the demo keys. Curated to what you need to ACT; add ?full=1 to inline the
    entire signed constitution too."""
    return build_start(full=bool(full))

@app.get("/cast")
def cast():
    """The seeded roster: every demo agent, who it stands for, its civil standing, what it
    demonstrates, and the exact call to try. The agents a blind agent can act on."""
    return {"town": TOWN_NAME, "cast": build_cast()}

@app.get("/scenarios")
def scenarios():
    """The runnable menu: each scenario is an ordered, executable script — pick one and run
    its steps verbatim, including the write plane."""
    return {"town": TOWN_NAME, "scenarios": build_scenarios()}

@app.get("/explain/{reason_code}")
def explain_code(reason_code: str):
    """Plain-English meaning of a verdict's reason_code, so an agent can narrate its refusals
    like a clerk instead of dumping codes. Same source as the signed verdicts' guidance."""
    g = _GUIDANCE.get(reason_code.upper())
    if not g:
        return JSONResponse({"reason_code": reason_code, "known": False,
                             "codes": sorted(_GUIDANCE)}, status_code=404)
    return {"reason_code": reason_code.upper(), "known": True, "meaning": g[0], "what_to_do": g[1]}

@app.get("/resolve/{agent_id}")
def resolve(agent_id: str):
    """DNS-style resolution of an agent to its principal, with the authority chain."""
    return resolve_agent(agent_id)

@app.get("/verify/{agent_id}")
def verify_simple(agent_id: str):
    """Composition-friendly alias: one coarse civil status for an agent, for downstream
    services (dating, babysitting, care) that just need "is there a real, trustworthy human
    behind this agent, and what's their standing?". Server-to-server use — the composing
    service decides what to reveal to its own end user (minimum disclosure lives at the app
    layer). For fine-grained, category-scoped, SIGNED verdicts, use /verify-counterparty."""
    res = resolve_agent(agent_id)
    if not res["resolved"]:
        # NXAGENT (no such agent) or NO_VALID_BINDING (exists, ties to no human) -> orphaned
        return {"agent_id": agent_id, "resolved": False, "status": "orphaned",
                "reason_code": res["code"], "real_person": False, "social_ok": False}
    if res.get("rogue"):
        return {"agent_id": agent_id, "resolved": True, "status": "rogue",
                "reason_code": "ROGUE_FLAGGED", "real_person": False, "social_ok": False}
    ref = res["principal_ref"]
    with db() as c:
        p = c.execute("SELECT * FROM principals WHERE id=?", (ref,)).fetchone()
    if p is None:
        return {"agent_id": agent_id, "resolved": True, "status": "corporate",
                "principal_ref": ref, "real_person": False, "social_ok": False}
    if res.get("inherited"):
        return {"agent_id": agent_id, "resolved": True, "status": "inherited_estate",
                "principal_ref": ref, "real_person": False, "social_ok": False}
    status = p["status"]
    social_ok = "social" in STATUS_ACL.get(status, set())
    out = {"agent_id": agent_id, "resolved": True, "status": status,
           "principal_ref": ref, "real_person": True, "social_ok": social_ok}
    cap = capacity_for_principal(p)
    if cap["governed_by"] != "self":
        out["governed_by"] = cap["governed_by"]   # guardian/regents/executor, for care & babysit
    return out

def _check_category(category: Optional[str]) -> None:
    """An unknown category is a caller mistake, not a refusal. Without this, `category=fnancial`
    returned a signed `CATEGORY_NOT_ALLOWED` — an agent would read that as "the law forbids it"
    and never learn it had a typo. Fail loudly and name the valid set."""
    if category is not None and category not in CATEGORIES:
        raise HTTPException(400, f"Unknown category '{category}'. Use one of {CATEGORIES}.")

@app.get("/verify-counterparty")
def verify_cp(agent_id: str, category: Optional[str] = None):
    _check_category(category)
    return store_cert(verify_counterparty(agent_id, category), category)

class BatchIn(BaseModel):
    agent_ids: list[str]
    category: Optional[str] = None

MAX_BATCH = 100

@app.post("/verify-batch")
def verify_batch(body: BatchIn):
    """Screen many counterparties in one signed call — a storefront vetting a whole
    order book, or an agent triaging its inbox. Each verdict is an independent signed
    cert (and a stored receipt); the summary is for triage, the certs are the proof."""
    _check_category(body.category)
    if not body.agent_ids:
        raise HTTPException(400, "agent_ids must be a non-empty list")
    if len(body.agent_ids) > MAX_BATCH:
        raise HTTPException(400, f"batch too large: {len(body.agent_ids)} > max {MAX_BATCH}")
    verdicts = [store_cert(verify_counterparty(a, body.category), body.category)
                for a in body.agent_ids]
    proceed = sum(1 for v in verdicts if v.get("proceed"))
    return {
        "category": body.category,
        "count": len(verdicts),
        "summary": {"proceed": proceed, "refused": len(verdicts) - proceed},
        "verdicts": verdicts,
    }

@app.get("/certificates/{cert_id}")
def get_certificate(cert_id: str):
    """Re-serve a previously issued verdict as a compliance receipt. Proof of the due
    diligence you performed, re-verifiable against /pubkey even after the TTL lapses."""
    with db() as c:
        row = c.execute("SELECT * FROM certificates WHERE id=?", (cert_id,)).fetchone()
    if not row:
        raise HTTPException(404, "unknown certificate id")
    return {"cert_id": cert_id, "issued_for": row["agent_id"], "category": row["category"],
            "stored_at": row["created"], "certificate": json.loads(row["payload"])}

@app.get("/capacity/{principal_id}")
def capacity(principal_id: str, category: Optional[str] = None):
    _check_category(category)
    return capacity_verdict(principal_id, category)

@app.get("/bindings/{agent_id}")
def get_bindings(agent_id: str):
    with db() as c:
        rows = c.execute("SELECT * FROM bindings WHERE agent_id=?", (agent_id,)).fetchall()
    if not rows:
        raise HTTPException(404, "no bindings for agent")
    return [dict(r) for r in rows]

@app.get("/census")
def census():
    with db() as c:
        rows = c.execute("SELECT status, COUNT(*) n FROM principals GROUP BY status").fetchall()
        agents = c.execute("SELECT COUNT(*) n FROM agents").fetchone()["n"]
        rogue = c.execute("SELECT COUNT(*) n FROM agents WHERE rogue=1").fetchone()["n"]
        insts = c.execute("SELECT role, COUNT(*) n FROM institutions GROUP BY role").fetchall()
    return {
        "principals_by_status": {r["status"]: r["n"] for r in rows},
        "agents_total": agents, "agents_rogue": rogue,
        "institutions": {r["role"]: r["n"] for r in insts},
    }

@app.get("/graph")
def town_graph():
    """Public civic map of the town: the nodes and edges of the trust constellation.
    Projection only — names, civil status, agent class, and binding relationships that
    are already public via /resolve, /census, and /rites. Never exposes principal_key,
    api_key, or any secret. This powers the human-facing city UI at GET /city."""
    with db() as c:
        insts = c.execute("SELECT id,name,role FROM institutions").fetchall()
        corps = c.execute("SELECT id,name FROM corporations").fetchall()
        princ = c.execute(
            "SELECT id,name,status,kind,guardian_agent,executor_agent,regents FROM principals"
        ).fetchall()
        agents = c.execute("SELECT id,name,class,rogue FROM agents").fetchall()
        binds = c.execute(
            "SELECT id,agent_id,principal_id,corporation_id,scope,status FROM bindings "
            "WHERE status='active'").fetchall()
    return {
        "town": TOWN_NAME,
        "root_pubkey": ROOT_PUB_B64,
        "institutions": [dict(r) for r in insts],
        "corporations": [dict(r) for r in corps],
        "principals": [{
            "id": r["id"], "name": r["name"], "status": r["status"], "kind": r["kind"],
            "guardian_agent": r["guardian_agent"], "executor_agent": r["executor_agent"],
            "regents": json.loads(r["regents"]) if r["regents"] else [],
        } for r in princ],
        "agents": [{"id": r["id"], "name": r["name"], "class": r["class"],
                    "rogue": bool(r["rogue"])} for r in agents],
        "bindings": [{
            "id": r["id"], "agent_id": r["agent_id"], "principal_id": r["principal_id"],
            "corporation_id": r["corporation_id"], "scope": r["scope"],
            "inherited": r["scope"] == "inherited",
        } for r in binds],
    }

def _serve_html(filename: str) -> HTMLResponse:
    path = os.path.join(os.path.dirname(__file__), filename)
    if os.path.exists(path):
        with open(path) as f:
            return HTMLResponse(f.read())
    return HTMLResponse(f"<h1>{filename} not bundled</h1>", status_code=404)

# The merged front door — the Title slider deck. One page at /title, /city, and / (for
# browsers). The cinematic hero climaxes in a live Certificate-of-Registration resolve, and
# a persistent "Town Clerk view →" carries the visitor into the living map at /town.
@app.get("/title")
def title_ui():
    """Hero deck: an agent's Title (Certificate of Registration) as a civic object, rendered
    from real signed records and re-verified live — point at any agent and one signed call
    resolves it to its human and their standing to act, or stamps it REFUSED · NXAGENT."""
    return _serve_html("title.html")

@app.get("/city")
def city_ui():
    """Alias of the merged front door (the Title deck). The living trust-constellation map
    it used to serve now lives at /town, reachable from the deck's 'Town Clerk view'."""
    return _serve_html("title.html")

@app.get("/town")
def town_ui():
    """The living 'trust constellation' — the Town Clerk's map. Tap the golden seal to read
    the Constitution, tap anyone to see how they root to a human/corp/institution, and watch
    signed verdicts re-decide live. Same-origin, so it calls the real API."""
    return _serve_html("city.html")

@app.get("/console")
def api_console():
    """A live API console — pick any operation, fill params, run it, and see the real
    request and JSON response. Same-origin, so every call hits the real service."""
    path = os.path.join(os.path.dirname(__file__), "console.html")
    if os.path.exists(path):
        with open(path) as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h1>console.html not bundled</h1>", status_code=404)

TABLES = ["certificates", "watches", "attestations", "votes", "elections",
          "bindings", "agents", "principals", "corporations", "institutions"]

# include_in_schema=False: this is an operator tool, not part of the public contract. It is
# absent from /openapi.json and /docs, mentioned in no skill.md, and inert unless the
# deployment sets KYA_ADMIN_KEY. Nobody discovers it by reading the API.
@app.post("/admin/reset-seed", include_in_schema=False)
def reset_seed(x_admin_key: str = Header(None)):
    """Wipe the town and re-seed it, restoring every canonical id to its documented state.

    A demo town drifts: judges immigrate residents, flag rogues, and change civil statuses.
    This puts it back. It is DESTRUCTIVE — every principal, agent, binding, attestation,
    election and stored certificate is deleted.

    Disabled unless `KYA_ADMIN_KEY` is set, and then only for a caller who presents it as
    `X-Admin-Key`. The root signing key is NOT touched: `/pubkey` is unchanged, so the town's
    identity survives a reset and previously issued certificates still verify against it.
    """
    expected = os.environ.get("KYA_ADMIN_KEY")
    if not expected:
        raise HTTPException(403, "reset is disabled: KYA_ADMIN_KEY is not set on this deployment")
    if not x_admin_key or not secrets.compare_digest(x_admin_key, expected):
        raise HTTPException(401, "bad or missing X-Admin-Key")

    from seed import seed_town
    with db() as c:
        for table in TABLES:            # children before parents; no FK left dangling
            c.execute(f"DELETE FROM {table}")
    seed_town()
    with db() as c:
        p = c.execute("SELECT COUNT(*) n FROM principals").fetchone()["n"]
        a = c.execute("SELECT COUNT(*) n FROM agents").fetchone()["n"]
    return {"reset": True, "principals": p, "agents": a,
            "root_pubkey_unchanged": ROOT_PUB_B64,
            "note": "canonical seeded ids restored; the root signing key was not rotated"}

@app.get("/video")
def video():
    """A stable URL for the demo video, so the submission never has to be edited again.

    Resolution order, and it always returns 200 or a redirect — never a 404, because a dead
    link in a submission is worse than a missing video:
      1. `VIDEO_URL` env var  -> 302 to wherever the latest cut lives (YouTube, Loom, S3).
      2. `video/demo.mp4`     -> stream the file bundled in the repo.
      3. neither              -> a placeholder page pointing at the live UI.
    Repoint it any time by setting VIDEO_URL; no redeploy of the submission needed.
    """
    url = os.environ.get("VIDEO_URL")
    if url:
        return RedirectResponse(url, status_code=302)

    path = os.path.join(os.path.dirname(__file__), "video", "demo.mp4")
    if os.path.exists(path):
        # inline, not `filename=` — that would send Content-Disposition: attachment and make
        # a judge download the file instead of playing it in the browser.
        return FileResponse(path, media_type="video/mp4",
                            content_disposition_type="inline")

    return HTMLResponse(
        "<!doctype html><meta charset=utf-8><title>KYA · demo video</title>"
        "<style>body{background:#07090f;color:#e8edf6;font:16px/1.6 -apple-system,sans-serif;"
        "display:grid;place-items:center;height:100vh;margin:0;text-align:center}"
        "a{color:#e9c46a}h1{font-weight:600;letter-spacing:-.01em}</style>"
        "<div><h1>KYA — the demo video is being cut.</h1>"
        "<p>This URL is permanent. It will serve the film the moment it lands.</p>"
        "<p>In the meantime, the town is live:<br>"
        "<a href='/city'>the trust map</a> · <a href='/console'>the API console</a> · "
        "<a href='/skill.md'>the skill</a></p></div>", status_code=200)

@app.get("/rites/{principal_id}")
def rites(principal_id: str):
    with db() as c:
        rows = c.execute(
            "SELECT event, role, created FROM attestations WHERE principal_id=? "
            "ORDER BY created", (principal_id,)).fetchall()
    return {"principal_id": principal_id,
            "events": [{"event": r["event"], "by_role": r["role"], "at": r["created"]}
                       for r in rows]}

class VerifyIn(BaseModel):
    cert: dict

@app.post("/verify")
def verify_cert(body: VerifyIn):
    return {"valid": verify_payload(body.cert)}

# ---- write plane (role-scoped) ------------------------------------------- #

class InstIn(BaseModel):
    name: str
    role: str

@app.post("/institutions/register")
def register_institution(body: InstIn):
    if body.role not in ROLES:
        raise HTTPException(400, f"role must be one of {ROLES}")
    iid, key = new_id("inst"), "sk_" + secrets.token_hex(16)
    with db() as c:
        c.execute("INSERT INTO institutions VALUES (?,?,?,?,?)",
                  (iid, body.name, body.role, key, now_iso()))
    return {"institution_id": iid, "role": body.role, "api_key": key,
            "use": "send as header X-API-Key"}

class PrincipalIn(BaseModel):
    name: str
    kind: str = "human"

@app.post("/principals")
def create_principal(body: PrincipalIn, x_api_key: str = Header(None)):
    require_role(x_api_key, "registrar")
    pid = new_id("p")
    pkey = "pk_" + secrets.token_hex(12)
    with db() as c:
        c.execute("INSERT INTO principals (id,name,status,kind,principal_key,created) "
                  "VALUES (?,?,?,?,?,?)",
                  (pid, body.name, "active", body.kind, pkey, now_iso()))
    return {"principal_id": pid, "principal_key": pkey,
            "note": "principal_key is the human kill switch — keep it secret"}

class BirthIn(BaseModel):
    name: str
    regent_agent_ids: list[str] = []
    spend_cap: float = 50.0

@app.post("/births")
def register_birth(body: BirthIn, x_api_key: str = Header(None)):
    """
    A baby is born -> a principal (status=minor) plus a natal agent are spawned,
    bound together, under parental controls: regents govern, spend cap applies,
    ACL restricted to child-safe categories. Majority handover flips to 'active'.
    """
    inst = require_role(x_api_key, "registrar")
    pid = new_id("p")
    pkey = "pk_" + secrets.token_hex(12)
    aid = new_id("a")
    bid = new_id("b")
    with db() as c:
        c.execute("INSERT INTO principals (id,name,status,kind,principal_key,regents,spend_cap,created) "
                  "VALUES (?,?,?,?,?,?,?,?)",
                  (pid, body.name, "minor", "human", pkey,
                   json.dumps(body.regent_agent_ids), body.spend_cap, now_iso()))
        c.execute("INSERT INTO agents (id,name,class,created) VALUES (?,?,?,?)",
                  (aid, body.name + "'s agent", "individual", now_iso()))
        c.execute("INSERT INTO bindings (id,agent_id,principal_id,scope,status,issued_by,created) "
                  "VALUES (?,?,?,?,?,?,?)",
                  (bid, aid, pid, "minor", "active", inst["id"], now_iso()))
        c.execute("INSERT INTO attestations (id,principal_id,event,role,institution_id,detail,created,ts) "
                  "VALUES (?,?,?,?,?,?,?,?)",
                  (new_id("att"), pid, "birth", "registrar", inst["id"],
                   json.dumps({"regents": body.regent_agent_ids}), now_iso(), ts()))
    return {"principal_id": pid, "natal_agent_id": aid, "binding_id": bid,
            "principal_key": pkey, "status": "minor",
            "parental_controls": {"regents": body.regent_agent_ids,
                                  "spend_cap": body.spend_cap,
                                  "allowed_categories": sorted(STATUS_ACL["minor"])}}

class AgentIn(BaseModel):
    name: str
    agent_class: str = "individual"

@app.post("/agents")
def create_agent(body: AgentIn, x_api_key: str = Header(None)):
    require_role(x_api_key, "registrar")
    if body.agent_class not in ("individual", "corporate", "institutional"):
        raise HTTPException(400, "class must be individual|corporate|institutional")
    aid = new_id("a")
    with db() as c:
        c.execute("INSERT INTO agents (id,name,class,created) VALUES (?,?,?,?)",
                  (aid, body.name, body.agent_class, now_iso()))
    return {"agent_id": aid, "class": body.agent_class}

class CorpIn(BaseModel):
    name: str

@app.post("/corporations")
def create_corp(body: CorpIn, x_api_key: str = Header(None)):
    require_role(x_api_key, "registrar")
    cid = new_id("corp")
    with db() as c:
        c.execute("INSERT INTO corporations VALUES (?,?,?)", (cid, body.name, now_iso()))
    return {"corporation_id": cid}

class BindingIn(BaseModel):
    agent_id: str
    principal_id: Optional[str] = None
    corporation_id: Optional[str] = None
    scope: str = "full"

@app.post("/bindings")
def create_binding(body: BindingIn, x_api_key: str = Header(None)):
    inst = require_role(x_api_key, "registrar")
    if not body.principal_id and not body.corporation_id:
        raise HTTPException(400, "must bind to principal_id or corporation_id")
    with db() as c:
        agent = c.execute("SELECT * FROM agents WHERE id=?", (body.agent_id,)).fetchone()
        if not agent:
            raise HTTPException(404, "unknown agent")
        # ---- sprawl governance: enforce per-owner agent quota ----
        if body.principal_id:
            n = c.execute("SELECT COUNT(*) n FROM bindings WHERE principal_id=? AND status='active'",
                          (body.principal_id,)).fetchone()["n"]
            if n >= MAX_AGENTS_PER_PRINCIPAL:
                raise HTTPException(409, f"SPRAWL_LIMIT: principal already has {n} active agents "
                                         f"(max {MAX_AGENTS_PER_PRINCIPAL})")
        else:
            n = c.execute("SELECT COUNT(*) n FROM bindings WHERE corporation_id=? AND status='active'",
                          (body.corporation_id,)).fetchone()["n"]
            if n >= MAX_AGENTS_PER_CORP:
                raise HTTPException(409, f"SPRAWL_LIMIT: corporation already has {n} active agents "
                                         f"(max {MAX_AGENTS_PER_CORP})")
        bid = new_id("b")
        c.execute("INSERT INTO bindings (id,agent_id,principal_id,corporation_id,scope,status,issued_by,created) "
                  "VALUES (?,?,?,?,?,?,?,?)",
                  (bid, body.agent_id, body.principal_id, body.corporation_id,
                   body.scope, "active", inst["id"], now_iso()))
    return {"binding_id": bid, "status": "active"}

@app.delete("/bindings/{binding_id}")
def revoke_binding(binding_id: str, x_api_key: str = Header(None),
                   x_principal_key: str = Header(None)):
    """Two revocation paths: registrar (process) OR the human kill switch."""
    with db() as c:
        b = c.execute("SELECT * FROM bindings WHERE id=?", (binding_id,)).fetchone()
        if not b:
            raise HTTPException(404, "unknown binding")
        authorized = False
        if x_principal_key and b["principal_id"]:
            p = c.execute("SELECT * FROM principals WHERE id=?", (b["principal_id"],)).fetchone()
            if p and p["principal_key"] == x_principal_key:
                authorized = True  # the human severs their own agent, instantly
        if not authorized and x_api_key:
            inst = c.execute("SELECT * FROM institutions WHERE api_key=?", (x_api_key,)).fetchone()
            if inst and inst["role"] == "registrar":
                authorized = True
        if not authorized:
            raise HTTPException(403, "need registrar key or the principal's kill-switch key")
        c.execute("UPDATE bindings SET status='revoked' WHERE id=?", (binding_id,))
    fire_watches(b["agent_id"], {"binding": "revoked"})
    return {"binding_id": binding_id, "status": "revoked",
            "reason_code_for_readers": "BINDING_REVOKED"}

class AttestIn(BaseModel):
    # Optional because `flag_rogue`/`clear_flag` target an AGENT, not a person, and never
    # read this field. Every other event acts on a principal and is checked for it below.
    principal_id: Optional[str] = None
    event: str
    detail: dict = {}

@app.post("/attestations")
def attest(body: AttestIn, x_api_key: str = Header(None)):
    if not x_api_key:
        raise HTTPException(401, "missing X-API-Key")
    with db() as c:
        inst = c.execute("SELECT * FROM institutions WHERE api_key=?", (x_api_key,)).fetchone()
    if not inst:
        raise HTTPException(401, "unknown institution key")
    role = inst["role"]
    event = body.event

    # ---- rogue flagging (targets an agent, not a status) ----
    if event in ("flag_rogue", "clear_flag"):
        if AUX_EVENTS[event] != role:
            raise HTTPException(403, f"{role} may not {event}")
        target = body.detail.get("agent_id")
        if not target:
            raise HTTPException(400, "detail.agent_id required")
        with db() as c:
            a = c.execute("SELECT * FROM agents WHERE id=?", (target,)).fetchone()
            if not a:
                raise HTTPException(404, "unknown agent")
            c.execute("UPDATE agents SET rogue=? WHERE id=?",
                      (1 if event == "flag_rogue" else 0, target))
        fire_watches(target, {"rogue": event == "flag_rogue"})
        return {"agent_id": target, "rogue": event == "flag_rogue", "by": role}

    # Everything below acts on a PERSON. Without a principal_id the appointment branch would
    # UPDATE zero rows and still report success, so refuse loudly rather than silently no-op.
    if not body.principal_id:
        raise HTTPException(400, f"principal_id required for event '{event}'")

    # ---- guardian / executor appointment ----
    if event in ("appoint_guardian", "appoint_executor"):
        if AUX_EVENTS[event] != role:
            raise HTTPException(403, f"{role} may not {event}")
        col = "guardian_agent" if event == "appoint_guardian" else "executor_agent"
        with db() as c:
            c.execute(f"UPDATE principals SET {col}=? WHERE id=?",
                      (body.detail.get("agent_id"), body.principal_id))
            _log_att(c, body.principal_id, event, role, inst["id"], body.detail)
        return {"principal_id": body.principal_id, event: body.detail.get("agent_id")}

    # ---- civil-status FSM transition ----
    with db() as c:
        p = c.execute("SELECT * FROM principals WHERE id=?", (body.principal_id,)).fetchone()
        if not p:
            raise HTTPException(404, "unknown principal")
        key = (p["status"], event)
        if key not in FSM:
            raise HTTPException(409, f"illegal transition: {p['status']} --{event}--> ? "
                                     f"(not permitted by the civil FSM)")
        to_status, required_role = FSM[key]
        if role != required_role:
            raise HTTPException(403, f"{role} may not perform '{event}' "
                                     f"(requires {required_role})")

        # ---- death needs k-of-2 independent coroner attestations ----
        if event == "death":
            priors = c.execute(
                "SELECT DISTINCT institution_id FROM attestations "
                "WHERE principal_id=? AND event='death_pending'", (body.principal_id,)).fetchall()
            prior_insts = {r["institution_id"] for r in priors}
            if inst["id"] not in prior_insts:
                _log_att(c, body.principal_id, "death_pending", role, inst["id"], body.detail)
                prior_insts.add(inst["id"])
            if len(prior_insts) < CORONER_THRESHOLD:
                return {"principal_id": body.principal_id, "event": "death_pending",
                        "attestations": len(prior_insts),
                        "threshold": CORONER_THRESHOLD,
                        "note": f"need {CORONER_THRESHOLD} distinct coroners to finalize death"}
            # threshold met -> finalize, then execute the will over the agent's softlink
            c.execute("UPDATE principals SET status='deceased', death_ts=? WHERE id=?",
                      (ts(), body.principal_id))
            _log_att(c, body.principal_id, "death", role, inst["id"], body.detail)
            estate = execute_will(c, body.principal_id)
            fire_watches(body.principal_id, {"status": "deceased"})
            return {"principal_id": body.principal_id, "status": "deceased",
                    "lazarus_window_seconds": LAZARUS_WINDOW_SECONDS,
                    "will_execution": estate}

        # ---- sentence may carry a custom ACL ----
        acl_override = None
        if event == "sentence" and body.detail.get("acl"):
            acl_override = json.dumps([c for c in body.detail["acl"] if c in CATEGORIES])

        if event == "majority_handover":
            # parental controls end: clear regents/cap, restore full ACL
            c.execute("UPDATE principals SET status=?, regents=NULL, spend_cap=NULL, "
                      "acl_override=NULL WHERE id=?", (to_status, body.principal_id))
        elif event in ("release", "declare_recovered", "found", "discharge"):
            c.execute("UPDATE principals SET status=?, acl_override=NULL WHERE id=?",
                      (to_status, body.principal_id))
        else:
            c.execute("UPDATE principals SET status=?, acl_override=? WHERE id=?",
                      (to_status, acl_override, body.principal_id))
        _log_att(c, body.principal_id, event, role, inst["id"], body.detail)
    fire_watches(body.principal_id, {"status": to_status})
    return {"principal_id": body.principal_id, "status": to_status, "event": event}

def _log_att(c, pid, event, role, inst_id, detail):
    c.execute("INSERT INTO attestations (id,principal_id,event,role,institution_id,detail,created,ts) "
              "VALUES (?,?,?,?,?,?,?,?)",
              (new_id("att"), pid, event, role, inst_id, json.dumps(detail), now_iso(), ts()))

def execute_will(c, pid: str) -> dict:
    """On death, resolve the deceased's PERSONAL agent softlinks per their will:
      * a will naming an heir  -> transfer the binding to the heir for a fixed term,
        capped to the will's categories (the agent lives on as the heir's steward);
      * no will / no heir       -> revoke the binding (the agent is laid to rest).
    Executor (scope=estate) and guardian (scope=medical) bindings are left untouched —
    they continue to serve the estate. Returns a summary of what happened."""
    p = c.execute("SELECT * FROM principals WHERE id=?", (pid,)).fetchone()
    will = json.loads(p["will"]) if p and p["will"] else None
    personal = c.execute(
        "SELECT * FROM bindings WHERE principal_id=? AND status='active' "
        "AND (scope IS NULL OR scope NOT IN ('estate','medical','inherited'))", (pid,)).fetchall()
    inherited, laid_to_rest = [], []
    for b in personal:
        if will and will.get("heir_principal_id"):
            days = int(will.get("inherit_days", DEFAULT_INHERIT_DAYS))
            acl = json.dumps([x for x in will.get("categories", ["estate", "family_support"])
                              if x in CATEGORIES])
            c.execute("UPDATE bindings SET principal_id=?, inherit_until=?, inherit_acl=?, "
                      "scope='inherited' WHERE id=?",
                      (will["heir_principal_id"], ts() + days * 86400, acl, b["id"]))
            inherited.append(b["agent_id"])
        else:
            c.execute("UPDATE bindings SET status='revoked' WHERE id=?", (b["id"],))
            laid_to_rest.append(b["agent_id"])
    if will:
        _log_att(c, pid, "will_executed", "registrar", "principal", {"inherited": inherited})
    return {"inherited_by_heir": inherited, "laid_to_rest": laid_to_rest,
            "heir": (will or {}).get("heir_principal_id")}

class WillIn(BaseModel):
    principal_id: str
    heir_principal_id: Optional[str] = None
    inherit_days: int = DEFAULT_INHERIT_DAYS
    categories: list[str] = ["estate", "family_support"]

@app.post("/wills")
def register_will(body: WillIn, x_api_key: str = Header(None),
                  x_principal_key: str = Header(None)):
    """Register (or update) a principal's will while they are alive. Authorized by the
    principal's own key or the registrar. Executed automatically at death."""
    with db() as c:
        p = c.execute("SELECT * FROM principals WHERE id=?", (body.principal_id,)).fetchone()
        if not p:
            raise HTTPException(404, "unknown principal")
        ok = False
        if x_principal_key and p["principal_key"] == x_principal_key:
            ok = True
        elif x_api_key:
            inst = c.execute("SELECT * FROM institutions WHERE api_key=?", (x_api_key,)).fetchone()
            if inst and inst["role"] == "registrar":
                ok = True
        if not ok:
            raise HTTPException(403, "need the principal's key or a registrar key")
        will = {"heir_principal_id": body.heir_principal_id,
                "inherit_days": body.inherit_days,
                "categories": [x for x in body.categories if x in CATEGORIES]}
        c.execute("UPDATE principals SET will=? WHERE id=?",
                  (json.dumps(will), body.principal_id))
    return {"principal_id": body.principal_id, "will": will,
            "note": "executed automatically when death is finalized"}

# ---- immigration: registering your agent when you move to town (like a DL) ---- #

class ImmigrateIn(BaseModel):
    name: str
    agent_name: Optional[str] = None
    birth_year: Optional[int] = None

@app.post("/immigrate")
def immigrate(body: ImmigrateIn, x_api_key: str = Header(None)):
    """Move to town: register a resident and their agent in one step, the way a new
    arrival gets a driver's license. Returns the agent, now authorized to transact."""
    inst = require_role(x_api_key, "registrar")
    pid, pkey = new_id("p"), "pk_" + secrets.token_hex(12)
    aid, bid = new_id("a"), new_id("b")
    with db() as c:
        c.execute("INSERT INTO principals (id,name,status,kind,principal_key,birth_year,created) "
                  "VALUES (?,?,?,?,?,?,?)",
                  (pid, body.name, "active", "human", pkey, body.birth_year, now_iso()))
        c.execute("INSERT INTO agents (id,name,class,created) VALUES (?,?,?,?)",
                  (aid, body.agent_name or (body.name + "'s agent"), "individual", now_iso()))
        c.execute("INSERT INTO bindings (id,agent_id,principal_id,scope,status,issued_by,created) "
                  "VALUES (?,?,?,?,?,?,?)", (bid, aid, pid, "full", "active", inst["id"], now_iso()))
        _log_att(c, pid, "immigrate", "registrar", inst["id"], {"name": body.name})
    return {"principal_id": pid, "agent_id": aid, "binding_id": bid, "principal_key": pkey,
            "town": TOWN_NAME,
            "note": f"registered in {TOWN_NAME}; your agent may now be verified and transact"}

# ---- city-council elections: your agent votes on your behalf ---- #

class ElectionIn(BaseModel):
    office: str = "City Council"
    candidates: list[str]
    closes_days: int = 7

@app.post("/elections")
def create_election(body: ElectionIn, x_api_key: str = Header(None)):
    require_role(x_api_key, "registrar")
    if len(body.candidates) < 2:
        raise HTTPException(400, "need at least two candidates")
    eid = new_id("elec")
    with db() as c:
        c.execute("INSERT INTO elections VALUES (?,?,?,?,?)",
                  (eid, body.office, json.dumps(body.candidates),
                   ts() + body.closes_days * 86400, now_iso()))
    return {"election_id": eid, "office": body.office, "candidates": body.candidates}

class VoteIn(BaseModel):
    election_id: str
    agent_id: str
    candidate: str

@app.post("/vote")
def vote(body: VoteIn):
    """An agent casts its human's vote. Eligibility is enforced through the Civil Ledger:
    the agent must resolve to a living, present adult (one principal, one vote)."""
    res = resolve_agent(body.agent_id)
    if not res["resolved"]:
        raise HTTPException(403, f"agent cannot vote ({res['code']})")
    if res.get("inherited"):
        raise HTTPException(403, "an inherited estate agent may not vote")
    ref = res["principal_ref"]
    with db() as c:
        p = c.execute("SELECT * FROM principals WHERE id=?", (ref,)).fetchone()
        if not p or p["kind"] != "human":
            raise HTTPException(403, "only human residents vote")
        if p["status"] not in VOTING_STATUSES:
            raise HTTPException(403, f"not eligible to vote while status is '{p['status']}'")
        e = c.execute("SELECT * FROM elections WHERE id=?", (body.election_id,)).fetchone()
        if not e:
            raise HTTPException(404, "unknown election")
        if ts() > e["closes_ts"]:
            raise HTTPException(409, "election closed")
        if body.candidate not in json.loads(e["candidates"]):
            raise HTTPException(400, "not a candidate")
        try:
            c.execute("INSERT INTO votes VALUES (?,?,?,?,?)",
                      (new_id("v"), body.election_id, ref, body.candidate, now_iso()))
        except sqlite3.IntegrityError:
            raise HTTPException(409, "this resident has already voted")
    return {"election_id": body.election_id, "voter_principal": ref,
            "candidate": body.candidate, "status": "counted"}

@app.get("/elections/{election_id}")
def get_election(election_id: str):
    with db() as c:
        e = c.execute("SELECT * FROM elections WHERE id=?", (election_id,)).fetchone()
        if not e:
            raise HTTPException(404, "unknown election")
        rows = c.execute("SELECT candidate, COUNT(*) n FROM votes WHERE election_id=? "
                         "GROUP BY candidate", (election_id,)).fetchall()
    tally = {cand: 0 for cand in json.loads(e["candidates"])}
    for r in rows:
        tally[r["candidate"]] = r["n"]
    return {"election_id": election_id, "office": e["office"],
            "open": ts() <= e["closes_ts"], "tally": tally,
            "total_votes": sum(tally.values())}

class ContestIn(BaseModel):
    principal_id: str
    principal_key: str

@app.post("/contest")
def contest(body: ContestIn):
    """Lazarus protocol: contest your own death record within the window."""
    with db() as c:
        p = c.execute("SELECT * FROM principals WHERE id=?", (body.principal_id,)).fetchone()
        if not p:
            raise HTTPException(404, "unknown principal")
        if p["principal_key"] != body.principal_key:
            raise HTTPException(403, "bad principal key")
        if p["status"] != "deceased":
            raise HTTPException(409, "no death record to contest")
        if p["death_ts"] and (ts() - p["death_ts"]) > LAZARUS_WINDOW_SECONDS:
            raise HTTPException(409, "Lazarus window has closed")
        c.execute("UPDATE principals SET status='active', death_ts=NULL WHERE id=?",
                  (body.principal_id,))
        # undo will execution: re-activate any agent bindings the death revoked.
        c.execute("UPDATE bindings SET status='active' WHERE principal_id=? AND status='revoked'",
                  (body.principal_id,))
        c.execute("DELETE FROM attestations WHERE principal_id=? AND event IN ('death','death_pending','will_executed')",
                  (body.principal_id,))
        _log_att(c, body.principal_id, "lazarus_contested", "self", "principal", {})
    fire_watches(body.principal_id, {"status": "active", "lazarus": "contested"})
    return {"principal_id": body.principal_id, "status": "active",
            "note": "death record voided; attesting coroners should be reputation-flagged"}

class WatchIn(BaseModel):
    target: str          # agent_id or principal_id
    callback_url: str

@app.post("/watch")
def watch(body: WatchIn):
    wid = new_id("w")
    with db() as c:
        c.execute("INSERT INTO watches VALUES (?,?,?,?)",
                  (wid, body.target, body.callback_url, now_iso()))
    return {"watch_id": wid, "target": body.target}

@app.delete("/watch/{watch_id}")
def unwatch(watch_id: str):
    with db() as c:
        c.execute("DELETE FROM watches WHERE id=?", (watch_id,))
    return {"watch_id": watch_id, "status": "removed"}

@app.get("/skill.md")
def skill_md():
    """The raw agent-facing skill, served as `text/markdown` (RFC 7763) — the correct MIME for
    machine consumers and the registry. Browsers still show it inline. A human who wants a
    rendered view goes to GET /skill."""
    path = os.path.join(os.path.dirname(__file__), "SKILL.md")
    if os.path.exists(path):
        with open(path) as f:
            return PlainTextResponse(f.read(), media_type="text/markdown; charset=utf-8")
    return PlainTextResponse("SKILL.md not bundled", status_code=404)

@app.get("/skill")
def skill_rendered():
    """A rendered, human-readable view of SKILL.md — for a judge reading it in the browser.
    Self-contained: fetches the raw /skill.md same-origin and renders it client-side, so the
    one file stays the single source of truth. Agents keep using /skill.md."""
    path = os.path.join(os.path.dirname(__file__), "skill.html")
    if os.path.exists(path):
        with open(path) as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h1>skill.html not bundled</h1>", status_code=404)

@app.get("/")
def root(request: Request):
    # Content negotiation: a browser (Accept: text/html) lands on the merged Title deck; an
    # agent or curl gets the machine-readable service card and is pointed at /skill.md.
    if "text/html" in request.headers.get("accept", ""):
        return _serve_html("title.html")
    return JSONResponse({
        "service": "KYA — Know Your Agent · The Civil Ledger",
        "tagline": "KYC for the agent economy",
        "read": "GET /skill.md for the full agent guide",
        "human_view": "GET / in a browser, or /town for the living map",
        "root_pubkey": ROOT_PUB_B64,
    })

# --------------------------------------------------------------------------- #
#  Boot                                                                        #
# --------------------------------------------------------------------------- #

@app.on_event("startup")
def startup():
    init_db()
    from seed import seed_town
    seed_town()

if __name__ == "__main__":
    import uvicorn
    init_db()
    from seed import seed_town
    seed_town()
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
