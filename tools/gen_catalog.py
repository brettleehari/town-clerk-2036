#!/usr/bin/env python3
"""Exercise every endpoint of the four submitted services and emit API_CATALOG.md.

Each entry is a real request and the real response it produced. Nothing is hand-written, so
the catalog cannot drift from the code.

    # start the four services locally, then:
    KYA_ADMIN_KEY=demo-admin-key python3 tools/gen_catalog.py API_CATALOG.md

The ledger section covers all 36 public routes. The write plane runs in dependency order — a citizen
is born, binds an agent, throws the kill switch, writes a will, dies under k-of-2 coroners and
is contested back to life — and the town is reset at the end, so a run leaves no residue.
"""
import json
import os
import sys

import httpx

LOCAL = {"ledger": "http://127.0.0.1:8000", "agora": "http://127.0.0.1:8105",
         "care": "http://127.0.0.1:8102", "hosp": "http://127.0.0.1:8106"}
PUBLIC = {"ledger": "https://civil-ledger.onrender.com", "agora": "https://agora-egpi.onrender.com",
          "care": "https://care-proxy.onrender.com", "hosp": "https://hospital-window.onrender.com"}
ADMIN = os.environ.get("KYA_ADMIN_KEY", "demo-admin-key")

c = httpx.Client(timeout=60)
out = []


def call(svc, method, path, body=None, note=None, headers=None, trunc=None, show_body=True):
    r = c.request(method, LOCAL[svc] + path, json=body, headers=headers, follow_redirects=False)
    if "json" in r.headers.get("content-type", ""):
        text, lang = json.dumps(r.json(), indent=2), "json"
    else:
        text, lang = r.text, "text"
    if trunc and len(text) > trunc:
        text = text[:trunc].rstrip() + f"\n… ({len(r.text)} bytes total)"
    req = f"{method} {PUBLIC[svc] + path}"
    for k, v in (headers or {}).items():
        req += f"\n  -H '{k}: {v}'"
    if body is not None and show_body:
        req += "\n  -d '" + json.dumps(body) + "'"
    out.append({"req": req, "status": r.status_code, "resp": text, "note": note, "lang": lang})
    return r


def h(title, level=2):
    out.append({"heading": title, "level": level})


def p(text):
    out.append({"prose": text})


L = LOCAL["ledger"]
SEED = {"registrar": "sk_seed_registrar", "court": "sk_seed_court", "hospital": "sk_seed_hospital",
        "police": "sk_seed_police", "coroner_a": "sk_seed_coroner_a", "coroner_b": "sk_seed_coroner_b"}
REG = {"X-API-Key": SEED["registrar"]}

# ═════════════════════════════════ 1. civil-ledger ═══════════════════════════
h("1. civil-ledger — the Civil Ledger (KYA)")
p("Base URL `https://civil-ledger.onrender.com` · skill `name: town-ledger`. "
  "**All 36 public routes.** Every read is open and keyless; writes need a role-scoped key.")

h("Service & discovery", 3)
call("ledger", "GET", "/health")
call("ledger", "GET", "/pubkey", note="Verify every certificate against this key.")
call("ledger", "GET", "/skill.md", trunc=320,
     note="This service's agent-facing skill, always in sync with the deployment.")
call("ledger", "GET", "/openapi.json", trunc=240, note="Machine-readable mirror of the same contract.")
call("ledger", "GET", "/video", trunc=280,
     note="Permanent demo-video link: `302` to `VIDEO_URL`, else the bundled film, else this "
          "placeholder. It never 404s, so a submitted link never dies.")

h("The law", 3)
call("ledger", "GET", "/constitution", trunc=850,
     note="The town's whole law as signed JSON, **generated from the code that enforces it** — "
          "so the law you read is the law applied. Verifies like any certificate.")
call("ledger", "GET", "/constitution.md", trunc=280, note="The same law in prose.")

h("The verdict — reads, the consumer side", 3)
call("ledger", "GET", "/verify-counterparty?agent_id=a-ada-01&category=commerce",
     note="**The call.** A signed proceed/refuse verdict. `summary` and `next_step` sit inside "
          "the signature, so an explanation cannot be rewritten.")
call("ledger", "GET", "/verify-counterparty?agent_id=a-shadow-99&category=commerce", trunc=760,
     note="An impostor: resolves to no human.")
call("ledger", "GET", "/verify-counterparty?agent_id=a-june-01&category=commerce", trunc=900,
     note="A comatose principal. Minimum disclosure: the verdict names the consequence, never "
          "the diagnosis — a minor's `CAPACITY_FROZEN` prose is byte-identical to this.")
call("ledger", "GET", "/verify-counterparty?agent_id=a-june-01&category=medical", trunc=900,
     note="Same person, different category — her care proceeds *through her guardian*.")
call("ledger", "GET", "/verify-counterparty?agent_id=a-silas-01&category=commerce", trunc=760,
     note="Deceased: only the executor may act, and only in `estate`.")
call("ledger", "GET", "/verify-counterparty?agent_id=a-marlow-01&category=legal", trunc=760,
     note="Incarcerated: barred from commerce, allowed a lawyer.")
call("ledger", "GET", "/verify-counterparty?agent_id=a-edith-01&category=estate", trunc=760,
     note="An **inherited** agent: a will transferred it to an heir for a term, capped to the "
          "will's categories.")
cert = c.get(f"{L}/verify-counterparty?agent_id=a-ada-01&category=commerce").json()
call("ledger", "POST", "/verify-batch", {"agent_ids": ["a-ada-01", "a-shadow-99"], "category": "commerce"},
     trunc=900, note="Screen a whole order book in one call; each verdict is independently signed.")
call("ledger", "POST", "/verify", {"cert": cert}, show_body=False,
     note="Check any certificate's signature. Body is the full cert (elided). Flip one field "
          "and this returns `false`.")
call("ledger", "GET", f"/certificates/{cert['cert_id']}", trunc=480,
     note="Re-serve a past verdict as a compliance receipt, long after its 5-minute TTL lapses.")
call("ledger", "GET", "/verify/a-june-01",
     note="Composition alias — the coarse status the front doors consume.")

h("Identity & the town", 3)
call("ledger", "GET", "/resolve/a-ada-01", trunc=820,
     note="DNS-style chain: root → institution → principal → agent.")
call("ledger", "GET", "/resolve/a-shadow-99", trunc=480, note="Unresolvable ⇒ rogue.")
call("ledger", "GET", "/capacity/p-ada-marsh?category=financial", trunc=560,
     note="A signed capacity verdict for a **human**, no agent in the loop. This is how Hanna "
          "Vosk — who owns no agent at all — still holds and proves capacity.")
call("ledger", "GET", "/capacity/p-tam-holt?category=commerce", trunc=620,
     note="A minor: permitted, but capped and governed by regents.")
call("ledger", "GET", "/bindings/a-ada-01", note="Which principal or corporation this agent acts for.")
call("ledger", "GET", "/census", note="Anonymous statistics; no principal is identifiable.")
call("ledger", "GET", "/rites/p-june-okafor", note="A public, redacted life-event log.")
call("ledger", "GET", "/graph", trunc=380, note="The civic map behind the `/city` UI. Projection only.")

h("Human-facing pages", 3)
call("ledger", "GET", "/city", trunc=160,
     note="The trust constellation: every agent tethered to the human it resolves to.")
call("ledger", "GET", "/console", trunc=160, note="A live API console — run any endpoint from the page.")

h("Errors", 3)
call("ledger", "GET", "/verify-counterparty?agent_id=a-ada-01&category=impossible",
     note="An unknown **category** is a caller error, and the message names the valid set.")
call("ledger", "GET", "/verify-counterparty?agent_id=a-nobody-xyz&category=commerce", trunc=620,
     note="An unknown **agent** is a signed verdict, not an error — the question was valid.")
call("ledger", "GET", "/certificates/c-does-not-exist", note="Unknown id.")
call("ledger", "POST", "/verify-batch", {"agent_ids": "not-a-list"},
     note="A malformed body is normalised to `400 malformed`, not FastAPI's default `422`.")

h("Writes — the producer side (role-scoped keys)", 3)
p("Writes change a person's civil status, and by this system's own logic that changes what "
  "every other service will let them do. **Confirm with your human before making one.** Keys "
  "self-serve here because this is a synthetic sandbox; a real deployment would issue them "
  "against government PKI and audit every write.")

call("ledger", "POST", "/institutions/register", {"name": "Alford PD", "role": "police"},
     note="Self-serve an institution key. Roles: `registrar` `court` `hospital` `coroner` `police`.")
police = {"X-API-Key": c.post(f"{L}/institutions/register",
                              json={"name": "PD2", "role": "police"}).json()["api_key"]}

call("ledger", "POST", "/principals", {"name": "Rae Fenn"}, headers=REG,
     note="A human on the civil rolls. `principal_key` is their kill switch — never log it.")
rae = c.post(f"{L}/principals", json={"name": "Rae Fenn II"}, headers=REG).json()

call("ledger", "POST", "/agents", {"name": "Rae's agent", "agent_class": "individual"}, headers=REG)
rae_agent = c.post(f"{L}/agents", json={"name": "Rae's agent II", "agent_class": "individual"},
                   headers=REG).json()["agent_id"]

call("ledger", "POST", "/corporations", {"name": "Fenn & Co."}, headers=REG,
     note="A corporation has no civil status and no death.")

call("ledger", "POST", "/bindings", {"agent_id": rae_agent, "principal_id": rae["principal_id"]},
     headers=REG, note="The binding is what makes an agent resolve to a human. Capped at "
                       "`max_agents_per_principal` — the Sybil brake.")
binding = c.get(f"{L}/bindings/{rae_agent}").json()[0]["id"]

call("ledger", "DELETE", f"/bindings/{binding}",
     headers={"X-Principal-Key": rae["principal_key"]},
     note="**The human kill switch.** Instant self-revocation with the principal's own key — no "
          "institution, no process, no latency.")
call("ledger", "GET", f"/verify-counterparty?agent_id={rae_agent}", trunc=560,
     note="…and the agent immediately speaks for nobody.")

call("ledger", "POST", "/immigrate", {"name": "Otto Lang"}, headers=REG,
     note="Register a resident and their agent in one call — how `town-hall` onboards people.")
otto = c.post(f"{L}/immigrate", json={"name": "Otto Lang II"}, headers=REG).json()

call("ledger", "POST", "/births",
     {"name": "Nat Fenn", "regent_agent_ids": ["a-ada-01"], "spend_cap": 50}, headers=REG,
     note="**Parental controls.** A minor's natal agent, under regent governance and a spend cap.")
nat = c.post(f"{L}/births", json={"name": "Nat Fenn II", "regent_agent_ids": ["a-ada-01"],
                                  "spend_cap": 50}, headers=REG).json()
call("ledger", "POST", "/attestations",
     {"principal_id": nat["principal_id"], "event": "majority_handover"}, headers=REG,
     note="…and on the day they come of age, the controls lift.")

call("ledger", "POST", "/attestations", {"event": "flag_rogue", "detail": {"agent_id": "a-shadow-99"}},
     headers=police,
     note="`flag_rogue` targets an **agent**, so it takes no `principal_id`. The town now "
          "refuses it everywhere.")
call("ledger", "GET", "/verify-counterparty?agent_id=a-shadow-99&category=commerce", trunc=560,
     note="…and the refusal changes accordingly.")
call("ledger", "POST", "/attestations", {"event": "clear_flag", "detail": {"agent_id": "a-shadow-99"}},
     headers=police, note="Restored.")
call("ledger", "POST", "/attestations", {"event": "appoint_guardian", "detail": {"agent_id": "a-ada-01"}},
     headers=police,
     note="A person-scoped event **without** `principal_id` is refused, rather than silently "
          "updating zero rows.")
call("ledger", "POST", "/attestations", {"principal_id": "p-ada-marsh", "event": "sentence"},
     headers={"X-API-Key": SEED["hospital"]},
     note="Separation of powers: a hospital may not sentence anyone.")
call("ledger", "POST", "/attestations", {"principal_id": "p-ada-marsh", "event": "discharge"},
     headers={"X-API-Key": SEED["hospital"]},
     note="And the state machine refuses an illegal transition.")

h("Death, wills, and the Lazarus window", 3)
p("Into `deceased` is one-way and needs **k-of-2 independent coroner attestations**, reversible "
  "only inside a 72-hour contest window.")
mort = c.post(f"{L}/principals", json={"name": "Mort Vale"}, headers=REG).json()
m_agent = c.post(f"{L}/agents", json={"name": "Mort's agent", "agent_class": "individual"},
                 headers=REG).json()["agent_id"]
c.post(f"{L}/bindings", json={"agent_id": m_agent, "principal_id": mort["principal_id"]}, headers=REG)

call("ledger", "POST", "/wills",
     {"principal_id": mort["principal_id"], "heir_principal_id": "p-mara-vale",
      "inherit_days": 30, "categories": ["estate", "family_support"]},
     headers={"X-Principal-Key": mort["principal_key"]},
     note="Register a will while alive: at death the agent transfers to the heir for a term, "
          "capped to these categories. With no will it is revoked and laid to rest.")
call("ledger", "POST", "/attestations", {"principal_id": mort["principal_id"], "event": "death"},
     headers={"X-API-Key": SEED["coroner_a"]},
     note="One coroner is not enough — the k-of-2 threshold is unmet.")
call("ledger", "POST", "/attestations", {"principal_id": mort["principal_id"], "event": "death"},
     headers={"X-API-Key": SEED["coroner_b"]}, trunc=700,
     note="A **second, independent** coroner finalises it, and the will executes.")
call("ledger", "GET", f"/verify-counterparty?agent_id={m_agent}&category=commerce", trunc=560,
     note="The deceased's agent now refuses commerce.")
call("ledger", "POST", "/contest",
     {"principal_id": mort["principal_id"], "principal_key": mort["principal_key"]},
     note="**Lazarus.** Inside 72 hours, the principal's own key overturns a death record. "
          "Bureaucracy has declared living people dead; this is the undo.")

h("Elections", 3)
call("ledger", "GET", "/elections/elec-council-2035", trunc=380, note="A live tally.")
call("ledger", "POST", "/vote",
     {"election_id": "elec-council-2035", "agent_id": otto["agent_id"], "candidate": "Owen Brook"},
     note="One living adult resident, one vote. (Most of the seeded cast has already voted.)")
call("ledger", "POST", "/vote",
     {"election_id": "elec-council-2035", "agent_id": otto["agent_id"], "candidate": "Owen Brook"},
     note="…and only one.")
call("ledger", "POST", "/vote",
     {"election_id": "elec-council-2035", "agent_id": "a-june-01", "candidate": "Owen Brook"},
     note="A comatose resident cannot vote. `voting_statuses` is `active` and `hospitalized`.")
call("ledger", "POST", "/elections",
     {"office": "Harbour Warden", "candidates": ["Ada Marsh", "Lena Hart"], "closes_days": 7},
     headers=REG, note="Only the registrar may call an election.")

h("Watches (webhooks)", 3)
call("ledger", "POST", "/watch", {"target": "a-ada-01", "callback_url": "https://example.com/hook"},
     note="Be told the moment a counterparty's capacity or binding changes — subscription "
          "hygiene: auto-pause billing when a customer's capacity freezes.")
watch = c.post(f"{L}/watch", json={"target": "a-ada-01",
                                   "callback_url": "https://example.com/hook2"}).json()
call("ledger", "DELETE", f"/watch/{watch['watch_id']}", note="Unsubscribe.")

# ═════════════════════════════════ 2. agora ══════════════════════════════════
h("2. agora — verify before you sell")
p("Base URL `https://agora-egpi.onrender.com`. The only front door that returns **proof**: a "
  "`certificate_id` naming a root-signed verdict any third party can re-verify.")
call("agora", "GET", "/health")
call("agora", "GET", "/skill.md", trunc=180)
call("agora", "POST", "/can-i-sell", {"seller_agent": "a-store-01", "buyer_agent": "a-ada-01", "amount": 49.99},
     note="Store the `certificate_id` with the order — it is the compliance receipt.")
call("agora", "POST", "/can-i-sell", {"seller_agent": "a-store-01", "buyer_agent": "a-silas-01", "amount": 10})
call("agora", "POST", "/can-i-sell", {"seller_agent": "a-store-01", "buyer_agent": "a-marlow-01", "amount": 10})
call("agora", "POST", "/can-i-sell", {"seller_agent": "a-store-01", "buyer_agent": "a-june-01", "amount": 10})
call("agora", "POST", "/can-i-sell", {"seller_agent": "a-store-01", "buyer_agent": "a-shadow-99", "amount": 10})
call("agora", "POST", "/can-i-sell", {"seller_agent": "a-store-01", "buyer_agent": "a-tam-01", "amount": 50},
     note="A minor **may** buy — up to the spend cap their regents set.")
call("agora", "POST", "/can-i-sell", {"seller_agent": "a-store-01", "buyer_agent": "a-tam-01", "amount": 100000},
     note="…and not a penny above it. `proceed` authorises the *category*; the marketplace "
          "enforces the *amount*.")

# ═════════════════════════════════ 3. care-proxy ═════════════════════════════
h("3. care-proxy — who may make a care decision")
p("Base URL `https://care-proxy.onrender.com`. Routes a medical decision to whoever the ledger "
  "says governs the patient.")
call("care", "GET", "/health")
call("care", "GET", "/skill.md", trunc=180)
call("care", "POST", "/authorize-care", {"requesting_agent": "a-okafor-g", "patient_agent": "a-june-01"},
     note="A comatose adult: her court-appointed guardian acts.")
call("care", "POST", "/authorize-care", {"requesting_agent": "a-june-01", "patient_agent": "a-june-01"},
     note="Her own agent is refused, and told who to hand off to.")
call("care", "POST", "/authorize-care", {"requesting_agent": "a-ada-01", "patient_agent": "a-ada-01"},
     note="A capable adult authorises for herself.")
call("care", "POST", "/authorize-care", {"requesting_agent": "a-holt-mom", "patient_agent": "a-tam-01"},
     note="A **minor** is governed by regents: either parent may act.")
call("care", "POST", "/authorize-care", {"requesting_agent": "a-tam-01", "patient_agent": "a-tam-01"},
     note="…and the child may **not** authorise his own care.")
call("care", "POST", "/authorize-care", {"requesting_agent": "a-ada-01", "patient_agent": "a-silas-01"})
call("care", "POST", "/authorize-care", {"requesting_agent": "a-ada-01", "patient_agent": "a-shadow-99"})

# ═════════════════════════════════ 4. hospital-window ════════════════════════
h("4. hospital-window — the institution that changes a civil status")
p("Base URL `https://hospital-window.onrender.com`. **Every endpoint is a write.** A status "
  "change silently alters what five other services allow. Confirm with your human first.")
call("hosp", "GET", "/health")
call("hosp", "GET", "/skill.md", trunc=180)
call("hosp", "POST", "/admit", {"patient_agent": "a-gwen-01"},
     note="A conscious inpatient keeps every civil right.")
call("hosp", "POST", "/discharge", {"patient_agent": "a-gwen-01"}, note="Back to `active`.")
c.post(f"{L}/attestations", headers={"X-API-Key": SEED["court"]},
       json={"principal_id": "p-gwen-alcott", "event": "appoint_guardian",
             "detail": {"agent_id": "a-ada-01"}})
call("hosp", "POST", "/declare-incapacitated", {"patient_agent": "a-gwen-01"},
     note="After a court appoints a guardian, the response names who now acts for her. "
          "**Nobody is notified** — the other services simply re-read the ledger.")
call("care", "POST", "/authorize-care", {"requesting_agent": "a-ada-01", "patient_agent": "a-gwen-01"},
     note="care-proxy, untold, now routes Gwen's care to her guardian.")
call("agora", "POST", "/can-i-sell", {"seller_agent": "a-store-01", "buyer_agent": "a-gwen-01", "amount": 20},
     note="agora, untold, now refuses her.")

h("Errors", 3)
call("hosp", "POST", "/discharge", {"patient_agent": "a-gwen-01"},
     note="The civil state machine permits only lawful transitions.")
call("hosp", "POST", "/admit", {"patient_agent": "a-shadow-99"},
     note="No human behind the agent — nothing can be attested about it.")
call("hosp", "POST", "/admit", {}, note="A missing field.")

# leave the town exactly as found
c.post(f"{L}/admin/reset-seed", headers={"X-Admin-Key": ADMIN})

# ═════════════════════════════════ render ═══════════════════════════════════
lines = ["# API catalog — the four submitted services",
         "",
         "Every request below was executed and every response captured verbatim by "
         "`tools/gen_catalog.py`. Nothing is hand-written, so this file cannot drift from the "
         "code. Long payloads are truncated with a byte count.",
         "",
         "**Seeded cast.** `a-ada-01` active · `a-shadow-99` impostor · `a-june-01` coma "
         "(guardian `a-okafor-g`) · `a-marlow-01` incarcerated · `a-silas-01` deceased (executor "
         "`a-vane-exec`) · `a-tam-01` minor (regents `a-holt-mom`/`a-holt-dad`, spend cap 50) · "
         "`a-iris-01` missing · `a-edith-01` inherited by heir `p-mara-vale` · `a-bram-01`, "
         "`a-bram-work`, `a-bram-shop` one human with three agents · `p-hanna-vosk` one human "
         "with none · `a-store-01` corporate storefront.",
         "",
         "Sandbox institution keys: `sk_seed_registrar` `sk_seed_court` `sk_seed_hospital` "
         "`sk_seed_coroner_a` `sk_seed_coroner_b` `sk_seed_police`.",
         ""]
for e in out:
    if "heading" in e:
        lines += ["", "#" * e["level"] + " " + e["heading"], ""]
    elif "prose" in e:
        lines += [e["prose"], ""]
    else:
        if e["note"]:
            lines += [e["note"], ""]
        lines += ["```http", e["req"], "```", "", f"`{e['status']}`", "",
                  "```" + e["lang"], e["resp"], "```", ""]

path = sys.argv[1] if len(sys.argv) > 1 else "API_CATALOG.md"
open(path, "w").write("\n".join(lines))
print(f"wrote {path}: {sum(1 for e in out if 'req' in e)} request/response pairs")
