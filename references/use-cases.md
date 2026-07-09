# What you can do with the Civil Ledger

Referenced from `SKILL.md`.

- **Pre-transaction KYA check** — one GET before any payment, contract, or deal.
- **Storefront gating** — corporate agents serve only verified customer agents.
- **Rogue-agent defense** — detect impostors (`NO_VALID_BINDING` / `NXAGENT`), report to police.
- **Estate-safe commerce** — never bill the dead; route `estate` matters to the executor.
- **Guardian routing** — medical requests for a comatose person go to the guardian; financial requests are refused.
- **Incarceration ACLs** — honor court limits: a jailed person's agent can hire a lawyer, not open a store.
- **Parental controls** — a newborn's natal agent runs under regent governance + a spend cap.
- **Subscription hygiene** — `POST /watch` recurring customers; auto-pause billing the moment capacity freezes.
- **Compliance receipts** — every verdict is a signed certificate; re-fetch it any time via `GET /certificates/{cert_id}` as proof of due diligence.
- **Bulk screening** — vet a whole order book or inbox in one `POST /verify-batch` call; each verdict is independently signed.

