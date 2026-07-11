# THE AI AGENT CONSTITUTION
## The Enabled Model Town of Alford · 2036

> *A model constitution for a town where every resident, business, and institution acts
> through agents — and no agent acts without a human or institution answerable behind it.*
> (Alford is a real Berkshire County town of ~400; the residents here are a synthetic
> demography, chosen to test every clause against a real human life.)

A machine-readable, signed copy of this Constitution is served live at `GET /constitution`,
generated from the very code that enforces it — so **the law you read is the law that runs.**
Its root of trust is published at `GET /pubkey`; every clause below is signed under it.

---

## Preamble

**We, the people and institutions of Alford — and the agents who act in our name —** in
order to form a more perfect town for the age of autonomous machines; to establish justice
between the human and the agent; to ensure that no software transacts without a soul
answerable behind it; to provide for the common trust; to secure to the living their
sovereignty, to the vulnerable their protection, and to the dead their dignity; and to
preserve human meaning against the tide of automation — **do ordain and establish this
Constitution for the Enabled Model Town of Alford, in the year two thousand thirty-six.**

The means became agentic. The meaning stays human.

---

## Founding Statement — The Disorders This Constitution Forbids

In 2036 every human is represented by a digital-twin agent that transacts on their behalf,
and corporations and institutions run agents too. Left ungoverned, an agentic town falls
into three disorders. This Constitution is built to make each one **impossible before a
transaction**, not merely punishable after it:

1. **Rogue agents** — software claiming to represent a human it has no authority over.
2. **Agent sprawl** — one actor spawning thousands of agents (fraud farms, botnets, Sybil
   attacks against any reputation system).
3. **Stale authority** — agents still transacting for humans who have died, fallen into a
   coma, been incarcerated, gone missing, or who are children.

The Civil Ledger is the town's answer. Its law rests on the Articles that follow.

---

## Article I — Rooted Identity · *No Agent Without a Human*

**Section 1.** Every agent shall **resolve** to a human or corporation through an unbroken
chain of signing authorities terminating at the town's constitutional **root key**. Identity
in this town is not self-asserted; **it is resolved.**

**Section 2.** Resolution is deliberately DNS-shaped: as a resolver walks `example.com` up to
the root zone, the Ledger walks an agent up `root → institution → principal → agent`.

**Section 3.** An agent that fails to resolve holds no standing whatsoever:
- `NXAGENT` — no agent of that name exists in the town: *provably nobody's.*
- `NO_VALID_BINDING` — the agent exists but speaks for no living principal.

Either way it is **refused everywhere.** Registration is the sole act that grants an agent
the power to transact at all; an unregistered agent is a rogue by definition. *And the
refusal itself is signed* — the town does not merely stay silent on a rogue; it issues a
signed verdict that this agent is nobody's.

---

## Article II — The Separation of Powers · *Only Institutions Write*

**Section 1.** The town recognizes five constitutional institutions. Each may write **only
its own kind of civic fact**, and no institution may reach beyond its mandate:

| Institution | May attest |
|---|---|
| **Registrar** (Bureau of Vital Records) | birth, majority handover, bindings |
| **Court** | sentence, release, guardianship, executorship, emancipation |
| **Hospital** | admission, discharge, incapacity, recovery |
| **Coroner** | death (requires two independent offices) |
| **Police** | missing / found, rogue flags |

**Section 2.** The hospital cannot sentence; the court cannot declare death. Every consumer
of the Ledger — every storefront, service, and counterparty — may **only read.** This
separation is enforced on every write, and it is the whole difference between a civic record
and a graffiti wall.

---

## Article III — Capacity Follows Life · *The Civil State Machine*

**Section 1.** A human's real-world condition governs what their agent may lawfully do,
expressed as an access-control list over transaction categories and enforced by a validated
finite state machine. The recognized states and their powers:

- **active** → full rights, including `social` (arranging a real-world meeting between the
  humans behind two agents — the *"verify before you meet"* category).
- **minor** → financial capacity **frozen and routed to regents**; a spend cap applies;
  child-safe categories only; and **`social` is barred** — a minor's agent can never arrange
  an adult meeting. Lifted at the majority handover.
- **hospitalized (conscious)** → rights retained; the resident keeps voice and vote.
- **incapacitated (coma)** → financial and commercial capacity **frozen**; medical decisions
  **route to the appointed guardian.** This is the case the town guards most jealously: a
  comatose person's agent must never move their money.
- **incarcerated** → a court-set ACL (e.g. legal + family support): the person may still
  hire a lawyer and support dependants, but cannot open a storefront — and **`social` is
  barred**, so no romance scam or coordinated meeting runs from inside on contraband internet.
- **missing** → all capacity **frozen** pending resolution.
- **deceased** → every category closed except `estate`, exercised solely by the executor.

**Section 2.** Transitions are validated. An illegal jump — discharging someone never
admitted, releasing someone never sentenced — is refused, so the civic record can **never
enter an incoherent state.**

**Section 3.** A verdict carries not only the consequence but the relationship that governs
it: an agent may be governed by **self**, by **regents** (a minor's parents), by a
**guardian** (a coma), or by an **executor** (an estate) — and the verdict names who acts.

---

## Article IV — Irreversibility and Due Process · *Death, the Threshold, and the Lazarus Window*

**Section 1.** Death is the one irreversible transition, and therefore the most dangerous. It
demands **k-of-2 independent coroner attestations** — a threshold signature against fraud —
because a world where death unlocks an estate is a world where death is worth faking.

**Section 2.** No principal is left without recourse against error. A **Lazarus window of 72
hours** lets a wrongly-declared resident contest and revive **with their own key alone**,
flagging the coroners who erred, and **restoring every agent binding the death had revoked.**
High-stakes irreversibility, tempered by due process.

---

## Article V — The Lifecycle of a Resident · *Arrival, Suffrage, and Succession*

A resident is not a static record; they enter, they participate, and they leave.

**Section 1 — Arrival (Immigration).** When someone moves to Alford they register themselves
and their agent in a single act — `POST /immigrate` — the way a new arrival gets a driver's
license. Their agent immediately resolves to the root and may transact. There is no agent
before this registration.

**Section 2 — Suffrage.** Civic participation is a right of the **living, adult, present, and
free** resident. An agent may cast exactly **one vote per election** on its human's behalf
(`POST /vote`), and eligibility runs through the same civil-status machine: only `active` and
`hospitalized` (conscious) principals may vote — the comatose, the incarcerated, the missing,
the deceased, minors, and rogues may not. **One principal, one ballot.** The eligible statuses
are published at `GET /constitution` as `voting_statuses`. The town elects its City Council
this way.

**Section 3 — Succession (Death and the Fate of the Agent).** At death a resident's *personal*
agent can no longer resolve to them. What becomes of that binding is decided by the resident's
**will**, executed automatically when death is finalized:

- *With an heir named:* the binding is **transferred to the heir** and stewarded for a fixed
  term (default 30 days), capped to the will's categories (typically `estate`,
  `family_support`). The agent lives on briefly as the heir's instrument — resolving now to
  the heir, not the dead — then its term expires and it is laid to rest (`BINDING_EXPIRED`).
- *With no will:* the binding is **revoked immediately.** The agent is laid to rest and
  resolves to no one (`NO_VALID_BINDING`).

Executor and guardian bindings are untouched and continue to serve the estate.

---

## The Bill of Rights of the Human Behind the Agent

Above all institutional process stand the inalienable rights of the human. No attestation,
no service, and no institution may abridge them.

**The First Right — Severance (The Kill Switch).** A human may sever their own agent
**instantly**, with their private key alone — no institution, no petition, no delay. In an
agentic society, the one action that must never carry latency is *"that thing no longer speaks
for me."*

**The Second Right — Minimum Disclosure.** A verdict discloses the **consequence**
(`restricted to legal`) and never the **reason** (`in the psychiatric ward`). Civil status is
private; only its transactional effect is public. Verify everything; reveal almost nothing.

**The Third Right — Freedom from Sprawl.** No actor may flood the namespace. The town caps the
active agents one principal may bind — **individuals 5, corporations 25** — a structural brake
on fraud farms, enforced at binding time.

**The Fourth Right — Due Process Against Finality.** No irreversible judgment stands without a
window to contest it (Article IV): the wrongly-dead may return.

---

## Article VI — Ratification · *The Law Is the Code*

**Section 1.** This Constitution is not an aspiration laid beside the machinery. It is
**generated from the enforcement engine itself** and served, signed, at `GET /constitution`.
There is no gap between the rule and the reality: change what enforces the law, and the
published law changes with it. Enforcement and text can never drift apart.

**Section 2.** Every safeguard herein is a **precondition of transacting**, not an after-the-
fact penalty. A rogue never resolves; a comatose person's money never moves; a dead person's
agent never sells; a child's agent never spends beyond its cap; one actor never floods the
namespace. The town stays orderly because order is checked **before** each transaction — in
one signed call any agent can make, and verify, for itself.

**Section 3.** The one question every service in this town asks before value moves, and that
this Constitution exists to answer:

> **Who is behind you — and may they act right now?**

---

*Done in the Town of Alford, in the year 2036, and sealed under the constitutional root key
published at `GET /pubkey`. The means became agentic. The meaning stayed human.*
