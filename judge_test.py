#!/usr/bin/env python3
"""
judge_test.py — an agent completes a real task using ONLY skill.md.

Every call below is documented in SKILL.md; nothing here reads the source. Read-only:
the town is left exactly as it was found.

    python3 judge_test.py                                  # against the live deployment
    BASE=http://localhost:8000 python3 judge_test.py       # against a local ledger
"""
import base64
import json
import os
import ssl
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("BASE", "https://civil-ledger.onrender.com").rstrip("/")
BAR = "═" * 58


def _ssl_context():
    """python.org's macOS build ships no CA bundle, so urllib cannot verify Render's cert
    while curl can. Fall back to certifi's roots rather than disabling verification —
    a script that teaches signature checking must not skip TLS checking."""
    ctx = ssl.create_default_context()
    if not ctx.get_ca_certs():
        try:
            import certifi
            ctx.load_verify_locations(certifi.where())
        except ImportError:
            print("warning: no CA bundle found. Run: pip install certifi", file=sys.stderr)
    return ctx


CTX = _ssl_context()


def step(title):
    print(f"\n{BAR}\n{title}\n{BAR}")


def get(path):
    """Returns (status, parsed_json). A 4xx is data here, not an exception — the point of
    step F is that the service says *why* it refused."""
    req = urllib.request.Request(BASE + path)
    try:
        with urllib.request.urlopen(req, timeout=90, context=CTX) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)


def verify_offline(cert, pubkey_b64):
    """The recipe straight out of SKILL.md: drop `signature`, canonicalize with sorted keys
    and compact separators, verify Ed25519 against /pubkey."""
    from nacl.signing import VerifyKey
    body = {k: v for k, v in cert.items() if k != "signature"}
    msg = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    VerifyKey(base64.b64decode(pubkey_b64)).verify(msg, base64.b64decode(cert["signature"]))
    return True


failures = []


def expect(label, cond):
    print(f"  {'✓' if cond else '✗'} {label}")
    if not cond:
        failures.append(label)


print(f"KYA judge test · agent uses only skill.md · base: {BASE}")

# ---------------------------------------------------------------- A. read the law
step("Step A. Agent reads /constitution — the law, as signed data")
_, law = get("/constitution")
cats = law["transaction_categories"]
statuses = sorted(law["status_acl"])
print(f"Found {len(cats)} transaction categories · {len(statuses)} civil statuses")
print(f"Categories: {', '.join(cats)}")
print(f"Statuses:   {', '.join(statuses)}")
_, pub = get("/pubkey")
expect("the constitution is signed by the root key", verify_offline(law, pub["pubkey_b64"]))

# ---------------------------------------------- B. the decision the service exists for
step('Step B. "A customer wants to buy. May I sell to them?"')
_, v = get("/verify-counterparty?agent_id=a-ada-01&category=commerce")
print(f"Verdict for a-ada-01: proceed={v['proceed']} · {v['reason_code']}")
print(f"Why:  {v['summary']}")
print(f"Next: {v['next_step']}")
print(f"Certificate {v['cert_id']} valid until {v['valid_until']}")
expect("an active adult may transact in commerce", v["proceed"] is True)

# ------------------------------------------------------ C. the receipt is verifiable
step("Step C. Agent verifies the verdict itself, offline")
expect("signature verifies against /pubkey", verify_offline(v, pub["pubkey_b64"]))
tampered = dict(v)
tampered["proceed"] = False
try:
    verify_offline(tampered, pub["pubkey_b64"])
    expect("a tampered certificate is rejected", False)
except Exception:
    expect("a tampered certificate is rejected", True)
print("The verdict is proof, not a promise: the seller cannot forge it, and neither can we.")

# ------------------------------------------------------------- D. the impostor
step("Step D. Next in line: an agent that represents nobody")
_, imp = get("/verify-counterparty?agent_id=a-shadow-99&category=commerce")
print(f"Verdict for a-shadow-99: proceed={imp['proceed']} · {imp['reason_code']}")
print(f"Why:  {imp['summary']}")
print(f"Next: {imp['next_step']}")
expect("the impostor is refused", imp["proceed"] is False and imp["reason_code"] == "NO_VALID_BINDING")

# ------------------------------------------------- E. the rule nobody else expresses
step("Step E. A comatose customer — the money is protected, the care is routed")
_, money = get("/verify-counterparty?agent_id=a-june-01&category=commerce")
_, care = get("/verify-counterparty?agent_id=a-june-01&category=medical")
print(f"commerce: proceed={money['proceed']} · {money['reason_code']}")
print(f"  {money['summary']}")
print(f"  {money['next_step']}")
print(f"medical:  proceed={care['proceed']} · {care['reason_code']}")
print(f"  {care['summary']}")
expect("her money is frozen", money["reason_code"] == "CAPACITY_FROZEN")
expect("her care routes to the appointed guardian",
       care["governed_by"]["role"] == "guardian" and care["governed_by"]["agent"] == "a-okafor-g")
expect("the prose never names the private reason",
       not any(w in (money["summary"] + money["next_step"]).lower()
               for w in ("coma", "comatose", "incapacitated")))
print("Minimum disclosure: the verdict names the consequence, never the diagnosis.")

# --------------------------------------------------------- F. errors are clean
step("Step F. Bad input handled cleanly")
code, err = get("/verify-counterparty?agent_id=a-ada-01&category=impossible")
print(f"HTTP {code} · {err.get('detail')}")
expect("an unknown category is a 400 naming the valid set",
       code == 400 and "financial" in str(err.get("detail")))
code, nx = get("/verify-counterparty?agent_id=a-nobody-xyz&category=commerce")
print(f"HTTP {code} · unknown agent -> {nx['reason_code']} (a verdict, not an error)")
expect("an unknown agent is a signed NXAGENT verdict", code == 200 and nx["reason_code"] == "NXAGENT")

# -------------------------------------------------------------------- verdict
step("PASS · agent completed the flow using only skill.md"
     if not failures else "FAIL · " + "; ".join(failures))
sys.exit(1 if failures else 0)
