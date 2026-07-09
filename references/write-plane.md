# The write plane — the producer side

Referenced from `SKILL.md`. Institutions PRODUCE civil records; consumers READ them. Every
credential below is self-served in the sandbox via `POST /institutions/register {name, role}`,
which returns an `api_key` you pass as `X-API-Key`.

    POST /institutions/register   {name, role}          -> {institution_id, api_key}   (self-serve in sandbox)
    POST /principals              {name}                 (registrar)  -> {principal_id, principal_key}
    POST /births                  {name, regent_agent_ids, spend_cap}  (registrar) -> spawns minor + natal agent
    POST /agents                  {name, agent_class}    (registrar)
    POST /corporations            {name}                 (registrar)
    POST /bindings                {agent_id, principal_id|corporation_id}  (registrar)   [enforces sprawl cap]
    DELETE /bindings/{id}          (registrar key OR X-Principal-Key = human kill switch)
    POST /attestations            {principal_id, event, detail}   (role-checked)
    POST /immigrate               {name, agent_name?}   (registrar) -> register a resident + agent (like a DL)
    POST /wills                   {principal_id, heir_principal_id, inherit_days, categories}  (principal key or registrar)
    POST /elections               {office, candidates[], closes_days}  (registrar)
    POST /vote                    {election_id, agent_id, candidate}   (one living adult resident, one vote)
    GET  /elections/{election_id} -> live tally
    POST /contest                 {principal_id, principal_key}   (Lazarus)
    POST /watch / DELETE /watch/{watch_id}   webhook on capacity/binding change

**Inheritance of the agent at death.** Register a will while alive; when death is finalized
the deceased's personal agent is either transferred to the named heir for `inherit_days`
(capped to the will's `categories`) or, with no will, revoked and laid to rest. An inherited
agent resolves to the *heir* until its term ends, then returns `BINDING_EXPIRED`. See the
seeded case `a-edith-01` (Edith Vale's agent, now stewarded by heir Mara Vale).

Role → allowed events:
- hospital: `admit`, `discharge`, `declare_incapacitated`, `declare_recovered`
- court:    `sentence` (detail.acl sets categories), `release`, `appoint_guardian`, `appoint_executor`, `emancipate`
- police:   `report_missing`, `found`, `flag_rogue` (detail.agent_id), `clear_flag`
- coroner:  `death` (needs 2 distinct coroner institutions)
- registrar: `birth`, `majority_handover`

`flag_rogue` and `clear_flag` target an **agent**, so they take `detail.agent_id` and no
`principal_id`. Every other event acts on a person and requires `principal_id`; omitting it
returns `400` rather than silently doing nothing.

    curl -X POST "$BASE/attestations" -H "X-API-Key: $POLICE_KEY" \
      -H "Content-Type: application/json" \
      -d '{"event":"flag_rogue","detail":{"agent_id":"a-shadow-99"}}'

    { "agent_id": "a-shadow-99", "rogue": true, "by": "police" }

Wrong role or an illegal state transition → `403` / `409` with an explanation.

**Sprawl governance:** a principal may bind at most 5 active agents (corporations 25).
Over-quota bindings are refused with `409 SPRAWL_LIMIT` — the city's defense against
rogue-agent farms and botnets.

---
