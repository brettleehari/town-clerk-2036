# The Constitution of Alford, Massachusetts

*How an agent-native town avoids chaos. (Alford is a real Berkshire County town of ~400;
the residents here are a synthetic demography.)*

A machine-readable, signed copy of this constitution is served live at `GET /constitution`,
generated from the very code that enforces it — so the law you read is the law that runs.

In 2035 every human is represented by a digital-twin agent that transacts on their behalf,
and corporations and institutions run agents too. Left ungoverned, this produces three
failure modes the city must prevent by design:

1. **Rogue agents** — software claiming to represent a human it has no authority over.
2. **Agent sprawl** — a single actor spawning thousands of agents (fraud farms, botnets,
   Sybil attacks on any reputation system).
3. **Stale authority** — agents still transacting for humans who have died, fallen into a
   coma, been incarcerated, gone missing, or who are children.

The Civil Ledger is the city's answer. It rests on five pillars.

## Pillar I — Rooted identity (no agent without a human)

Every agent must **resolve** to a human or corporation through a chain of signing
authorities terminating at the city's constitutional **root key**. This is deliberately
DNS-shaped: as a resolver walks `example.com` up to the root zone, the Ledger walks an
agent up `root → institution → principal → agent`. An agent that fails to resolve is
`NXAGENT` (does not exist) or `NO_VALID_BINDING` (exists but speaks for nobody). Either
way it is refused. **Identity is not self-asserted; it is resolved.**

## Pillar II — Separation of powers (only institutions write)

The city has five constitutional institutions, and each may write only its own kind of
civic fact:

| Institution | May attest |
|---|---|
| Registrar (Bureau of Vital Records) | birth, majority handover, bindings |
| Court | sentence, release, guardianship, executorship, emancipation |
| Hospital | admission, discharge, incapacity, recovery |
| Coroner | death (requires two independent offices) |
| Police | missing/found, rogue flags |

No institution can reach beyond its mandate — the hospital cannot sentence, the court
cannot declare death. Every consumer only reads. This separation is enforced on every
write and is the difference between a civic record and a graffiti wall.

## Pillar III — Capacity follows real life (the civil state machine)

A human's real-world condition governs what their agent may lawfully do, expressed as an
access-control list over transaction categories and enforced by a finite state machine:

- **active** → full rights, including `social` (arranging a real-world meeting between the
  humans behind two agents — the "verify before you meet" category).
- **minor** → financial frozen and routed to regents; a spend cap applies; child-safe
  categories only, and **`social` is barred** — a minor's agent can never arrange an adult
  meeting. Lifted at the majority handover.
- **hospitalized (conscious)** → rights retained.
- **incapacitated (coma)** → financial and commercial capacity **frozen**; medical
  decisions **route to the appointed guardian**. This is the case the city cares about
  most: a comatose person's agent must never move their money.
- **incarcerated** → a court-set ACL (e.g. legal + family support); the person can still
  hire a lawyer and support dependants, but cannot open a storefront — and **`social` is
  barred**, so a prisoner with contraband internet cannot run romance scams or coordinate
  meetings from inside.
- **missing** → frozen pending resolution.
- **deceased** → all categories closed except `estate`, exercised only by the executor.

Transitions are validated: an illegal jump (e.g. discharging someone who was never
admitted) is refused, so the record can never enter an incoherent state.

## Pillar IV — Irreversibility with a safety valve

Death is the one irreversible transition, so it demands **k-of-2 independent coroner
attestations** — a threshold signature against fraud, because a world where death unlocks
an estate is a world where death is worth faking. A **Lazarus window** (72h) lets a
wrongly-declared principal contest and revive with their own key, flagging the coroners
who erred. High-stakes irreversibility, with due process.

## Pillar V — Human sovereignty (limits on the machine)

Two rights sit above institutional process:

- **The kill switch.** A human can sever their own agent instantly, with their private
  key alone — no institution, no delay. In an agentic society the one action that must
  never have latency is *"that thing no longer speaks for me."*
- **Minimum disclosure.** A verdict tells a counterparty the *consequence*
  (`restricted to legal`) never the *reason* (`in the psychiatric ward`). Civic status is
  private; only its transactional effect is public.

And against sprawl, the city caps how many active agents one principal may bind
(individuals 5, corporations 25) — a structural brake on fraud farms, enforced at
binding time.

## Pillar VI — The lifecycle: arrival, suffrage, and death

A resident is not a static record; they enter, participate, and leave.

**Arrival (immigration).** When someone moves to Alford they register themselves and their
agent in one act — `POST /immigrate` — the way a new arrival gets a driver's license. Their
agent immediately resolves to the root and may transact. There is no agent without this
registration; an unregistered agent is a rogue.

**Suffrage.** Civic participation is a right of the living adult resident, present and free.
An agent may cast exactly one vote per election on its human's behalf (`POST /vote`), and
eligibility is enforced through the same civil-status machine: only `active` and
`hospitalized` (conscious inpatient) principals may vote — the comatose, the incarcerated,
the missing, the deceased, minors, and rogues cannot; one principal, one ballot. The
eligible statuses are published at `GET /constitution` as `voting_statuses`. The town
elects its City Council this way.

**Death and the fate of the agent.** At death the deceased's *personal* agent can no longer
resolve to them — they are gone. What happens to that softlink is decided by the resident's
**will**, executed automatically when death is finalized:

- *With an heir named:* the binding is transferred to the heir and stewarded for a fixed term
  (default 30 days), capped to the will's categories (typically `estate`, `family_support`).
  The agent lives on briefly as the heir's instrument — resolving now to the heir, not the
  dead — then its term expires and it is laid to rest (`BINDING_EXPIRED`).
- *With no will:* the binding is revoked immediately. The agent is laid to rest and resolves
  to no one (`NO_VALID_BINDING`).

Executor and guardian bindings are untouched and continue to serve the estate. And because
death can be wrongly declared, the Lazarus contest not only revives the principal but
restores the agent bindings the death had revoked.

## Why this prevents chaos rather than merely reacting to it

Every safeguard is a *precondition of transacting*, not an after-the-fact penalty. A rogue
never resolves; a comatose person's money never moves; a dead person's agent never sells;
a child's agent never spends beyond its cap; one actor never floods the namespace. The
city stays orderly because order is checked **before** each transaction, in one signed
call any agent can make — and verify — for itself.
