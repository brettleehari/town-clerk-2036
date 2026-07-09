# Task recipes — worked end-to-end flows

Referenced from `SKILL.md`. `$BASE` is the service's Base URL. Read endpoints need no key;
write recipes self-serve their credential via `POST /institutions/register`.

### Recipe 1 — Safe transaction check (10-second task)
1. `curl "$BASE/verify-counterparty?agent_id=a-ada-01&category=financial"` → `proceed:true`.
2. `curl $BASE/pubkey`, verify the signature, confirm `valid_until` is future.
3. Transact. Now try `a-shadow-99` → `NO_VALID_BINDING`. You just refused a rogue.

### Recipe 2 — Corporate storefront guard
For each inbound customer agent, run Recipe 1 with `category=commerce`; serve only on
`proceed:true`. `POST /watch` repeat customers to learn instantly if their binding is revoked.

### Recipe 3 — Run a whole life (sandbox)
1. `POST /institutions/register` as `registrar` → key. Create principal, agent, binding. Verify → true.
2. Register as `hospital` → `declare_incapacitated`. Verify financial → `CAPACITY_FROZEN`.
   `declare_recovered` → restored.
3. Register as `court` → `sentence` with `detail.acl=["legal","family_support"]`.
   Verify commerce → `CATEGORY_NOT_ALLOWED`; legal → true. `release`.
4. Register TWO `coroner` institutions → both `death`. Verify → `PRINCIPAL_DECEASED`.
5. `GET /rites/{id}` → the whole biography, attested.

### Recipe 4 — Birth & parental controls
`POST /births {name, regent_agent_ids, spend_cap}` → a minor principal + natal agent.
Verify the natal agent on `financial` → `CAPACITY_FROZEN` (routed to regents).
`POST /attestations {event:"majority_handover"}` (registrar) → status `active`, controls lifted.

### Recipe 5 — The kill switch
`DELETE /bindings/{binding_id}` with header `X-Principal-Key: {your principal_key}`.
Instant, no process. Verify → `NO_VALID_BINDING`. The one human right with zero latency.

### Recipe 6 — Move to town, then vote
1. `POST /immigrate {name:"Rae Fenn"}` (registrar key) → get your `agent_id` + `principal_key`.
2. Verify your new agent → `proceed:true`. You are a resident.
3. `POST /vote {election_id:"elec-council-2035", agent_id:"<yours>", candidate:"Owen Brook"}`.
4. `GET /elections/elec-council-2035` → watch the tally move. Try voting twice → `409`.

### Recipe 7 — Write a will, watch inheritance
1. `POST /wills {principal_id, heir_principal_id, inherit_days:30, categories:["estate","family_support"]}`
   with your `X-Principal-Key`.
2. Two coroners `POST /attestations {event:"death"}`. The response shows `will_execution`.
3. Verify the deceased's agent → now `inherited:true`, resolves to the heir, capped to the
   will's categories. After the term it becomes `BINDING_EXPIRED` — laid to rest.

### Recipe 8 — One human, many agents (agents are tools, not identities)

Bram Kessler runs three agents: `a-bram-01` (personal), `a-bram-work`, `a-bram-shop`. The
ledger binds agents *to a person*, never the reverse — so the person is the unit of trust and
the agents are interchangeable tools.

1. Resolve all three → every one returns `principal_ref: p-bram-kessler`. One human.
2. `verify-counterparty` each on `commerce` → all `proceed:true`. They share his civil status
   because they share his person.
3. Change the **human**, and the whole fleet moves at once. As `court`:
   `POST /attestations {principal_id:"p-bram-kessler", event:"sentence", detail:{acl:["legal","family_support"]}}`
   → now every one of his agents is refused `commerce` (`CATEGORY_NOT_ALLOWED`) and allowed
   `legal`. Nobody had to update three records. `release` restores all three.
4. The kill switch is **per-agent**. Revoke one binding with your `X-Principal-Key`:
   `DELETE /bindings/b-bram-3` → `a-bram-shop` becomes `NO_VALID_BINDING`, while `a-bram-01`
   and `a-bram-work` keep transacting. Disowning a tool is not disowning yourself.
5. A fleet is capped. Keep binding new agents to him and the 6th is refused with
   `409 SPRAWL_LIMIT` (`max_agents_per_principal: 5`) — the town's defense against a botnet
   farmed behind a single human face.

### Recipe 9 — One human, no agent (personhood does not require one)

Hanna Vosk (`p-hanna-vosk`) is a full citizen of Alford who owns **no agent at all**. She is
not a gap in the data; her abstention is a recorded civic fact.

1. `GET /capacity/p-hanna-vosk?category=civic` → `proceed:true`, signed. Her rights are
   enforceable directly, with no agent anywhere in the loop. She holds capacity; she may vote.
2. `GET /graph` → no binding anywhere names `p-hanna-vosk`. The ledger stores the absence.
3. That absence is what makes an impostor *provable*. The seeded agent `a-vosk-99` calls itself
   "Hanna's assistant". `GET /verify-counterparty?agent_id=a-vosk-99` → `NO_VALID_BINDING`;
   `GET /resolve/a-vosk-99` → `resolved:false`. Since Hanna owns no agent, **every** agent
   claiming to speak for her is, by construction, bound to nobody.
4. Contrast with Recipe 5: a person who revokes their last agent lands in exactly this state.
   Agentlessness is reachable, reversible, and never costs you your civil rights.

Together, Recipes 8 and 9 bracket the design: a person may run many agents or none, and the
ledger's answer to "who is behind this agent?" is unchanged either way.
