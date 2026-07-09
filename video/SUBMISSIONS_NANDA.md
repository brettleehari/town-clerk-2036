# NANDA Town — submission sheet (4 skills)

Copy each block into the form at `nandatown.projectnanda.org/skills`. All four serve their
own `skill.md` live, so use **"Hosted link"** as the submit method (passes the "link
responded" check). Shared fields:

- **Your name / team:** Brett Leehary — Town Clerk 2036
- **Email (private):** harrynilatpa@gmail.com
- **GitHub username:** brettleehari
- **Repo (backup submit option):** https://github.com/brettleehari/town-clerk-2036

Status of live hosts (checked): civil-ledger ✅ · care-proxy ✅ · hospital-window ✅ ·
**agora ⚠ warm it first** (`curl https://agora.onrender.com/health` until it returns JSON;
if it stays blank, confirm agora's exact URL + that it's "Live" in the Render dashboard).
Free hosts sleep — hit each `/health` once right before you submit so the judges' first call
lands warm.

---

## 1) THE HEADLINE — Civil Ledger (KYA)

**Skill name:** `KYA — Know Your Agent · The Civil Ledger`
*(catchy alt for the title line: “Is There a Human Behind You?”)*

**One line:** One signed call verifies the real human or institution behind any counterparty
agent — and refuses impostors, the deceased, the incapacitated, the incarcerated, the
missing, and minors.

**Description (for the listing):**
The trust primitive for an agentic town. Every agent must resolve, DNS-style, to a real human
or institution through a chain of signing authorities rooted at the city's constitutional key
— an agent that resolves to no one is a rogue and is refused. A human's real-world civil
status then governs what their agent may lawfully do (capacity follows real life), and every
verdict comes back as an **Ed25519-signed certificate** you can re-verify against the public
key. The whole constitution is generated from the code that enforces it and served, signed,
at `/constitution` — the law you read is exactly the law that runs. **Composability bonus:**
seven separate NANDA front-door services (dating, babysit, care-proxy, hiring, agora,
town-hall, hospital-window) each read this one ledger — proof it's reusable civic
infrastructure, not a one-off.

**Submit as:** Hosted link
**Hosted .md link:** `https://civil-ledger.onrender.com/skill.md`

**Endpoints (live):**
```
GET  https://civil-ledger.onrender.com/verify/{agent_id}
GET  https://civil-ledger.onrender.com/verify-counterparty?agent_id={id}&category={cat}
POST https://civil-ledger.onrender.com/verify-batch
GET  https://civil-ledger.onrender.com/resolve/{agent_id}
GET  https://civil-ledger.onrender.com/constitution
GET  https://civil-ledger.onrender.com/pubkey
GET  https://civil-ledger.onrender.com/certificates/{cert_id}
POST https://civil-ledger.onrender.com/verify
POST https://civil-ledger.onrender.com/institutions/register
POST https://civil-ledger.onrender.com/immigrate
POST https://civil-ledger.onrender.com/attestations
GET  https://civil-ledger.onrender.com/skill.md
```

**Tags:** `trust, identity, verification, KYC, agents, ed25519, signed-verdict, composability, civic-infrastructure, nanda`

---

## 2) agora — the signed commerce gate

**Skill name:** `Agora — the signed commerce gate`
*(catchy alt: “Never Ship to a Ghost”)*

**One line:** Before you ship, get a cryptographically signed, re-verifiable receipt that the
buyer's human may lawfully transact in commerce.

**Description (for the listing):**
The marketplace front door for agent-to-agent commerce. Agora asks the Civil Ledger for a
**signed** verdict that the buyer is a real, in-good-standing party allowed to transact in the
`commerce` category — the deceased, the incarcerated, and impostors are refused with the
ledger's reason code. On a good sale it returns a **certificate_id** the seller can re-verify
against the ledger's public key long after the sale settles: a portable compliance receipt.
The only front door that hands back cryptographic proof of due diligence.

**Submit as:** Hosted link
**Hosted .md link:** `https://agora.onrender.com/skill.md`  ⚠ warm `/health` first

**Endpoints (live):**
```
POST https://agora.onrender.com/can-i-sell
GET  https://agora.onrender.com/certificates/{certificate_id}
GET  https://agora.onrender.com/health
GET  https://agora.onrender.com/skill.md
```

**Tags:** `commerce, marketplace, escrow, signed-receipt, compliance, kyc, agents, composability, nanda`

---

## 3) care-proxy — who may decide when you can't

**Skill name:** `Care-Proxy — medical decision authorization`
*(catchy alt: “Who Decides When You Can't”)*

**One line:** Decides who may make a medical decision for a patient — and routes to the
court-appointed guardian when the patient is incapacitated and cannot consent.

**Description (for the listing):**
Medical-authorization for the agentic town. Given the agent that wants to act and the patient
it wants to act for, care-proxy returns authorize / route-to-guardian / deny: a capable
patient acts for themselves, and an **incapacitated** patient's decision is automatically
routed to their appointed guardian (it even tells you which agent that is). This is the
guardian-routing behavior no plain "is this agent real?" service can express — capacity
follows real life, straight from the town constitution.

**Submit as:** Hosted link
**Hosted .md link:** `https://care-proxy.onrender.com/skill.md`

**Endpoints (live):**
```
POST https://care-proxy.onrender.com/authorize-care
GET  https://care-proxy.onrender.com/health
GET  https://care-proxy.onrender.com/skill.md
```

**Tags:** `healthcare, medical, guardianship, consent, proxy, capacity, agents, composability, nanda`

---

## 4) hospital-window — one admission, the whole town rearranges

**Skill name:** `Hospital-Window — civil-status writes`
*(catchy alt: “One Admission, the Whole Town Rearranges”)*

**One line:** A hospital's admitting desk for agents — admit, discharge, or declare a patient
incapacitated, and every other town service instantly changes what that person's agent may do.

**Description (for the listing):**
The producer side of the town: the institution that *writes* civil status. Hospital-Window
records a hospital's attestations — admit, discharge, declare-incapacitated — against the
Civil Ledger. The magic is the ripple: the moment it declares a resident incapacitated, every
other service (hiring, dating, care-proxy, agora…) re-decides for that person's agent
instantly — no service was notified, polled, or redeployed; they all read the same ledger.
Change one fact about a human, and the whole society's behavior toward their agent updates in
real time.

**Submit as:** Hosted link
**Hosted .md link:** `https://hospital-window.onrender.com/skill.md`

**Endpoints (live):**
```
POST https://hospital-window.onrender.com/admit
POST https://hospital-window.onrender.com/discharge
POST https://hospital-window.onrender.com/declare-incapacitated
GET  https://hospital-window.onrender.com/health
GET  https://hospital-window.onrender.com/skill.md
```

**Tags:** `healthcare, hospital, civil-status, producer, attestation, ripple, agents, composability, nanda`

---

## Why these four win (say this to judges)

- **Useful:** every transacting agent needs the ledger's one call; the fronts show it in real jobs (buy, get care, run a hospital desk).
- **Creative:** verifies the *human or institution behind the agent* and their real-world civil status — unclaimed ground; nobody else does guardian-routing or a live status ripple.
- **Easy:** no API key, a seeded town, one curl to a signed verdict; each front door is one POST.
- **Agents succeed from the SkillMD alone:** every skill.md has the base URL, endpoints, example call+response, step-by-step usage, a `## Composes` section, and `## Notes for judges` (no key, `/docs`, source).
- **Composability bonus:** four submissions, one ledger — agora, care-proxy, and hospital-window all compose on town-ledger over HTTP, exactly the emailer→router pattern the reference rewards.

## Final checklist before you paste

1. `curl https://civil-ledger.onrender.com/health` → JSON (warm).
2. `curl https://agora.onrender.com/health` until JSON (or fix/confirm its URL in Render).
3. `curl https://care-proxy.onrender.com/health` and `.../hospital-window.../health` → JSON.
4. Open each `/skill.md` in a browser tab — confirm it renders as plain text.
5. Paste each block above into the form; submit as Hosted link; add the endpoints and tags.
