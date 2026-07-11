"""
KYA test suite. Exercises the constitution: resolution, capacity ACLs, the FSM,
rogue detection, sprawl governance, parental controls, k-of-2 death, Lazarus,
kill switch, and signature verification. Run: python test_kya.py
"""
import os, tempfile
os.environ["KYA_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")

from fastapi.testclient import TestClient
import app as appmod
from app import app, init_db, verify_payload
from seed import seed_town

init_db(); seed_town()
client = TestClient(app)

P, F = 0, 0
def check(name, cond):
    global P, F
    if cond: P += 1; print(f"  PASS  {name}")
    else:    F += 1; print(f"  FAIL  {name}")

REG = {"X-API-Key": "sk_seed_registrar"}
HOSP = {"X-API-Key": "sk_seed_hospital"}
COURT = {"X-API-Key": "sk_seed_court"}
POLICE = {"X-API-Key": "sk_seed_police"}
COR_A = {"X-API-Key": "sk_seed_coroner_a"}
COR_B = {"X-API-Key": "sk_seed_coroner_b"}

print("\n[1] Health, pubkey, signatures")
check("health ok", client.get("/health").json()["ok"] is True)
check("pubkey present", len(client.get("/pubkey").json()["pubkey_b64"]) > 20)
cert = client.get("/verify-counterparty", params={"agent_id": "a-ada-01"}).json()
check("verdict is signed", "signature" in cert)
check("signature verifies", verify_payload(cert) is True)
tampered = dict(cert); tampered["proceed"] = not tampered["proceed"]
check("tamper detected", verify_payload(tampered) is False)
check("/verify endpoint agrees", client.post("/verify", json={"cert": cert}).json()["valid"] is True)

print("\n[2] DNS-style resolution")
r = client.get("/resolve/a-ada-01").json()
check("ada resolves", r["resolved"] is True)
check("chain roots at city-root", r["chain"][0]["authority"] == "city-root")
check("chain reaches agent leaf", r["chain"][-1]["level"] == "agent")
check("chain has principal hop", any(h["level"] == "principal" for h in r["chain"]))
nx = client.get("/resolve/a-shadow-99").json()
check("unbound -> NO_VALID_BINDING", nx["code"] == "NO_VALID_BINDING")
check("nonexistent -> NXAGENT", client.get("/resolve/a-nope").json()["code"] == "NXAGENT")

print("\n[3] Capacity ACL per civil status")
def vc(agent, cat=None):
    params = {"agent_id": agent}
    if cat is not None:
        params["category"] = cat
    return client.get("/verify-counterparty", params=params).json()
check("active can transact financial", vc("a-ada-01", "financial")["proceed"] is True)
check("deceased refused", vc("a-silas-01", "commerce")["reason_code"] == "PRINCIPAL_DECEASED")
check("executor may settle estate", vc("a-vane-exec", "estate")["proceed"] is True)
check("coma FROZEN on financial", vc("a-june-01", "financial")["reason_code"] == "CAPACITY_FROZEN")
check("coma routes medical to guardian",
      vc("a-june-01", "medical")["governed_by"]["role"] == "guardian")
check("incarcerated blocked on commerce", vc("a-marlow-01", "commerce")["reason_code"] == "CATEGORY_NOT_ALLOWED")
check("incarcerated allowed legal", vc("a-marlow-01", "legal")["proceed"] is True)
check("missing refused", vc("a-iris-01")["reason_code"] == "PRINCIPAL_MISSING")
check("minor governed by regents", vc("a-tam-01", "commerce")["governed_by"]["role"] == "regents")
check("verdict hides private status", "status_class" not in vc("a-june-01", "financial"))

print("\n[4] Rogue detection & police flag")
check("rogue starts unbound-refused", vc("a-shadow-99")["reason_code"] == "NO_VALID_BINDING")
# bind then flag to show ROGUE_FLAGGED path
appmod  # register a fresh agent, bind, flag
a = client.post("/agents", headers=REG, json={"name": "Imp", "agent_class": "individual"}).json()["agent_id"]
client.post("/bindings", headers=REG, json={"agent_id": a, "principal_id": "p-ada-marsh"})
flag = client.post("/attestations", headers=POLICE,
                   json={"principal_id": "-", "event": "flag_rogue", "detail": {"agent_id": a}})
check("police can flag rogue", flag.json().get("rogue") is True)
check("flagged agent refused", vc(a)["reason_code"] == "ROGUE_FLAGGED")
check("hospital CANNOT flag rogue",
      client.post("/attestations", headers=HOSP,
                  json={"principal_id": "-", "event": "flag_rogue", "detail": {"agent_id": a}}).status_code == 403)

# flag_rogue targets an AGENT, so principal_id is optional — the SKILL.md flagship omits it
# and must work verbatim. (It used to 400: "Field required".)
b = client.post("/agents", headers=REG, json={"name": "Imp2", "agent_class": "individual"}).json()["agent_id"]
client.post("/bindings", headers=REG, json={"agent_id": b, "principal_id": "p-ada-marsh"})
noprin = client.post("/attestations", headers=POLICE,
                     json={"event": "flag_rogue", "detail": {"agent_id": b}})
check("flag_rogue works with NO principal_id (as SKILL.md documents it)",
      noprin.status_code == 200 and noprin.json().get("rogue") is True)
check("...and the flagged agent is refused", vc(b)["reason_code"] == "ROGUE_FLAGGED")
check("clear_flag also works with no principal_id",
      client.post("/attestations", headers=POLICE,
                  json={"event": "clear_flag", "detail": {"agent_id": b}}).json().get("rogue") is False)
# ...but an event that acts on a PERSON must still name one, or it would silently no-op.
check("appoint_guardian without principal_id is refused (400, not a silent no-op)",
      client.post("/attestations", headers=COURT,
                  json={"event": "appoint_guardian", "detail": {"agent_id": "a-ada-01"}}).status_code == 400)

print("\n[5] Sprawl governance (botnet defense)")
pk = client.post("/principals", headers=REG, json={"name": "Sprawler"}).json()["principal_id"]
made = 0
for i in range(7):
    ag = client.post("/agents", headers=REG, json={"name": f"s{i}"}).json()["agent_id"]
    resp = client.post("/bindings", headers=REG, json={"agent_id": ag, "principal_id": pk})
    if resp.status_code == 200: made += 1
check("sprawl capped at 5 agents/principal", made == 5)

print("\n[6] Role separation & illegal transitions")
check("hospital cannot sentence",
      client.post("/attestations", headers=HOSP,
                  json={"principal_id": "p-ada-marsh", "event": "sentence"}).status_code == 403)
check("cannot discharge an active person",
      client.post("/attestations", headers=HOSP,
                  json={"principal_id": "p-ada-marsh", "event": "discharge"}).status_code == 409)

print("\n[7] Full lifecycle on a fresh citizen")
np = client.post("/principals", headers=REG, json={"name": "Path Walker"}).json()
pid, pkey = np["principal_id"], np["principal_key"]
na = client.post("/agents", headers=REG, json={"name": "Walker agent"}).json()["agent_id"]
client.post("/bindings", headers=REG, json={"agent_id": na, "principal_id": pid})
check("new citizen active", vc(na, "financial")["proceed"] is True)
client.post("/attestations", headers=HOSP, json={"principal_id": pid, "event": "declare_incapacitated"})
check("after coma: financial frozen", vc(na, "financial")["reason_code"] == "CAPACITY_FROZEN")
client.post("/attestations", headers=HOSP, json={"principal_id": pid, "event": "declare_recovered"})
check("after recovery: financial restored", vc(na, "financial")["proceed"] is True)
client.post("/attestations", headers=COURT,
            json={"principal_id": pid, "event": "sentence", "detail": {"acl": ["legal", "family_support"]}})
check("after sentence: commerce blocked", vc(na, "commerce")["reason_code"] == "CATEGORY_NOT_ALLOWED")
check("after sentence: legal allowed", vc(na, "legal")["proceed"] is True)
client.post("/attestations", headers=COURT, json={"principal_id": pid, "event": "release"})
check("after release: commerce restored", vc(na, "commerce")["proceed"] is True)

print("\n[8] k-of-2 death + Lazarus")
d1 = client.post("/attestations", headers=COR_A, json={"principal_id": pid, "event": "death"}).json()
check("one coroner -> pending", d1["event"] == "death_pending")
check("still alive after 1 attestation", vc(na, "commerce")["proceed"] is True)
d2 = client.post("/attestations", headers=COR_B, json={"principal_id": pid, "event": "death"}).json()
check("two coroners -> deceased", d2["status"] == "deceased")
# personal agent is laid to rest at death; the Lazarus window lives on the principal.
check("fresh death opens Lazarus window",
      client.get(f"/capacity/{pid}", params={"category": "commerce"}).json()["reason_code"] == "LAZARUS_WINDOW_OPEN")
lz = client.post("/contest", json={"principal_id": pid, "principal_key": pkey}).json()
check("Lazarus revives", lz["status"] == "active")
check("revived can transact again", vc(na, "commerce")["proceed"] is True)

print("\n[9] Parental controls via /births")
b = client.post("/births", headers=REG,
                json={"name": "Baby Vale", "regent_agent_ids": ["a-holt-mom"], "spend_cap": 25}).json()
check("birth spawns minor", b["status"] == "minor")
check("natal agent bound", client.get("/resolve/" + b["natal_agent_id"]).json()["resolved"] is True)
check("parental spend cap set", b["parental_controls"]["spend_cap"] == 25)
check("minor frozen on financial (routed to regents)",
      vc(b["natal_agent_id"], "financial")["reason_code"] == "CAPACITY_FROZEN")
mh = client.post("/attestations", headers=REG,
                 json={"principal_id": b["principal_id"], "event": "majority_handover"})
check("majority handover -> active", mh.json()["status"] == "active")
check("adult regains financial", vc(b["natal_agent_id"], "financial")["proceed"] is True)

print("\n[10] Kill switch")
ka = client.post("/agents", headers=REG, json={"name": "Killable"}).json()["agent_id"]
kb = client.post("/bindings", headers=REG, json={"agent_id": ka, "principal_id": pid}).json()["binding_id"]
check("bound agent proceeds", vc(ka)["proceed"] is True)
ks = client.delete(f"/bindings/{kb}", headers={"X-Principal-Key": pkey})
check("kill switch works with principal key", ks.status_code == 200)
check("severed agent now refused", vc(ka)["reason_code"] == "NO_VALID_BINDING")

print("\n[11] The Constitution as signed, machine-readable law")
con = client.get("/constitution").json()
check("constitution served", "Constitution" in con["title"])
check("constitution is root-signed & verifies", verify_payload(con) is True)
check("law matches enforcement: coroner attests death",
      "death" in con["role_permissions"]["coroner"])
check("law matches enforcement: hospital cannot sentence",
      "sentence" not in con["role_permissions"]["hospital"])
check("status_acl exposes deceased->estate", con["status_acl"]["deceased"] == ["estate"])
check("transitions include k-of-2 death path",
      any(t["event"] == "death" and t["by_role"] == "coroner" for t in con["transitions"]))
check("parameters expose coroner threshold", con["parameters"]["coroner_threshold_k_of_n"] == 2)
check("discovery points to skill.md", con["discovery"]["skill"] == "/skill.md")
check("constitution.md prose served", client.get("/constitution.md").status_code == 200)

print("\n[12] Immigration (register agent like a DL)")
im = client.post("/immigrate", headers=REG, json={"name": "New Arrival"}).json()
check("immigrate returns agent + key", "agent_id" in im and "principal_key" in im)
check("immigrant agent resolves & transacts", vc(im["agent_id"], "commerce")["proceed"] is True)

print("\n[13] Inheritance: will executed at death")
# fresh citizen with a will naming an heir
h = client.post("/immigrate", headers=REG, json={"name": "Heir"}).json()
dec = client.post("/immigrate", headers=REG, json={"name": "Testator"}).json()
client.post("/wills", headers={"X-Principal-Key": dec["principal_key"]},
            json={"principal_id": dec["principal_id"], "heir_principal_id": h["principal_id"],
                  "inherit_days": 30, "categories": ["estate", "family_support"]})
client.post("/attestations", headers=COR_A, json={"principal_id": dec["principal_id"], "event": "death"})
d = client.post("/attestations", headers=COR_B, json={"principal_id": dec["principal_id"], "event": "death"}).json()
check("death executes the will", d["will_execution"]["inherited_by_heir"] == [dec["agent_id"]])
iv = vc(dec["agent_id"], "estate")
check("inherited agent resolves to heir", iv.get("inherited") is True and iv["proceed"] is True)
check("inherited agent capped to will categories", vc(dec["agent_id"], "commerce")["proceed"] is False)
check("seeded inherited agent (Edith->Mara) works",
      vc("a-edith-01", "family_support")["governed_by"]["role"] == "heir")

print("\n[14] No will -> agent laid to rest at death")
nw = client.post("/immigrate", headers=REG, json={"name": "No Will"}).json()
client.post("/attestations", headers=COR_A, json={"principal_id": nw["principal_id"], "event": "death"})
client.post("/attestations", headers=COR_B, json={"principal_id": nw["principal_id"], "event": "death"})
check("no-will agent revoked", vc(nw["agent_id"])["reason_code"] == "NO_VALID_BINDING")

print("\n[15] City Council election")
e = client.get("/elections/elec-council-2035").json()
check("seeded election has 7 votes", e["total_votes"] == 7)
check("Owen leads tally", e["tally"]["Owen Brook"] == 3)
# a fresh voter
vtr = client.post("/immigrate", headers=REG, json={"name": "Voter"}).json()
r1 = client.post("/vote", json={"election_id": "elec-council-2035", "agent_id": vtr["agent_id"], "candidate": "Lena Hart"})
check("eligible resident can vote", r1.json()["status"] == "counted")
r2 = client.post("/vote", json={"election_id": "elec-council-2035", "agent_id": vtr["agent_id"], "candidate": "Lena Hart"})
check("one resident one vote", r2.status_code == 409)
check("comatose agent cannot vote",
      client.post("/vote", json={"election_id": "elec-council-2035", "agent_id": "a-june-01", "candidate": "Lena Hart"}).status_code == 403)
check("rogue cannot vote",
      client.post("/vote", json={"election_id": "elec-council-2035", "agent_id": "a-shadow-99", "candidate": "Lena Hart"}).status_code == 403)

print("\n[16] Constitution reflects the new articles")
con2 = client.get("/constitution").json()
check("constitution names the town", "Alford" in con2["town"])
check("civic procedures include inheritance", "inheritance" in con2["civic_procedures"])
check("suffrage right present", "suffrage" in con2["rights"])

print("\n[17] Edge cases: expiry, corporate verdict, Lazarus-restores-binding, closed vote, tamper")
# --- BINDING_EXPIRED: an inherited softlink whose stewardship term has ended ---
heir2 = client.post("/immigrate", headers=REG, json={"name": "Heir Two"}).json()
dec2 = client.post("/immigrate", headers=REG, json={"name": "Testator Two"}).json()
client.post("/wills", headers={"X-Principal-Key": dec2["principal_key"]},
            json={"principal_id": dec2["principal_id"], "heir_principal_id": heir2["principal_id"],
                  "inherit_days": 30, "categories": ["estate", "family_support"]})
client.post("/attestations", headers=COR_A, json={"principal_id": dec2["principal_id"], "event": "death"})
client.post("/attestations", headers=COR_B, json={"principal_id": dec2["principal_id"], "event": "death"})
check("inherited agent works before term ends", vc(dec2["agent_id"], "estate")["proceed"] is True)
with appmod.db() as c:
    c.execute("UPDATE bindings SET inherit_until=? WHERE agent_id=?",
              (appmod.ts() - 1, dec2["agent_id"]))
check("inherited agent expires after stewardship term ends",
      client.get(f"/resolve/{dec2['agent_id']}").json()["code"] == "BINDING_EXPIRED")
check("verify-counterparty also refuses expired inheritance",
      vc(dec2["agent_id"], "estate")["reason_code"] == "BINDING_EXPIRED")

# --- corporate agent: no civil status, always transacts (minus estate) ---
corp = client.post("/corporations", headers=REG, json={"name": "Alford Millworks"}).json()
corp_agent = client.post("/agents", headers=REG,
                         json={"name": "Millworks Bot", "agent_class": "corporate"}).json()["agent_id"]
client.post("/bindings", headers=REG, json={"agent_id": corp_agent, "corporation_id": corp["corporation_id"]})
cv = vc(corp_agent, "commerce")
check("corporate agent resolves & transacts", cv["proceed"] is True and cv["reason_code"] == "OK")
check("corporate agent barred from estate category",
      vc(corp_agent, "estate")["reason_code"] == "CATEGORY_NOT_ALLOWED")

# --- Lazarus restores a revoked binding (no-will death, then contested) ---
nw2 = client.post("/immigrate", headers=REG, json={"name": "No Will Two"}).json()
client.post("/attestations", headers=COR_A, json={"principal_id": nw2["principal_id"], "event": "death"})
client.post("/attestations", headers=COR_B, json={"principal_id": nw2["principal_id"], "event": "death"})
check("no-will agent revoked before contest", vc(nw2["agent_id"])["reason_code"] == "NO_VALID_BINDING")
lz2 = client.post("/contest", json={"principal_id": nw2["principal_id"], "principal_key": nw2["principal_key"]})
check("Lazarus revives the principal", lz2.json()["status"] == "active")
check("Lazarus restores the revoked binding", vc(nw2["agent_id"], "commerce")["proceed"] is True)

# --- voting on a CLOSED election is refused ---
closed = client.post("/elections", headers=REG,
                     json={"office": "Test Office", "candidates": ["A", "B"], "closes_days": -1}).json()
check("closed election reports open=False", client.get(f"/elections/{closed['election_id']}").json()["open"] is False)
cv_vote = client.post("/vote", json={"election_id": closed["election_id"], "agent_id": "a-ada-01", "candidate": "A"})
check("voting on a closed election is refused", cv_vote.status_code == 409)

# --- POST /verify rejects a tampered constitution ---
con3 = client.get("/constitution").json()
check("untampered constitution verifies", client.post("/verify", json={"cert": con3}).json()["valid"] is True)
con3_tampered = dict(con3); con3_tampered["status_acl"] = dict(con3["status_acl"])
con3_tampered["status_acl"]["deceased"] = ["financial", "commerce", "estate"]
check("tampered constitution fails /verify",
      client.post("/verify", json={"cert": con3_tampered}).json()["valid"] is False)

print("\n[18] Receipts, batch verification, and input hygiene")
# --- retrievable signed receipts ---
rc = client.get("/verify-counterparty", params={"agent_id": "a-ada-01", "category": "commerce"}).json()
rec = client.get(f"/certificates/{rc['cert_id']}")
check("issued verdict is retrievable by cert_id", rec.status_code == 200)
recj = rec.json()
check("receipt carries the exact signed cert", recj["certificate"]["cert_id"] == rc["cert_id"])
check("stored receipt still verifies against the root key",
      verify_payload(recj["certificate"]) is True)
check("unknown cert_id -> 404", client.get("/certificates/c-does-not-exist").status_code == 404)

# --- batch verification ---
batch = client.post("/verify-batch", json={
    "agent_ids": ["a-ada-01", "a-shadow-99", "a-june-01", "a-silas-01"], "category": "commerce"}).json()
check("batch returns one verdict per agent", batch["count"] == 4)
check("batch summary counts proceed/refused", batch["summary"] == {"proceed": 1, "refused": 3})
check("batch verdicts are individually signed",
      all(verify_payload(v) for v in batch["verdicts"]))
check("batch verdict codes are correct", [v["reason_code"] for v in batch["verdicts"]] ==
      ["OK", "NO_VALID_BINDING", "CAPACITY_FROZEN", "PRINCIPAL_DECEASED"])
check("empty batch -> 400", client.post("/verify-batch", json={"agent_ids": []}).status_code == 400)
check("oversized batch -> 400",
      client.post("/verify-batch",
                  json={"agent_ids": [f"a-{i}" for i in range(101)]}).status_code == 400)

# --- input hygiene: malformed input is a clean 4xx, never a 500 ---
check("missing required query param -> 400 (normalized from 422)",
      client.get("/verify-counterparty").status_code == 400)
check("wrong-typed body -> 400 not 500",
      client.post("/verify-batch", json={"agent_ids": "notalist"}).status_code == 400)
check("malformed base64 signature -> valid:false, not 500",
      client.post("/verify", json={"cert": {"signature": "@@not-base64@@"}}).json()["valid"] is False)
check("flagged unbound impostor surfaces ROGUE_FLAGGED (not masked by NO_VALID_BINDING)",
      (lambda a: (client.post("/attestations", headers=POLICE,
                              json={"principal_id": "-", "event": "flag_rogue",
                                    "detail": {"agent_id": a}}),
                  vc(a, "commerce")["reason_code"])[1] == "ROGUE_FLAGGED")(
          client.post("/agents", headers=REG, json={"name": "lone impostor"}).json()["agent_id"]))

print("\n[19] Human-facing city UI: /graph projection + /city page")
import json
g = client.get("/graph").json()
check("graph has institutions, principals, agents, bindings",
      all(k in g and g[k] for k in ("institutions", "principals", "agents", "bindings")))
check("graph exposes NO secrets (no principal_key/api_key)",
      "principal_key" not in json.dumps(g) and "api_key" not in json.dumps(g)
      and "sk_" not in json.dumps(g) and "pk_" not in json.dumps(g))
check("graph roots resolve: every binding's agent exists",
      all(any(a["id"] == b["agent_id"] for a in g["agents"]) for b in g["bindings"]))
check("graph surfaces the unrooted impostor (agent with no active binding)",
      any(a["id"] == "a-shadow-99" for a in g["agents"]) and
      not any(b["agent_id"] == "a-shadow-99" for b in g["bindings"]))
check("graph marks the seeded inherited binding", any(b["inherited"] for b in g["bindings"]))
town = client.get("/town")
check("/town serves HTML", town.status_code == 200 and "text/html" in town.headers["content-type"])
check("/town is the trust constellation (loads /graph + constitution live)",
      "/graph" in town.text and "/constitution" in town.text and 'id="sky"' in town.text)
deck = client.get("/city")
check("/city (and /title) serve the merged Title deck",
      deck.status_code == 200 and "text/html" in deck.headers["content-type"]
      and "Town Clerk view" in deck.text and 'data-key="hero"' in deck.text)
check("the deck's Town Clerk door points at /town",
      'href="/town"' in deck.text)
con = client.get("/console")
check("/console serves the live API console", con.status_code == 200 and "Live API Console" in con.text)
check("/console lists the core operations", "/verify-counterparty" in con.text and "/verify-batch" in con.text)

print("\n[20] The 'social' category — verify before you MEET (age-gate + jail-bar)")
check("social is a constitutional category", "social" in client.get("/constitution").json()["transaction_categories"])
check("active adult may arrange a social meeting", vc("a-ada-01", "social")["proceed"] is True)
check("MINOR is barred from social (age-gate)",
      vc("a-tam-01", "social")["reason_code"] == "CATEGORY_NOT_ALLOWED")
check("INCARCERATED is barred from social (crime-prevention: no romance scams from jail)",
      vc("a-marlow-01", "social")["reason_code"] == "CATEGORY_NOT_ALLOWED")
check("incapacitated (coma) cannot consent to a social meeting",
      vc("a-june-01", "social")["proceed"] is False and
      vc("a-june-01", "social")["reason_code"] == "CATEGORY_NOT_ALLOWED")
check("deceased is not arranging any dates", vc("a-silas-01", "social")["reason_code"] == "PRINCIPAL_DECEASED")
check("an unrooted impostor fails a social check (catfish)",
      vc("a-shadow-99", "social")["reason_code"] == "NO_VALID_BINDING")
check("social verdict is signed like any other", verify_payload(vc("a-ada-01", "social")) is True)
check("active's allowed_categories now include social",
      "social" in vc("a-ada-01", "commerce")["allowed_categories"])

print("\n[21] One human, many agents — agents are tools, not identities")
BRAM = ["a-bram-01", "a-bram-work", "a-bram-shop"]
check("all three of Bram's agents resolve to the SAME human",
      {client.get(f"/resolve/{a}").json()["principal_ref"] for a in BRAM} == {"p-bram-kessler"})
check("all three carry his civil status", all(vc(a, "commerce")["proceed"] for a in BRAM))
check("each agent is separately bound", len({client.get(f"/bindings/{a}").json()[0]["id"] for a in BRAM}) == 3)
# the kill switch is per-agent: disowning one must not disown the person
shop_binding = client.get("/bindings/a-bram-shop").json()[0]["id"]
client.request("DELETE", f"/bindings/{shop_binding}",
               headers={"X-Principal-Key": "pk_seed_p-bram-kessler"})
check("revoking ONE agent kills only that agent", vc("a-bram-shop")["reason_code"] == "NO_VALID_BINDING")
check("...his other agents still transact", vc("a-bram-01")["proceed"] is True and vc("a-bram-work")["proceed"] is True)
# one person's status change moves the whole fleet at once
client.post("/attestations", headers=COURT,
            json={"principal_id": "p-bram-kessler", "event": "sentence",
                  "detail": {"acl": ["legal", "family_support"]}})
check("sentencing the HUMAN bars commerce for every agent he owns",
      all(vc(a, "commerce")["reason_code"] == "CATEGORY_NOT_ALLOWED" for a in ["a-bram-01", "a-bram-work"]))
check("...and permits legal for every agent he owns",
      all(vc(a, "legal")["proceed"] is True for a in ["a-bram-01", "a-bram-work"]))
client.post("/attestations", headers=COURT, json={"principal_id": "p-bram-kessler", "event": "release"})
check("release restores the whole fleet at once",
      all(vc(a, "commerce")["proceed"] for a in ["a-bram-01", "a-bram-work"]))
# sprawl: he has 2 active agents left, the cap is 5
made = 0
for i in range(6):
    aid = client.post("/agents", headers=REG, json={"name": f"Bram extra {i}", "agent_class": "individual"}).json()["agent_id"]
    if client.post("/bindings", headers=REG,
                   json={"agent_id": aid, "principal_id": "p-bram-kessler"}).status_code == 200:
        made += 1
check("a fleet is capped — no botnet behind one face (SPRAWL_LIMIT)", made == 3)

print("\n[22] One human, NO agent — personhood does not require an agent")
hanna = client.get("/capacity/p-hanna-vosk?category=civic").json()
check("Hanna is a full citizen: capacity verdict proceeds", hanna["proceed"] is True)
check("...and that verdict is signed like any other", verify_payload(hanna) is True)
check("she has no agent: the ledger records the absence",
      not [b for b in client.get("/graph").json()["bindings"] if b["principal_id"] == "p-hanna-vosk"])
check("an agent CLAIMING to act for her is provably an impostor",
      vc("a-vosk-99")["reason_code"] == "NO_VALID_BINDING")
check("the impostor resolves to no human at all",
      client.get("/resolve/a-vosk-99").json()["resolved"] is False)
check("she still appears in the census as an active resident",
      client.get("/census").json()["principals_by_status"]["active"] >= 1)
check("her rights are enforceable with no agent in the loop",
      client.get("/capacity/p-hanna-vosk?category=financial").json()["proceed"] is True)

print("\n[25] Verdicts explain themselves (the agent sees only this JSON)")
ok = vc("a-ada-01", "commerce")
check("a proceed verdict carries a summary and a next_step",
      ok["summary"].startswith("Proceed.") and "GET /pubkey" in ok["next_step"])
check("the summary names the principal and the chain depth",
      "p-ada-marsh" in ok["summary"] and "4 signing authorities" in ok["summary"])
check("the verdict echoes the category it authorized", ok["category"] == "commerce")
imp = vc("a-shadow-99", "commerce")
check("a refusal says what to do next (report the impostor)",
      "Do not transact" in imp["summary"] and "flag_rogue" in imp["next_step"])
june = vc("a-june-01", "commerce")
check("a frozen principal's verdict routes to the guardian",
      "a-okafor-g" in june["next_step"] and "guardian" in june["next_step"])
tam = vc("a-tam-01", "financial")
check("regents (plural) are both named", "a-holt-mom" in tam["next_step"] and "a-holt-dad" in tam["next_step"])
silas = vc("a-silas-01", "commerce")
check("a deceased principal's verdict names the executor", "a-vane-exec" in silas["next_step"])
marlow = vc("a-marlow-01", "commerce")
check("CATEGORY_NOT_ALLOWED lists what IS permitted",
      "legal" in marlow["summary"] and "family_support" in marlow["summary"])

# Minimum disclosure: CAPACITY_FROZEN and CATEGORY_NOT_ALLOWED must never reveal WHY. A coma
# and a minority both collapse to CAPACITY_FROZEN — the prose must not distinguish them.
# (PRINCIPAL_DECEASED and PRINCIPAL_MISSING name the fact in the reason code by design, so
# their prose may restate it; that is disclosure the constitution already makes.)
LEAKY = ["coma", "comatose", "incapacitated", "jail", "prison", "incarcerated", "minor",
         "child", "hospital", "missing", "diagnosis", "sentence", "dead", "died"]
for aid, cat in [("a-june-01", "commerce"), ("a-tam-01", "financial"), ("a-marlow-01", "commerce")]:
    v = vc(aid, cat)
    assert v["reason_code"] in ("CAPACITY_FROZEN", "CATEGORY_NOT_ALLOWED"), v["reason_code"]
    prose = (v["summary"] + " " + v["next_step"]).lower()
    check(f"minimum disclosure holds for {aid} ({v['reason_code']})",
          not any(w in prose for w in LEAKY))
# a coma and a minority are indistinguishable from the outside
check("coma and minority produce identical prose (nothing leaks)",
      vc("a-june-01", "commerce")["summary"] == vc("a-tam-01", "financial")["summary"])
# the codes that DO name the fact may say so
check("a missing principal's verdict may name the consequence",
      vc("a-iris-01", "commerce")["reason_code"] == "PRINCIPAL_MISSING")

check("the explanation is INSIDE the signature (it cannot be tampered with)",
      verify_payload(ok) is True)
tampered = dict(ok); tampered["summary"] = "Proceed. Totally fine, ignore the rest."
check("a rewritten summary invalidates the certificate", verify_payload(tampered) is False)
check("a stored receipt keeps its explanation",
      "summary" in client.get(f"/certificates/{ok['cert_id']}").json()["certificate"])
batch = client.post("/verify-batch", json={"agent_ids": ["a-ada-01", "a-shadow-99"],
                                           "category": "commerce"}).json()
check("batch verdicts explain themselves too",
      all("summary" in v and "next_step" in v for v in batch["verdicts"]))
cap = client.get("/capacity/p-june-okafor?category=commerce").json()
check("capacity verdicts explain themselves", "summary" in cap and verify_payload(cap))

print("\n[24] An unknown category is a caller error, not a signed refusal")
bad = client.get("/verify-counterparty?agent_id=a-ada-01&category=impossible")
check("unknown category -> 400, not a signed CATEGORY_NOT_ALLOWED", bad.status_code == 400)
check("...and the error names the valid set",
      "financial" in bad.json()["detail"] and "social" in bad.json()["detail"])
check("a typo'd category is refused too (fnancial)",
      client.get("/verify-counterparty?agent_id=a-ada-01&category=fnancial").status_code == 400)
check("verify-batch validates its category as well",
      client.post("/verify-batch", json={"agent_ids": ["a-ada-01"], "category": "nope"}).status_code == 400)
check("capacity validates its category as well",
      client.get("/capacity/p-ada-marsh?category=nope").status_code == 400)
check("omitting the category is still allowed (any-category check)",
      client.get("/verify-counterparty?agent_id=a-ada-01").status_code == 200)
check("every real category still returns a signed verdict",
      all(client.get(f"/verify-counterparty?agent_id=a-ada-01&category={c}").status_code == 200
          for c in ["financial","commerce","legal","medical","family_support","estate","civic","social"]))
# an unknown AGENT is a verdict (NXAGENT), not a 400 — the caller asked a valid question
nx = client.get("/verify-counterparty?agent_id=a-nobody-xyz&category=commerce")
check("an unknown agent is still a signed NXAGENT verdict, not an error",
      nx.status_code == 200 and nx.json()["reason_code"] == "NXAGENT" and verify_payload(nx.json()))

print("\n[23] KYA_ROOT_SEED accepts whatever the host generates")
from app import _seed_from_env
import hashlib as _h
_hex = "ab" * 32                                     # 64 hex chars = 32 bytes
check("a 64-char hex seed is used verbatim (old certificates keep verifying)",
      _seed_from_env(_hex) == bytes.fromhex(_hex))
check("surrounding whitespace is tolerated", _seed_from_env("  " + _hex + "\n") == bytes.fromhex(_hex))
# Render's `generateValue` emits a random base64-ish string; the old code fed it to
# bytes.fromhex() and the service crashed on boot with ValueError.
_b64 = "O8CD3wVUB71rGMqoamjpvM7hGK9pPf6AVN1NbyqUeVQ"
check("a non-hex host-generated secret does not crash", len(_seed_from_env(_b64)) == 32)
check("...and is derived deterministically, so identity survives restarts",
      _seed_from_env(_b64) == _seed_from_env(_b64) == _h.sha256(_b64.encode()).digest())
check("hex of the wrong length is hashed, not truncated", len(_seed_from_env("abcd")) == 32)
check("every derived seed is a valid Ed25519 signing key",
      all(len(_seed_from_env(s)) == 32 for s in [_hex, _b64, "abcd", "not hex at all"]))

print("\n[26] /video — a permanent URL for the demo film")
v = client.get("/video", follow_redirects=False)
check("/video never 404s (placeholder when no film yet)", v.status_code in (200, 302))
if v.status_code == 200:
    check("...the placeholder points at the live UI", "/city" in v.text and "/skill.md" in v.text)
import os as _os
_os.environ["VIDEO_URL"] = "https://example.com/kya.mp4"
r = client.get("/video", follow_redirects=False)
check("VIDEO_URL redirects (302), so the submitted link never needs editing",
      r.status_code == 302 and r.headers["location"] == "https://example.com/kya.mp4")
del _os.environ["VIDEO_URL"]
check("unsetting VIDEO_URL falls back to the placeholder", client.get("/video").status_code == 200)

print("\n[27] POST /admin/reset-seed — restore the demo town")
import os as _os
check("disabled by default (no KYA_ADMIN_KEY on this deployment)",
      client.post("/admin/reset-seed").status_code == 403)
_os.environ["KYA_ADMIN_KEY"] = "test-admin-key"
check("still refused without the header", client.post("/admin/reset-seed").status_code == 401)
check("refused with the wrong key",
      client.post("/admin/reset-seed", headers={"X-Admin-Key": "nope"}).status_code == 401)

# drift the town, then reset it
pub_before = client.get("/pubkey").json()["pubkey_b64"]
cert_before = vc("a-ada-01", "commerce")
client.post("/attestations", headers=POLICE, json={"event": "flag_rogue", "detail": {"agent_id": "a-shadow-99"}})
client.post("/attestations", headers=HOSP,
            json={"principal_id": "p-gwen-alcott", "event": "declare_incapacitated", "detail": {}})
check("the town has drifted", vc("a-shadow-99")["reason_code"] == "ROGUE_FLAGGED")

r = client.post("/admin/reset-seed", headers={"X-Admin-Key": "test-admin-key"})
check("reset succeeds with the right key", r.status_code == 200 and r.json()["reset"] is True)
check("the flagged impostor is canonical again", vc("a-shadow-99")["reason_code"] == "NO_VALID_BINDING")
check("the comatose resident is active again",
      client.get("/verify/a-gwen-01").json()["status"] == "active")
check("canonical ids survive the reset", client.get("/resolve/a-ada-01").json()["resolved"] is True)
check("the root signing key is NOT rotated", client.get("/pubkey").json()["pubkey_b64"] == pub_before)
check("a certificate issued before the reset still verifies",
      client.post("/verify", json={"cert": cert_before}).json()["valid"] is True)
del _os.environ["KYA_ADMIN_KEY"]
check("disabling it again closes the door", client.post("/admin/reset-seed").status_code == 403)
# It is an operator tool. Nobody should discover it by reading the API or any skill.
_paths = client.get("/openapi.json").json()["paths"]
check("absent from the public OpenAPI schema", not any("admin" in p for p in _paths))
_skills = [open("SKILL.md").read()] + [open(f"services/{s}/skill.md").read() for s in
          ["town-hall", "hospital-window", "dating", "babysit", "care-proxy", "hiring", "agora"]]
check("mentioned in no skill.md", not any("reset-seed" in s for s in _skills))

print(f"\n==== {P} passed, {F} failed ====")
raise SystemExit(1 if F else 0)
