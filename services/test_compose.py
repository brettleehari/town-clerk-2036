"""
Composition test — the full journey, proven end to end.

Stands up the Civil Ledger in-process, then wires each front-door service's ledger client
to it (the same trick the real deployment does over HTTP via LEDGER_URL). Verifies:

  town-hall onboards a new agent  ->  that SAME agent then uses dating / babysit / care,
  and every constitutional rule (minor, incarcerated, guardian routing, orphaned) holds.

Run:  python3 services/test_compose.py     (from the repo root)
"""
import importlib.util
import os
import sys
import tempfile

os.environ["KYA_DB"] = os.path.join(tempfile.mkdtemp(), "compose.db")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from fastapi.testclient import TestClient
import app as ledger_app
from seed import seed_town

ledger_app.init_db(); seed_town()
LEDGER = TestClient(ledger_app.app)

def load(name):
    path = os.path.join(ROOT, "services", name, "main.py")
    spec = importlib.util.spec_from_file_location(f"svc_{name.replace('-', '_')}", path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod

date = load("dating")
baby = load("babysit")
care = load("care-proxy")
hall = load("town-hall")
hire = load("hiring")
agora = load("agora")
hosp = load("hospital-window")

# --- compose: point each service's ledger client at the in-process ledger ---
from fastapi import HTTPException

def _get(path): return LEDGER.get(path).json()
def _req(method, path, **kw): return LEDGER.request(method, path, **kw).json()

def _req_strict(method, path, **kw):
    """Mirror the real httpx client: a 4xx from the ledger raises, so the service's error
    handling (illegal FSM transitions, unresolvable agents) is exercised, not skipped."""
    r = LEDGER.request(method, path, **kw)
    if r.status_code >= 400:
        raise HTTPException(r.status_code, _detail(r))
    return r.json()

def _detail(r):
    try:    return r.json().get("detail", r.text)
    except Exception: return r.text

date._ledger_get = _get
baby._ledger_get = _get
care._ledger_get = _get
hall._ledger = _req
hire._ledger_get = _get
agora._ledger_get = _get
hosp._ledger = _req_strict

DC, BC, CC, HC = (TestClient(m.app) for m in (date, baby, care, hall))
RC, AC, WC = (TestClient(m.app) for m in (hire, agora, hosp))

P = F = 0
def check(name, cond, extra=""):
    global P, F
    if cond: P += 1; print(f"  PASS  {name}")
    else:    F += 1; print(f"  FAIL  {name}  {extra}")

print("\n[1] town-hall: a person arrives and mints a verified agent")
r = HC.post("/move-to-town", json={"name": "Rae Fenn"}).json()
new_agent = r.get("agent_id")
check("onboarded, got an agent id", bool(new_agent), r)
check("new agent is immediately verifiable", r.get("now_verifiable", {}).get("real_person") is True)
check("new agent is social-eligible (active adult)", r["now_verifiable"]["social_ok"] is True)

print("\n[2] dating: the NEW agent arranges a date with a seeded resident")
d = DC.post("/arrange-meeting", json={"my_agent": new_agent, "their_agent": "a-ada-01"}).json()
check("meeting arranged between two verified adults", d.get("both_verified") is True)
check("a time was proposed or 'no free time'", ("proposed_time" in d) or ("no mutually" in d.get("reason", "")))
d2 = DC.post("/arrange-meeting", json={"my_agent": new_agent, "their_agent": "a-tam-01"}).json()
check("date refused with a minor (no reason leaked)", d2["arranged"] is False and "reason" in d2)
d3 = DC.post("/arrange-meeting", json={"my_agent": new_agent, "their_agent": "a-marlow-01"}).json()
check("date refused with an incarcerated match", d3["arranged"] is False)
d4 = DC.post("/arrange-meeting", json={"my_agent": new_agent, "their_agent": "a-shadow-99"}).json()
check("date refused with an orphaned/rogue agent", d4["arranged"] is False)

print("\n[3] babysit: verify the sitter is a safe adult")
b = BC.post("/book-sitter", json={"parent_agent": new_agent, "sitter_agent": "a-lena-01"}).json()
check("active adult sitter -> booked", b.get("sitter_verified") is True)
b2 = BC.post("/book-sitter", json={"parent_agent": new_agent, "sitter_agent": "a-marlow-01"}).json()
check("incarcerated sitter refused", b2["booked"] is False)
b3 = BC.post("/book-sitter", json={"parent_agent": new_agent, "sitter_agent": "a-tam-01"}).json()
check("a minor cannot be the sitter", b3["booked"] is False)
b4 = BC.post("/book-sitter", json={"parent_agent": "a-holt-mom", "sitter_agent": "a-lena-01",
                                   "child_agent": "a-tam-01"}).json()
check("registered guardian may book for their child", b4.get("sitter_verified") is True)
b5 = BC.post("/book-sitter", json={"parent_agent": new_agent, "sitter_agent": "a-lena-01",
                                   "child_agent": "a-tam-01"}).json()
check("non-guardian refused for that child", b5["booked"] is False)

print("\n[4] care-proxy: guardian routing for an incapacitated patient")
c = CC.post("/authorize-care", json={"requesting_agent": "a-okafor-g", "patient_agent": "a-june-01"}).json()
check("guardian authorized for comatose patient", c.get("authorized") is True and c.get("acting_as") == "guardian")
c2 = CC.post("/authorize-care", json={"requesting_agent": "a-june-01", "patient_agent": "a-june-01"}).json()
check("patient's own agent routed to guardian", c2["authorized"] is False and c2.get("route_to") == "a-okafor-g")
c3 = CC.post("/authorize-care", json={"requesting_agent": new_agent, "patient_agent": new_agent}).json()
check("capable patient self-authorizes", c3.get("authorized") is True and c3.get("acting_as") == "self")
c4 = CC.post("/authorize-care", json={"requesting_agent": new_agent, "patient_agent": "a-silas-01"}).json()
check("no care authorization for a deceased patient", c4["authorized"] is False)

print("\n[5] hiring: verify the worker is a capable, present adult")
h = RC.post("/offer-work", json={"employer_agent": "a-store-01", "worker_agent": "a-ada-01",
                                 "role": "shopkeeper"}).json()
check("active adult -> hired", h.get("hired") is True and h.get("worker_status") == "active")
h2 = RC.post("/offer-work", json={"employer_agent": "a-store-01", "worker_agent": "a-tam-01",
                                  "role": "shopkeeper"}).json()
check("a minor is refused (no child labor)", h2["hired"] is False and "child labor" in h2["reason"])
h3 = RC.post("/offer-work", json={"employer_agent": "a-store-01", "worker_agent": "a-marlow-01",
                                  "role": "shopkeeper"}).json()
check("incarcerated worker refused (cannot contract from custody)",
      h3["hired"] is False and h3["worker_status"] == "incarcerated")
h4 = RC.post("/offer-work", json={"employer_agent": "a-store-01", "worker_agent": "a-shadow-99",
                                  "role": "shopkeeper"}).json()
check("orphaned/rogue agent refused (no human behind it)",
      h4["hired"] is False and h4["worker_status"] == "orphaned")
h5 = RC.post("/offer-work", json={"employer_agent": "a-store-01", "worker_agent": "a-cyrus-01",
                                  "role": "remote clerk"}).json()
check("conscious inpatient keeps the right to contract", h5.get("hired") is True)

print("\n[6] agora: the SIGNED commerce verdict gates the sale")
s = AC.post("/can-i-sell", json={"seller_agent": "a-store-01", "buyer_agent": "a-ada-01",
                                 "amount": 49.99}).json()
check("active buyer -> sale proceeds", s.get("sell") is True)
check("sale carries a re-verifiable signed certificate id", bool(s.get("certificate_id")))
check("the certificate resolves at the ledger",
      LEDGER.get(f"/certificates/{s['certificate_id']}").status_code == 200)
s2 = AC.post("/can-i-sell", json={"seller_agent": "a-store-01", "buyer_agent": "a-silas-01",
                                  "amount": 10}).json()
check("deceased buyer refused PRINCIPAL_DECEASED",
      s2["sell"] is False and s2["reason_code"] == "PRINCIPAL_DECEASED")
s3 = AC.post("/can-i-sell", json={"seller_agent": "a-store-01", "buyer_agent": "a-marlow-01",
                                  "amount": 10}).json()
check("incarcerated buyer refused CATEGORY_NOT_ALLOWED",
      s3["sell"] is False and s3["reason_code"] == "CATEGORY_NOT_ALLOWED")
s4 = AC.post("/can-i-sell", json={"seller_agent": "a-store-01", "buyer_agent": "a-june-01",
                                  "amount": 10}).json()
check("comatose buyer refused CAPACITY_FROZEN",
      s4["sell"] is False and s4["reason_code"] == "CAPACITY_FROZEN")
s5 = AC.post("/can-i-sell", json={"seller_agent": "a-store-01", "buyer_agent": "a-shadow-99",
                                  "amount": 10}).json()
check("orphaned buyer refused NO_VALID_BINDING",
      s5["sell"] is False and s5["reason_code"] == "NO_VALID_BINDING")

print("\n[7] hospital-window: a PRODUCER changes a status; consumers react with no notification")
w = WC.post("/admit", json={"patient_agent": "a-gwen-01"}).json()
check("admit -> hospitalized", w.get("status") == "hospitalized")
check("a conscious inpatient keeps social rights", w.get("social_ok") is True)
check("...and may still be hired",
      RC.post("/offer-work", json={"employer_agent": "a-store-01", "worker_agent": "a-gwen-01",
                                   "role": "remote clerk"}).json()["hired"] is True)
w2 = WC.post("/discharge", json={"patient_agent": "a-gwen-01"}).json()
check("discharge -> active", w2.get("status") == "active")
w3 = WC.post("/discharge", json={"patient_agent": "a-gwen-01"})
check("discharging a non-inpatient is an illegal transition (409)", w3.status_code == 409)
w4 = WC.post("/admit", json={"patient_agent": "a-shadow-99"})
check("cannot attest about an agent with no human behind it (404)", w4.status_code == 404)

print("\n[8] the money shot: two front doors coordinate through the ledger alone")
r2 = HC.post("/move-to-town", json={"name": "Otto Lang"}).json()
otto, otto_p = r2["agent_id"], r2["principal_id"]
check("otto onboards as an active adult", r2["now_verifiable"]["status"] == "active")
check("otto can be hired while active",
      RC.post("/offer-work", json={"employer_agent": "a-store-01", "worker_agent": otto,
                                   "role": "clerk"}).json()["hired"] is True)
# the town court appoints Ada as Otto's guardian (only a court may do this)
LEDGER.post("/attestations", headers={"X-API-Key": "sk_seed_court"},
            json={"principal_id": otto_p, "event": "appoint_guardian",
                  "detail": {"agent_id": "a-ada-01"}})
# the hospital declares Otto incapacitated — it tells NO ONE but the ledger
w5 = WC.post("/declare-incapacitated", json={"patient_agent": otto}).json()
check("hospital declares otto incapacitated", w5.get("status") == "incapacitated")
check("the ledger now reports otto is governed by his guardian",
      w5.get("now_governed_by", {}).get("agent") == "a-ada-01")
# ...and every other front door reacts, having been told nothing
check("care-proxy now routes otto's care to his guardian",
      CC.post("/authorize-care", json={"requesting_agent": "a-ada-01",
                                       "patient_agent": otto}).json().get("acting_as") == "guardian")
check("care-proxy refuses otto's own agent, naming the guardian",
      CC.post("/authorize-care", json={"requesting_agent": otto,
                                       "patient_agent": otto}).json().get("route_to") == "a-ada-01")
check("hiring now refuses otto (cannot consent)",
      RC.post("/offer-work", json={"employer_agent": "a-store-01", "worker_agent": otto,
                                   "role": "clerk"}).json()["hired"] is False)
check("agora now refuses otto CAPACITY_FROZEN",
      AC.post("/can-i-sell", json={"seller_agent": "a-store-01", "buyer_agent": otto,
                                   "amount": 5}).json()["reason_code"] == "CAPACITY_FROZEN")
check("dating now refuses otto a meeting",
      DC.post("/arrange-meeting", json={"my_agent": "a-ada-01",
                                        "their_agent": otto}).json()["arranged"] is False)
check("babysit now refuses otto as a sitter",
      BC.post("/book-sitter", json={"parent_agent": "a-ada-01",
                                    "sitter_agent": otto}).json()["booked"] is False)

print("\n[9] Parental controls survive the front doors")
# care-proxy: a minor is governed by REGENTS. Reading only role=="guardian" let a 14-year-old
# authorise his own surgery while his parents were refused.
m = CC.post("/authorize-care", json={"requesting_agent": "a-holt-mom", "patient_agent": "a-tam-01"}).json()
check("a regent may authorize care for their child", m.get("authorized") is True and m["acting_as"] == "regents")
check("either parent works",
      CC.post("/authorize-care", json={"requesting_agent": "a-holt-dad", "patient_agent": "a-tam-01"}).json()["authorized"] is True)
self_auth = CC.post("/authorize-care", json={"requesting_agent": "a-tam-01", "patient_agent": "a-tam-01"}).json()
check("the minor may NOT authorize their own care", self_auth["authorized"] is False)
check("...and the refusal names both regents", set(self_auth["route_to"]) == {"a-holt-mom", "a-holt-dad"})
check("a comatose adult still routes to their guardian",
      CC.post("/authorize-care", json={"requesting_agent": "a-okafor-g", "patient_agent": "a-june-01"}).json()["acting_as"] == "guardian")
check("a capable adult still self-authorizes",
      CC.post("/authorize-care", json={"requesting_agent": "a-ada-01", "patient_agent": "a-ada-01"}).json()["acting_as"] == "self")

# agora: `proceed` authorises the CATEGORY, not the AMOUNT. A minor carries a spend cap.
under = AC.post("/can-i-sell", json={"seller_agent": "a-store-01", "buyer_agent": "a-tam-01", "amount": 50}).json()
check("a minor may buy up to their spend cap", under["sell"] is True)
over = AC.post("/can-i-sell", json={"seller_agent": "a-store-01", "buyer_agent": "a-tam-01", "amount": 100000}).json()
check("a minor may NOT buy above it (no $100k sale to a 14-year-old)",
      over["sell"] is False and over["reason_code"] == "SPEND_CAP_EXCEEDED")
check("...and the refusal routes to the regents", set(over["route_to"]) == {"a-holt-mom", "a-holt-dad"})
check("an adult has no cap and is unaffected",
      AC.post("/can-i-sell", json={"seller_agent": "a-store-01", "buyer_agent": "a-ada-01", "amount": 100000}).json()["sell"] is True)

print("\n[10] hospital-window survives a stale institution key")
# POST /admin/reset-seed deletes every institution, invalidating the key this service
# self-registered at boot. It used to report that as a 409 "illegal transition", which is a
# clinical claim about the patient rather than the truth about our credential.
hosp._key_cache["hospital"] = "sk_this_key_no_longer_exists"
r = WC.post("/admit", json={"patient_agent": "a-gwen-01"})
check("a stale key is re-registered, not reported as an illegal transition",
      r.status_code == 200 and r.json()["status"] == "hospitalized")
r = WC.post("/discharge", json={"patient_agent": "a-gwen-01"})
check("...and the patient is restored", r.status_code == 200 and r.json()["status"] == "active")
r = WC.post("/admit", json={"patient_agent": "a-silas-01"})
check("a GENUINE illegal transition still returns 409 with the real status",
      r.status_code == 409 and "deceased" in r.json()["detail"])

print(f"\n==== compose: {P} passed, {F} failed ====")
raise SystemExit(1 if F else 0)
