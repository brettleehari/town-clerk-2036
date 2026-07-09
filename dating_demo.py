#!/usr/bin/env python3
"""
dating_demo — "verify before you MEET."

Two people have been chatting through their agents: messages, a few photos, a
spark. Now one agent proposes a real-world date. Before either human is put in a
room with a stranger, BOTH agents ask the Civil Ledger one question on the new
`social` category: "is there a real, living, consenting adult behind you?"

They learn the answer — and NOTHING else. No birthday, no address, no medical
history. Minimum disclosure: the consequence, never the private reason.

Run:  python3 dating_demo.py            (defaults to http://127.0.0.1:8000)
"""
import json, sys, time, urllib.request, urllib.error

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
C = dict(dim="\033[2m", b="\033[1m", g="\033[32m", r="\033[31m", y="\033[33m",
         cy="\033[36m", mag="\033[35m", blu="\033[34m", pink="\033[95m", x="\033[0m")

def rule(t): print(f"\n{C['b']}{'─'*68}\n {t}\n{'─'*68}{C['x']}")
def chat(who,msg,col): print(f"  {col}{C['b']}{who}{C['x']}  {C['dim']}“{msg}”{C['x']}")
def act(who,msg,col): print(f"  {col}{C['b']}{who}’s agent{C['x']}  {msg}")
def ok(t):  print(f"    {C['g']}{C['b']}✅ PROCEED{C['x']} {t}")
def no(t,code): print(f"    {C['r']}{C['b']}⛔ REFUSE{C['x']} {C['dim']}[{code}]{C['x']} {t}")

def req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE+path, data=data, method=method,
        headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(r, timeout=10) as resp: return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read())
        except Exception: return e.code, {}
def V(agent):
    _, d = req("GET", f"/verify-counterparty?agent_id={agent}&category=social"); return d
def beat(): time.sleep(.4)

print(f"{C['pink']}{C['b']}\n   ♥  V E R I F Y   B E F O R E   Y O U   M E E T{C['x']}")
print(f"{C['dim']}   the Civil Ledger · the `social` category · {BASE}{C['x']}")

# ---------------------------------------------------------------------------
rule("The prelude · three days of chatting")
print(f"{C['dim']}  Ada and Mara matched. Their agents have traded 40 messages and a few")
print(f"  photos. It's going well. Mara's agent proposes the next step:{C['x']}")
chat("Mara","coffee Saturday? there's a place on Elm I love", C['blu'])
chat("Ada","yes! but… you could be anyone behind that screen 😅", C['mag'])
print(f"{C['dim']}  Right instinct. Before a real-world meeting, each agent runs the same")
print(f"  check on the OTHER — a bilateral handshake. A date happens only if BOTH")
print(f"  humans verify as real, living, consenting adults.{C['x']}")

# ---------------------------------------------------------------------------
rule("Act I · Two adults verify each other")
pairs = [("Ada","a-ada-01",C['mag']), ("Mara","a-mara-01",C['blu'])]
verdicts = {}
for name, aid, col in pairs:
    other = [p for p in pairs if p[0]!=name][0]
    act(name, f"asks the ledger about {other[2]}{other[0]}{C['x']}{C['dim']} before agreeing to meet…{C['x']}", col)
    d = V(other[1]); verdicts[other[0]] = d; beat()
    if d.get("proceed"): ok(f"{other[0]} is a verifiable adult. Safe to meet.")
    else: no(f"{other[0]} did not verify.", d.get("reason_code"))
both = all(verdicts[n].get("proceed") for n,_,_ in pairs)
print()
if both:
    print(f"  {C['g']}{C['b']}❤ It's a date.{C['x']} Both sides cleared — Saturday, coffee on Elm.")
# minimum disclosure proof
d = verdicts["Mara"]
print(f"  {C['dim']}What Ada's agent learned about Mara: proceed={d.get('proceed')}, "
      f"class={d.get('agent_class')}.{C['x']}")
leaked = [k for k in ("birth_year","status_class","address","dob","name") if k in d]
print(f"  {C['dim']}Private details leaked: {C['x']}{C['g']}{leaked or 'NONE'}{C['x']}  "
      f"{C['dim']}— she knows Mara is real & adult, not her birthday.{C['x']}")
# a signed safety receipt to text a friend
_, ver = req("POST","/verify",{"cert":d})
print(f"  {C['dim']}Safety receipt {d.get('cert_id')} — signed by the city root, /verify → "
      f"{C['x']}{C['g']}{C['b']}{ver.get('valid')}{C['x']}{C['dim']}. Text it to a friend before you go.{C['x']}")

# ---------------------------------------------------------------------------
rule("Act II · The guardrail that matters most")
print(f"{C['dim']}  Different match. A charming profile wants to meet an adult. Behind the")
print(f"  agent is Tam — 14 years old. Watch the town refuse it, automatically:{C['x']}")
act("an adult", f"verifies the match {C['cy']}a-tam-01{C['x']} on `social`…", C['mag']); beat()
d = V("a-tam-01")
no("this agent's human is a MINOR. An adult meeting cannot be arranged.", d.get("reason_code"))
print(f"  {C['g']}{C['b']}→ An adult was just stopped from being catfished into meeting a minor —{C['x']}")
print(f"  {C['dim']}   and no one had to reveal a birthday to prove it. The age-gate is law.{C['x']}")

# ---------------------------------------------------------------------------
rule("Act III · The catfish & the con from a cell")
act("Ada", f"vets a too-good-to-be-true match {C['cy']}a-shadow-99{C['x']}…", C['mag']); beat()
d = V("a-shadow-99")
no("resolves to NO human. A catfish. There is nobody real behind it.", d.get("reason_code"))
act("Ada", f"vets another eager suitor {C['cy']}a-marlow-01{C['x']}…", C['mag']); beat()
d = V("a-marlow-01")
no("the human behind it is incarcerated — barred from `social`.", d.get("reason_code"))
print(f"  {C['dim']}   A prisoner with a contraband phone can't run a romance scam here.{C['x']}")

rule("Epilogue")
print(f"{C['dim']}  After the messages and the photos, one question remained: is there a real,")
print(f"  accountable adult behind this? The ledger answered it for both sides at once —")
print(f"  proving realness and adulthood while revealing nothing private, and refusing the")
print(f"  minor, the catfish, and the con from a cell. No human was in the loop.{C['x']}")
print(f"  {C['pink']}{C['b']}Verify the human behind the agent — before you meet them.{C['x']}\n")
