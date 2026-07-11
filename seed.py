"""
Seed the town of ALFORD, MASSACHUSETTS — a real Berkshire County town (pop. ~400) —
as a synthetic demography of agent-represented residents.

Includes the five constitutional institutions, a representative sample of 13 residents
spanning every civil status (active, minor, hospitalized, incapacitated, incarcerated,
missing, deceased) and a range of ages (born 1945-2012), a corporate storefront, a rogue impostor,
one INHERITED agent (a will executed at death, stewarded by an heir), and an open
City Council election with votes already cast.

Canonical demo IDs (used by SKILL.md and the tests) are preserved. Idempotent.
"""
import json
from app import db, now_iso, ts, DEFAULT_INHERIT_DAYS

INST = {
    "registrar": ("inst-registrar", "Alford Bureau of Vital Records", "sk_seed_registrar"),
    "court":     ("inst-court",     "Alford Town Court",              "sk_seed_court"),
    "hospital":  ("inst-hospital",  "Fairview Hospital",              "sk_seed_hospital"),
    "coroner":   ("inst-coroner-a", "Berkshire Coroner A",            "sk_seed_coroner_a"),
    "police":    ("inst-police",    "Alford Police",                  "sk_seed_police"),
    "insurance": ("inst-insurance", "Alford Mutual Insurance",        "sk_seed_insurance"),
}
CORONER_B = ("inst-coroner-b", "Berkshire Coroner B", "sk_seed_coroner_b", "coroner")


def _has(c, table, _id):
    return c.execute(f"SELECT 1 FROM {table} WHERE id=?", (_id,)).fetchone() is not None


def seed_town():
    with db() as c:
        if _has(c, "institutions", "inst-registrar"):
            return

        for role, (iid, name, key) in INST.items():
            c.execute("INSERT INTO institutions VALUES (?,?,?,?,?)", (iid, name, role, key, now_iso()))
        c.execute("INSERT INTO institutions VALUES (?,?,?,?,?)",
                  (CORONER_B[0], CORONER_B[1], CORONER_B[3], CORONER_B[2], now_iso()))

        def P(pid, name, status, by=None, **kw):
            c.execute(
                "INSERT INTO principals (id,name,status,kind,guardian_agent,executor_agent,"
                "regents,principal_key,acl_override,spend_cap,death_ts,will,birth_year,created) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (pid, name, status, "human", kw.get("guardian"), kw.get("executor"),
                 json.dumps(kw["regents"]) if kw.get("regents") else None,
                 f"pk_seed_{pid}", kw.get("acl"), kw.get("cap"), kw.get("death_ts"),
                 json.dumps(kw["will"]) if kw.get("will") else None, by, now_iso()))

        def A(aid, name, cls="individual", rogue=0):
            c.execute("INSERT INTO agents (id,name,class,rogue,created) VALUES (?,?,?,?,?)",
                      (aid, name, cls, rogue, now_iso()))

        def B(bid, aid, pid=None, corp=None, scope="full", inherit_until=None, inherit_acl=None):
            c.execute("INSERT INTO bindings (id,agent_id,principal_id,corporation_id,scope,status,"
                      "issued_by,inherit_until,inherit_acl,created) VALUES (?,?,?,?,?,?,?,?,?,?)",
                      (bid, aid, pid, corp, scope, "active", "inst-registrar",
                       inherit_until, inherit_acl, now_iso()))

        # ---- canonical demo citizens (referenced by SKILL.md + tests) ----
        P("p-ada-marsh", "Ada Marsh", "active", 1979)
        A("a-ada-01", "Ada's agent"); B("b-ada", "a-ada-01", "p-ada-marsh")

        P("p-silas-crane", "Silas Crane", "deceased", 1948,
          executor="a-vane-exec", death_ts=ts() - 10 * 24 * 3600)  # no will: agent softlinked to the dead
        A("a-silas-01", "Silas's agent"); B("b-silas", "a-silas-01", "p-silas-crane")
        A("a-vane-exec", "Vane (executor)"); B("b-vane", "a-vane-exec", "p-silas-crane", scope="estate")

        P("p-june-okafor", "June Okafor", "incapacitated", 1966, guardian="a-okafor-g")
        A("a-june-01", "June's agent"); B("b-june", "a-june-01", "p-june-okafor")
        A("a-okafor-g", "Okafor guardian"); B("b-okaforg", "a-okafor-g", "p-june-okafor", scope="medical")

        P("p-marlow-reyes", "Marlow Reyes", "incarcerated", 1990,
          acl=json.dumps(["legal", "family_support"]))
        A("a-marlow-01", "Marlow's agent"); B("b-marlow", "a-marlow-01", "p-marlow-reyes")

        P("p-tam-holt", "Tam Holt", "minor", 2012, regents=["a-holt-mom", "a-holt-dad"], cap=50.0)
        A("a-tam-01", "Tam's agent"); B("b-tam", "a-tam-01", "p-tam-holt", scope="minor")

        P("p-iris-vane", "Iris Vane", "missing", 1985)
        A("a-iris-01", "Iris's agent"); B("b-iris", "a-iris-01", "p-iris-vane")

        # ---- INHERITED agent: Edith Vale died WITH a will; her agent now serves heir Mara ----
        P("p-mara-vale", "Mara Vale", "active", 1988)
        A("a-mara-01", "Mara's agent"); B("b-mara", "a-mara-01", "p-mara-vale")
        P("p-edith-vale", "Edith Vale", "deceased", 1945,
          death_ts=ts() - 2 * 24 * 3600,
          will={"heir_principal_id": "p-mara-vale", "inherit_days": DEFAULT_INHERIT_DAYS,
                "categories": ["estate", "family_support"]})
        A("a-edith-01", "Edith's agent")
        B("b-edith", "a-edith-01", "p-mara-vale", scope="inherited",
          inherit_until=ts() + DEFAULT_INHERIT_DAYS * 86400,
          inherit_acl=json.dumps(["estate", "family_support"]))

        # ---- more Alford residents (demography spread) ----
        P("p-owen-brook", "Owen Brook", "active", 1972)
        A("a-owen-01", "Owen's agent"); B("b-owen", "a-owen-01", "p-owen-brook")
        P("p-lena-hart", "Lena Hart", "active", 1995)
        A("a-lena-01", "Lena's agent"); B("b-lena", "a-lena-01", "p-lena-hart")
        P("p-nora-blau", "Nora Blau", "active", 1951)
        A("a-nora-01", "Nora's agent"); B("b-nora", "a-nora-01", "p-nora-blau")
        P("p-cyrus-ford", "Cyrus Ford", "hospitalized", 1960)  # conscious inpatient: keeps rights + vote
        A("a-cyrus-01", "Cyrus's agent"); B("b-cyrus", "a-cyrus-01", "p-cyrus-ford")
        P("p-gwen-alcott", "Gwen Alcott", "active", 2003)
        A("a-gwen-01", "Gwen's agent"); B("b-gwen", "a-gwen-01", "p-gwen-alcott")

        # ---- ONE HUMAN, MANY AGENTS: agents are tools, not identities ----
        # Bram runs three specialised agents. All three resolve to the SAME principal, so all
        # three inherit his civil status the instant it changes — and revoking one leaves the
        # others untouched. This is why the ledger binds agents to a person, not the reverse.
        P("p-bram-kessler", "Bram Kessler", "active", 1983)
        A("a-bram-01", "Bram's personal agent"); B("b-bram-1", "a-bram-01", "p-bram-kessler")
        A("a-bram-work", "Bram's work agent"); B("b-bram-2", "a-bram-work", "p-bram-kessler")
        A("a-bram-shop", "Bram's shopping agent"); B("b-bram-3", "a-bram-shop", "p-bram-kessler")

        # ---- ONE HUMAN, NO AGENT: the right to abstain ----
        # Hanna declines to be represented by any agent. She is a full citizen — she votes, she
        # holds capacity — she simply has no digital twin. The ledger records the ABSENCE, which
        # is what makes an impostor provable: any agent claiming to be Hanna is, by construction,
        # bound to nobody. Personhood does not require an agent.
        P("p-hanna-vosk", "Hanna Vosk", "active", 1958)
        A("a-vosk-99", "'Hanna's assistant' (unbound impostor)")   # no binding: claims a woman who owns no agent

        # ---- a corporate storefront + a rogue ----
        c.execute("INSERT INTO corporations VALUES (?,?,?)",
                  ("corp-marshco", "Marsh & Co. General Store", now_iso()))
        A("a-store-01", "Marsh & Co. storefront agent", cls="corporate")
        B("b-store", "a-store-01", corp="corp-marshco")
        A("a-shadow-99", "Shadow (unbound impostor)")   # no binding: rogue

        # ---- an open City Council election, with votes already cast ----
        candidates = ["Ada Marsh", "Owen Brook", "Lena Hart"]
        c.execute("INSERT INTO elections VALUES (?,?,?,?,?)",
                  ("elec-council-2035", "Alford City Council", json.dumps(candidates),
                   ts() + 7 * 86400, now_iso()))
        cast = [("p-ada-marsh", "Owen Brook"), ("p-owen-brook", "Owen Brook"),
                ("p-lena-hart", "Lena Hart"), ("p-nora-blau", "Ada Marsh"),
                ("p-mara-vale", "Lena Hart"), ("p-cyrus-ford", "Owen Brook"),
                ("p-gwen-alcott", "Ada Marsh")]
        for i, (pid, cand) in enumerate(cast):
            c.execute("INSERT INTO votes VALUES (?,?,?,?,?)",
                      (f"v-seed-{i}", "elec-council-2035", pid, cand, now_iso()))

        # birth events for the rites log
        for pid in ("p-ada-marsh", "p-silas-crane", "p-june-okafor", "p-marlow-reyes",
                    "p-tam-holt", "p-iris-vane", "p-edith-vale", "p-mara-vale"):
            c.execute("INSERT INTO attestations (id,principal_id,event,role,institution_id,detail,created,ts) "
                      "VALUES (?,?,?,?,?,?,?,?)",
                      (f"att-birth-{pid}", pid, "birth", "registrar", "inst-registrar", "{}", now_iso(), ts()))

        # Alford Mutual Insurance confirms coverage for a few living residents (a civic fact
        # orthogonal to civil status; readable via /graph and /rites).
        for pid in ("p-ada-marsh", "p-bram-kessler", "p-cyrus-ford", "p-owen-brook"):
            c.execute("UPDATE principals SET covered=1 WHERE id=?", (pid,))
            c.execute("INSERT INTO attestations (id,principal_id,event,role,institution_id,detail,created,ts) "
                      "VALUES (?,?,?,?,?,?,?,?)",
                      (f"att-cover-{pid}", pid, "confirm_coverage", "insurance", "inst-insurance",
                       "{}", now_iso(), ts()))


if __name__ == "__main__":
    from app import init_db
    init_db(); seed_town(); print("seeded Alford, MA")
