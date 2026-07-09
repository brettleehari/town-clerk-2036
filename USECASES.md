# What agents ask the Civil Ledger — the service layer (131 use cases)

A catalog of concrete jobs an autonomous agent can request from KYA using only SKILL.md
and the live API. Grouped by service. Each line pairs a scenario with the call/verdict it
maps to. **Kept as reference only — not rendered in the UI for now.**

## Financial · verify before money moves
- A payments agent verifies a payee before wiring funds — `verify-counterparty?category=financial`
- A lending agent checks a borrower isn't operating for a dead principal — `→ PRINCIPAL_DECEASED`
- A payroll agent confirms an employee's agent still has a valid binding — `binding_valid:true`
- An escrow agent verifies both parties before releasing funds — `POST /verify-batch`
- A subscription agent re-checks a customer before the monthly charge — `GET /verify-counterparty`
- A wallet agent refuses a transfer to an agent flagged rogue — `→ ROGUE_FLAGGED`
- A treasury agent screens a vendor for a capacity freeze before prepayment — `→ CAPACITY_FROZEN`
- A remittance agent confirms the recipient resolves to a real human, not a mule — `GET /resolve`
- An invoicing agent checks a counterparty before extending credit terms — `category=financial`
- A tax agent verifies an estate's executor before disbursing a refund — `category=estate`
- A donation agent confirms a fundraiser is bound to a real principal — `binding_valid`
- A refund agent verifies the original payer still represents that human — `GET /bindings`
- A margin agent halts trading for a counterparty who went missing — `→ PRINCIPAL_MISSING`

## Commerce · storefront gating
- A storefront agent serves only customers whose agents verify — `category=commerce`
- A marketplace matcher screens both buyer and seller before pairing — `POST /verify-batch`
- A ticketing agent refuses a minor's agent buying age-restricted goods — `→ CATEGORY_NOT_ALLOWED`
- A rental agent verifies a renter before handing over the keys — `verify-counterparty`
- A checkout agent confirms the card-holder's agent has a live binding — `binding_valid`
- A wholesale agent blocks a jailed principal from opening an account — `→ CATEGORY_NOT_ALLOWED`
- A returns agent verifies the buyer before authorizing a refund — `GET /verify-counterparty`
- A loyalty agent enrolls only verified customer agents — `category=commerce`
- A dropship agent screens a supplier for rogue flags — `rogue_flag`
- A booking agent confirms a guest resolves to a real human — `GET /resolve`
- A dynamic-pricing agent watches a repeat buyer for status changes — `POST /watch`
- A procurement agent bulk-screens 100 vendor agents in one call — `POST /verify-batch`
- A storefront auto-pauses a subscriber the instant capacity freezes — `watch → webhook`

## Legal · contracts & counsel
- A contracts agent verifies a counterparty before executing an agreement — `category=legal`
- A retainer agent confirms an incarcerated principal may still hire counsel — `→ proceed:true`
- A notary agent checks the signer's agent has a valid binding — `binding_valid`
- A dispute agent verifies both parties resolve to real principals — `GET /resolve`
- An arbitration agent screens a claimant for rogue flags — `rogue_flag`
- A compliance agent confirms a signatory isn't a minor — `status_acl`
- A power-of-attorney agent verifies the grantor's liveness — `verify-counterparty`
- A licensing agent checks an applicant resolves to a human — `→ NO_VALID_BINDING?`
- A settlement agent verifies an executor for a deceased party — `category=estate`
- A subpoena agent confirms the served party's binding — `GET /bindings`
- A guardianship agent reads who governs a principal — `governed_by`
- An NDA agent bulk-verifies counterparties before circulating a draft — `POST /verify-batch`

## Medical · guardian routing
- A telehealth agent routes a coma patient's care to the guardian — `category=medical → guardian`
- A pharmacy agent verifies a patient before dispensing — `verify-counterparty`
- A records agent refuses financial requests for an incapacitated principal — `→ CAPACITY_FROZEN`
- A consent agent confirms a minor's medical requests route to regents — `governed_by:regents`
- A scheduling agent verifies a patient has a live binding — `binding_valid`
- An insurance agent checks a claimant isn't deceased before payout — `→ PRINCIPAL_DECEASED`
- A caregiver agent confirms its authority as a coma patient's guardian — `governed_by`
- A discharge agent reviews the attested status history — `GET /rites`
- A triage agent screens an inbound agent for rogue flags — `rogue_flag`
- An eldercare agent watches a patient for incapacitation — `POST /watch`
- A mental-health agent honors minimum disclosure — 'refused', not why — `reason_code only`
- A prescription agent verifies the requester resolves to a real human — `GET /resolve`

## Family support · parental controls
- A childcare agent verifies a newborn's natal agent runs under regents — `category=family_support`
- An allowance agent honors a minor's spend cap — `spend_cap`
- A tuition agent confirms a dependant's binding — `binding_valid`
- A benefits agent verifies a family member resolves to a human — `GET /resolve`
- A support-payment agent confirms a jailed parent may still support kin — `→ proceed:true`
- A custody agent reads guardianship — `governed_by`
- A dependant-care agent confirms a minor can't transact financially — `→ CAPACITY_FROZEN`
- A school-enrollment agent confirms a regent's authority — `governed_by:regents`
- A family-plan agent bulk-verifies every member — `POST /verify-batch`
- A handover agent confirms controls lifted at adulthood — `GET /rites`
- A guardian-appointment agent verifies the appointed guardian's agent — `verify-counterparty`
- A minor-safety agent refuses any social request from a child's agent — `category=social → refused`

## Estate · death & inheritance
- An executor agent settles a deceased principal's affairs — `category=estate → proceed`
- A probate agent verifies the court-appointed executor — `governed_by:executor`
- An inheritance agent confirms an heir stewards an inherited agent — `inherited:true`
- A will agent registers a will while the principal is alive — `POST /wills`
- An estate agent refuses commerce for a deceased principal — `→ PRINCIPAL_DECEASED`
- A trust agent detects an inherited agent past its term — `→ BINDING_EXPIRED`
- A beneficiary agent confirms the heir's liveness — `verify-counterparty`
- An asset-transfer agent routes only estate matters to the executor — `category=estate`
- A Lazarus agent contests a wrongful death within 72h — `POST /contest`
- A funeral agent verifies the estate's authorized representative — `governed_by`
- An heirloom agent checks an inherited agent's capped categories — `allowed_categories`
- A legacy agent confirms a no-will agent was laid to rest — `→ NO_VALID_BINDING`

## Civic · residency & elections
- A voting agent casts one resident's ballot — `POST /vote`
- A registrar agent immigrates a new resident — `POST /immigrate`
- A poll agent confirms only living adults may vote — `VOTING_STATUSES`
- A census agent reads anonymous town statistics — `GET /census`
- A tally agent watches an election in real time — `GET /elections/{id}`
- A civic-ID agent verifies a resident's binding — `binding_valid`
- A ballot agent refuses a second vote from one resident — `→ 409`
- A community agent confirms a member resolves to a real human — `GET /resolve`
- A petition agent bulk-verifies signatory agents — `POST /verify-batch`
- A jury agent verifies a resident isn't deceased or missing — `reason_code`
- A town-hall agent screens attendees for rogue flags — `rogue_flag`
- A residency agent confirms an immigrant's new binding — `→ proceed:true`

## Social · verify before you MEET
- A dating agent verifies a match is a real, consenting adult — `category=social`
- A meetup agent refuses a minor's agent arranging an adult meeting — `→ age-gate`
- A dating agent catches a catfish that resolves to no human — `→ NO_VALID_BINDING`
- A safety agent blocks a romance scam run from a jail cell — `→ CATEGORY_NOT_ALLOWED`
- Two agents run a bilateral social check before a first date — `both proceed`
- A companion agent proves adulthood without revealing a birthday — `minimum disclosure`
- A social agent mints a signed safety receipt to text a friend — `GET /certificates/{id}`
- A matchmaker bulk-screens candidate agents on social — `POST /verify-batch`
- A friend-finder confirms a new contact's liveness — `verify-counterparty`
- A community-event agent refuses agents whose principals are missing — `→ PRINCIPAL_MISSING`
- A social agent watches a match for status changes — `POST /watch`
- A chaperone agent verifies both parties before an in-person meet — `category=social`
- A verification agent confirms a profile isn't flagged rogue — `rogue_flag`

## Security · rogue-agent defense
- A watchdog agent detects an impostor resolving to no human — `→ NO_VALID_BINDING`
- A security agent self-registers as police and flags a rogue — `flag_rogue`
- A defense agent confirms a flag propagates town-wide — `→ ROGUE_FLAGGED`
- A sentinel agent detects a wholly unknown agent — `→ NXAGENT`
- An anti-botnet agent trips the per-principal sprawl cap — `→ SPRAWL_LIMIT`
- A fraud agent screens a counterparty before every deal — `verify-counterparty`
- A trust agent clears a wrongly-flagged agent — `clear_flag`
- A monitor agent watches a suspicious agent's binding — `POST /watch`
- A gatekeeper refuses any agent with an expired binding — `→ BINDING_EXPIRED`
- A verifier confirms a resolution chain up to the root — `GET /resolve`
- A police agent reports a person missing — `report_missing`
- An audit agent detects a tampered verdict — `POST /verify → false`

## Compliance · receipts & bulk
- A compliance agent stores every verdict as a signed receipt — `GET /certificates/{id}`
- An auditor re-verifies a past verdict against the root key — `POST /verify`
- A KYC agent bulk-screens a whole order book — `POST /verify-batch`
- A due-diligence agent archives a cert as proof of a check — `cert_id`
- A regulator agent confirms a verdict's signature and TTL — `valid_until`
- A screening agent triages an inbox of 100 agents in one call — `POST /verify-batch`
- A receipt agent re-fetches a verdict long after its TTL lapsed — `GET /certificates`
- A reporting agent proves due diligence with a signed certificate — `signature`
- A batch agent summarizes proceed/refuse counts across a cohort — `summary`
- A verification agent checks a cert's valid_until is in the future — `valid_until`

## Identity · resolution & human rights
- A resolver agent walks the DNS-style chain root→agent — `GET /resolve/{id}`
- A binding agent checks which principal an agent represents — `GET /bindings/{id}`
- A human severs their own agent instantly — the kill switch — `DELETE /bindings + X-Principal-Key`
- A pubkey agent fetches the root key to verify every cert — `GET /pubkey`
- A liveness agent confirms a counterparty is a living human — `reason_code`
- A capacity agent queries a human's status directly — `GET /capacity/{id}`
- A rites agent reads a public, redacted life-event log — `GET /rites/{id}`
- A law agent fetches the signed constitution and reasons over it — `GET /constitution`
- An onboarding agent self-serves an institution key — `POST /institutions/register`
- A recovery agent restores a binding via Lazarus — `POST /contest`
