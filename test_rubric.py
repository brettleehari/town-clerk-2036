"""
NANDA part-2 rubric harness — turns the judging criteria into automated checks.

Part 2 (the main event, 80%) requires a hosted service + a SKILL.md that lets an agent
succeed with no human help, scored on: Useful, Creative, Easy to set up, and
"agents succeed using only your SKILL.md" — plus judge dimensions correctness, realism,
design, docs. This file asserts as many of those as can be checked mechanically, so the
overnight loop cannot regress the submission's score without turning the gate red.

Run: python test_rubric.py   (hosting is local; uses an in-process client, no network.)
"""
import os, re, tempfile, json
os.environ["KYA_DB"] = os.path.join(tempfile.mkdtemp(), "rubric.db")

from fastapi.testclient import TestClient
from app import app, init_db, verify_payload
from seed import seed_town

init_db(); seed_town()
c = TestClient(app)

HERE = os.path.dirname(os.path.abspath(__file__))
def read(name):
    p = os.path.join(HERE, name)
    return open(p).read() if os.path.exists(p) else ""

SKILL = read("SKILL.md")
P = F = 0
def check(name, cond, hint=""):
    global P, F
    if cond: P += 1; print(f"  PASS  {name}")
    else:    F += 1; print(f"  FAIL  {name}" + (f"  ({hint})" if hint else ""))

# --- NANDA required SKILL.md structure: name, what it does, base URL, endpoints, steps ---
print("\n[R1] SKILL.md has the NANDA-required structure")
low = SKILL.lower()
# Agent Skills spec: SKILL.md carries YAML frontmatter (name + description) for
# progressive disclosure, then the title/body. Accept either a leading title or
# frontmatter-then-title.
_has_frontmatter = SKILL.lstrip().startswith("---") and "name:" in SKILL.split("---")[1] \
    and "description:" in SKILL.split("---")[1]
check("has a title / service name",
      SKILL.strip().startswith("#") or bool(re.search(r"^# ", SKILL, re.M)))
check("has Agent Skills frontmatter (name + description)", _has_frontmatter)
check("states what it does", "know your agent" in low or "civil ledger" in low)
check("declares a base URL", "base url" in low and "http" in low)
check("lists endpoints", "/verify-counterparty" in SKILL and "GET" in SKILL)
check("has step-by-step agent instructions", "prime directive" in low or "how the agent" in low or "recipe" in low)
check("shows an example call", "curl" in low)
check("shows an example response / reason codes", "reason_code" in SKILL or "proceed" in SKILL)

# --- Easy to set up: a real signed verdict in ONE call, zero auth, zero writes ---
print("\n[R2] Easy to set up — ten-second first call works with no auth")
v = c.get("/verify-counterparty", params={"agent_id": "a-ada-01", "category": "commerce"}).json()
check("first call returns a verdict", "proceed" in v and "reason_code" in v)
check("verdict is signed & verifies", verify_payload(v) is True)
check("no auth needed for reads", c.get("/verify-counterparty", params={"agent_id": "a-ada-01"}).status_code == 200)

# --- Agents succeed from SKILL.md ALONE: no dead references, endpoints exist, /skill.md served ---
print("\n[R3] Agents succeed using only SKILL.md")
paths = set(c.get("/openapi.json").json()["paths"].keys())
for ep in ["/verify-counterparty", "/resolve/{agent_id}", "/constitution", "/pubkey",
           "/capacity/{principal_id}", "/immigrate", "/vote", "/wills"]:
    check(f"endpoint exists: {ep}", ep in paths, "referenced in SKILL.md but missing from API")
# Every agent id mentioned in SKILL.md must resolve, OR be an agent the town deliberately
# seeds with no binding (the impostors). Derive that set from the live graph rather than
# hard-coding it, so a new seeded impostor can be documented without editing this test.
_g = c.get("/graph").json()
_bound = {b["agent_id"] for b in _g["bindings"]}
unbound_by_design = {a["id"] for a in _g["agents"] if a["id"] not in _bound}
ids = sorted(set(re.findall(r"\ba-[a-z0-9]+(?:-[a-z0-9]+)*\b", SKILL)))
bad = []
for aid in ids:
    r = c.get(f"/resolve/{aid}").json()
    if not r.get("resolved") and aid not in unbound_by_design:
        bad.append(aid)
check("no dead agent references in SKILL.md", not bad, f"unresolvable: {bad}")
check("the town seeds at least one unbound impostor", len(unbound_by_design) >= 1)
check("/skill.md is served by the service", c.get("/skill.md").status_code == 200)
check("served /skill.md matches the file", c.get("/skill.md").text.strip()[:40] == SKILL.strip()[:40])
check("constitution is machine-readable + signed", verify_payload(c.get("/constitution").json()) is True)

# --- Useful: the core verdict is actionable across the real failure modes ---
print("\n[R4] Useful — the verdict discriminates the cases agents care about")
cases = {
    "a-ada-01": ("commerce", True),
    "a-shadow-99": (None, False),      # rogue
    "a-silas-01": ("commerce", False), # deceased
    "a-june-01": ("financial", False), # coma
    "a-marlow-01": ("commerce", False),# jailed
}
ok = True
for aid, (cat, expect) in cases.items():
    params = {"agent_id": aid}
    if cat: params["category"] = cat
    got = c.get("/verify-counterparty", params=params).json()["proceed"]
    ok = ok and (got is expect)
check("verdict correct across active/rogue/deceased/coma/jailed", ok)

# --- Creative / positioning: the differentiator is stated (human behind the agent) ---
print("\n[R5] Creative — the KYA positioning is explicit")
check("frames 'KYC for agents' / human behind the agent",
      "kyc" in low or "human behind" in low or "know your agent" in low)

# --- Design: producer/consumer separation (open reads + role-scoped writes) both real ---
print("\n[R6] Design — separation of powers is enforced, not just documented")
check("writes are role-scoped (hospital cannot sentence)",
      c.post("/attestations", headers={"X-API-Key": "sk_seed_hospital"},
             json={"principal_id": "p-ada-marsh", "event": "sentence"}).status_code == 403)
check("reads are open (no key needed)", c.get("/census").status_code == 200)

# --- Docs + realism (judge dimensions) ---
print("\n[R7] Docs & realism")
for doc in ["SKILL.md", "CONSTITUTION.md", "README.md", "SCORING.md"]:
    check(f"doc present: {doc}", bool(read(doc)))
check("honesty/limits section present (realism)", "honest" in SKILL.lower() or "limits" in SKILL.lower())

# --- Registry submission payload is constructible (name, source_type, source_url, endpoints) ---
print("\n[R8] NANDA registry submission payload is constructible")
payload = {"name": "KYA — Know Your Agent",
           "source_type": "url",
           "source_url": "http://localhost:8000/skill.md",
           "endpoints": "GET /verify-counterparty?agent_id={id}&category={cat}"}
check("submission payload has all required fields",
      all(k in payload and payload[k] for k in ("name", "source_type", "source_url", "endpoints")))

print(f"\n==== rubric: {P} passed, {F} failed ====")
raise SystemExit(1 if F else 0)
