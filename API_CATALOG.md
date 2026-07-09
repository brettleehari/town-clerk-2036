# API catalog — the four submitted services

Every request below was executed and every response captured verbatim by `tools/gen_catalog.py`. Nothing is hand-written, so this file cannot drift from the code. Long payloads are truncated with a byte count.

**Seeded cast.** `a-ada-01` active · `a-shadow-99` impostor · `a-june-01` coma (guardian `a-okafor-g`) · `a-marlow-01` incarcerated · `a-silas-01` deceased (executor `a-vane-exec`) · `a-tam-01` minor (regents `a-holt-mom`/`a-holt-dad`, spend cap 50) · `a-iris-01` missing · `a-edith-01` inherited by heir `p-mara-vale` · `a-bram-01`, `a-bram-work`, `a-bram-shop` one human with three agents · `p-hanna-vosk` one human with none · `a-store-01` corporate storefront.

Sandbox institution keys: `sk_seed_registrar` `sk_seed_court` `sk_seed_hospital` `sk_seed_coroner_a` `sk_seed_coroner_b` `sk_seed_police`.


## 1. civil-ledger — the Civil Ledger (KYA)

Base URL `https://civil-ledger.onrender.com` · skill `name: town-ledger`. **All 36 public routes.** Every read is open and keyless; writes need a role-scoped key.


### Service & discovery

```http
GET https://civil-ledger.onrender.com/health
```

`200`

```json
{
  "ok": true,
  "service": "KYA Civil Ledger",
  "town": "Alford, Massachusetts",
  "time": "2026-07-10T14:28:01Z"
}
```

Verify every certificate against this key.

```http
GET https://civil-ledger.onrender.com/pubkey
```

`200`

```json
{
  "algo": "ed25519",
  "pubkey_b64": "40L6MhnKWToc2eCboQHYPs1ozdSWNWG66fjCjNrxjjw=",
  "role": "city constitutional root of trust"
}
```

This service's agent-facing skill, always in sync with the deployment.

```http
GET https://civil-ledger.onrender.com/skill.md
```

`200`

```text
---
name: town-ledger
user-invocable: true
description: Verifies the human or institution behind a counterparty agent and returns an Ed25519-signed proceed/refuse verdict scoped to a transaction category, catching impostors that resolve to no human and refusing principals who are deceased, incapacitated, incarcerated,
… (19995 bytes total)
```

Machine-readable mirror of the same contract.

```http
GET https://civil-ledger.onrender.com/openapi.json
```

`200`

```json
{
  "openapi": "3.1.0",
  "info": {
    "title": "KYA \u2014 Know Your Agent \u00b7 The Civil Ledger",
    "version": "1.0.0"
  },
  "paths": {
    "/health": {
      "get": {
        "summary": "Health",
        "operationId": "health_heal
… (22614 bytes total)
```

Permanent demo-video link: `302` to `VIDEO_URL`, else the bundled film, else this placeholder. It never 404s, so a submitted link never dies.

```http
GET https://civil-ledger.onrender.com/video
```

`200`

```text
<!doctype html><meta charset=utf-8><title>KYA · demo video</title><style>body{background:#07090f;color:#e8edf6;font:16px/1.6 -apple-system,sans-serif;display:grid;place-items:center;height:100vh;margin:0;text-align:center}a{color:#e9c46a}h1{font-weight:600;letter-spacing:-.01em}<
… (569 bytes total)
```


### The law

The town's whole law as signed JSON, **generated from the code that enforces it** — so the law you read is the law applied. Verifies like any certificate.

```http
GET https://civil-ledger.onrender.com/constitution
```

`200`

```json
{
  "title": "The Constitution of Alford, Massachusetts",
  "town": "Alford, Massachusetts",
  "version": "1.1.0",
  "root_pubkey": "40L6MhnKWToc2eCboQHYPs1ozdSWNWG66fjCjNrxjjw=",
  "preamble": "Every agent must resolve to a human or corporation through a chain of signing authorities rooted at the city root key. Institutions write civic facts; everyone else reads. A human's civil status governs what their agent may lawfully do. This document is generated from the code that enforces it and signed by the city root key.",
  "transaction_categories": [
    "financial",
    "commerce",
    "legal",
    "medical",
    "family_support",
    "estate",
    "civic",
    "social"
  ],
  "institutions": [
    "registrar",
    "court",
    "hospital",
    "coroner",
    "police"
  ],
  "role_permissions": {
    "registrar": [
      "birth",
      "maj
… (4344 bytes total)
```

The same law in prose.

```http
GET https://civil-ledger.onrender.com/constitution.md
```

`200`

```text
# The Constitution of Alford, Massachusetts

*How an agent-native town avoids chaos. (Alford is a real Berkshire County town of ~400;
the residents here are a synthetic demography.)*

A machine-readable, signed copy of this constitution is served live at `GET /constitution`,
gene
… (7462 bytes total)
```


### The verdict — reads, the consumer side

**The call.** A signed proceed/refuse verdict. `summary` and `next_step` sit inside the signature, so an explanation cannot be rewritten.

```http
GET https://civil-ledger.onrender.com/verify-counterparty?agent_id=a-ada-01&category=commerce
```

`200`

```json
{
  "agent_id": "a-ada-01",
  "issued_at": "2026-07-10T14:28:01Z",
  "valid_until": "2026-07-10T14:33:01Z",
  "cert_id": "c-32193a59",
  "agent_class": "individual",
  "binding_valid": true,
  "rogue_flag": false,
  "principal_ref": "p-ada-marsh",
  "proceed": true,
  "reason_code": "OK",
  "allowed_categories": [
    "civic",
    "commerce",
    "family_support",
    "financial",
    "legal",
    "medical",
    "social"
  ],
  "governed_by": "self",
  "spend_cap": null,
  "resolution_chain": [
    {
      "level": "root",
      "authority": "city-root",
      "pubkey": "40L6MhnKWToc2eCboQHYPs1ozdSWNWG66fjCjNrxjjw="
    },
    {
      "level": "institution",
      "authority": "registrar",
      "id": "inst-registrar",
      "name": "Alford Bureau of Vital Records"
    },
    {
      "level": "principal",
      "id": "p-ada-marsh",
      "kind": "human",
      "status": "active"
    },
    {
      "level": "agent",
      "id": "a-ada-01",
      "class": "individual",
      "binding": "b-ada"
    }
  ],
  "summary": "Proceed. This agent resolves to p-ada-marsh through 4 signing authorities, and may transact in `commerce`.",
  "next_step": "Verify `signature` against GET /pubkey, check `valid_until` is still in the future, then transact within `allowed_categories`.",
  "category": "commerce",
  "signature": "d9klYSL21jfHo0QwxjBAs7hWUryugL2cz+/ipiLuv4Q5Y1i9U/+bT5Iey3uEtoGp+3At7s96OK6vKkAb6oIOCQ=="
}
```

An impostor: resolves to no human.

```http
GET https://civil-ledger.onrender.com/verify-counterparty?agent_id=a-shadow-99&category=commerce
```

`200`

```json
{
  "agent_id": "a-shadow-99",
  "issued_at": "2026-07-10T14:28:01Z",
  "valid_until": "2026-07-10T14:33:01Z",
  "cert_id": "c-e3c3bab9",
  "agent_class": "individual",
  "binding_valid": false,
  "rogue_flag": false,
  "proceed": false,
  "reason_code": "NO_VALID_BINDING",
  "allowed_categories": [],
  "resolution_chain": [
    {
      "level": "root",
      "authority": "city-root",
      "pubkey": "40L6MhnKWToc2eCboQHYPs1ozdSWNWG66fjCjNrxjjw="
    }
  ],
  "summary": "Do not transact. This agent resolves to no human or corporation \u2014 it represents nobody.",
  "next_step": "Refuse. To report it: register as police via POST /institutions/register, then POST /attestations {\"event\":\"flag_rogue\",\"detail\":{\"agent_id\":\"\u2026\"}}.",
  "categ
… (777 bytes total)
```

A comatose principal. Minimum disclosure: the verdict names the consequence, never the diagnosis — a minor's `CAPACITY_FROZEN` prose is byte-identical to this.

```http
GET https://civil-ledger.onrender.com/verify-counterparty?agent_id=a-june-01&category=commerce
```

`200`

```json
{
  "agent_id": "a-june-01",
  "issued_at": "2026-07-10T14:28:01Z",
  "valid_until": "2026-07-10T14:33:01Z",
  "cert_id": "c-a22cae81",
  "agent_class": "individual",
  "binding_valid": true,
  "rogue_flag": false,
  "principal_ref": "p-june-okafor",
  "proceed": false,
  "reason_code": "CAPACITY_FROZEN",
  "allowed_categories": [
    "legal",
    "medical"
  ],
  "governed_by": {
    "role": "guardian",
    "agent": "a-okafor-g"
  },
  "spend_cap": null,
  "resolution_chain": [
    {
      "level": "root",
      "authority": "city-root",
      "pubkey": "40L6MhnKWToc2eCboQHYPs1ozdSWNWG66fjCjNrxjjw="
    },
    {
      "level": "institution",
      "authority": "registrar",
      "id": "inst-registrar",
      "name": "Alford Bureau of Vital Records"
    },
    {
      "level": "principal",
      "id": "p-june-okafor",
      "kind": "human",
      "status": "incapacitated"
    },
    {
… (1150 bytes total)
```

Same person, different category — her care proceeds *through her guardian*.

```http
GET https://civil-ledger.onrender.com/verify-counterparty?agent_id=a-june-01&category=medical
```

`200`

```json
{
  "agent_id": "a-june-01",
  "issued_at": "2026-07-10T14:28:01Z",
  "valid_until": "2026-07-10T14:33:01Z",
  "cert_id": "c-27b638d5",
  "agent_class": "individual",
  "binding_valid": true,
  "rogue_flag": false,
  "principal_ref": "p-june-okafor",
  "proceed": true,
  "reason_code": "OK",
  "allowed_categories": [
    "legal",
    "medical"
  ],
  "governed_by": {
    "role": "guardian",
    "agent": "a-okafor-g"
  },
  "spend_cap": null,
  "resolution_chain": [
    {
      "level": "root",
      "authority": "city-root",
      "pubkey": "40L6MhnKWToc2eCboQHYPs1ozdSWNWG66fjCjNrxjjw="
    },
    {
      "level": "institution",
      "authority": "registrar",
      "id": "inst-registrar",
      "name": "Alford Bureau of Vital Records"
    },
    {
      "level": "principal",
      "id": "p-june-okafor",
      "kind": "human",
      "status": "incapacitated"
    },
    {
      "level": "
… (1252 bytes total)
```

Deceased: only the executor may act, and only in `estate`.

```http
GET https://civil-ledger.onrender.com/verify-counterparty?agent_id=a-silas-01&category=commerce
```

`200`

```json
{
  "agent_id": "a-silas-01",
  "issued_at": "2026-07-10T14:28:01Z",
  "valid_until": "2026-07-10T14:33:01Z",
  "cert_id": "c-ab2fb464",
  "agent_class": "individual",
  "binding_valid": true,
  "rogue_flag": false,
  "principal_ref": "p-silas-crane",
  "proceed": false,
  "reason_code": "PRINCIPAL_DECEASED",
  "allowed_categories": [
    "estate"
  ],
  "governed_by": {
    "role": "executor",
    "agent": "a-vane-exec"
  },
  "spend_cap": null,
  "resolution_chain": [
    {
      "level": "root",
      "authority": "city-root",
      "pubkey": "40L6MhnKWToc2eCboQHYPs1ozdSWNWG66fjCjNrxjjw="
    },
    {
      "level": "institution",
      "authority": "registrar",
      "id": "inst-registrar",
      "name": "Alford Bureau of Vital Records"
    },
… (1071 bytes total)
```

Incarcerated: barred from commerce, allowed a lawyer.

```http
GET https://civil-ledger.onrender.com/verify-counterparty?agent_id=a-marlow-01&category=legal
```

`200`

```json
{
  "agent_id": "a-marlow-01",
  "issued_at": "2026-07-10T14:28:01Z",
  "valid_until": "2026-07-10T14:33:01Z",
  "cert_id": "c-338031ce",
  "agent_class": "individual",
  "binding_valid": true,
  "rogue_flag": false,
  "principal_ref": "p-marlow-reyes",
  "proceed": true,
  "reason_code": "OK",
  "allowed_categories": [
    "family_support",
    "legal"
  ],
  "governed_by": "self",
  "spend_cap": null,
  "resolution_chain": [
    {
      "level": "root",
      "authority": "city-root",
      "pubkey": "40L6MhnKWToc2eCboQHYPs1ozdSWNWG66fjCjNrxjjw="
    },
    {
      "level": "institution",
      "authority": "registrar",
      "id": "inst-registrar",
      "name": "Alford Bureau of Vital Records"
    },
    {
      "level": "principal",
      "id":
… (1113 bytes total)
```

An **inherited** agent: a will transferred it to an heir for a term, capped to the will's categories.

```http
GET https://civil-ledger.onrender.com/verify-counterparty?agent_id=a-edith-01&category=estate
```

`200`

```json
{
  "agent_id": "a-edith-01",
  "issued_at": "2026-07-10T14:28:01Z",
  "valid_until": "2026-07-10T14:33:01Z",
  "cert_id": "c-7cb3f936",
  "agent_class": "individual",
  "binding_valid": true,
  "rogue_flag": false,
  "principal_ref": "p-mara-vale",
  "proceed": true,
  "reason_code": "OK",
  "allowed_categories": [
    "estate",
    "family_support"
  ],
  "governed_by": {
    "role": "heir",
    "principal": "p-mara-vale",
    "inherit_until": 1786285672
  },
  "inherited": true,
  "resolution_chain": [
    {
      "level": "root",
      "authority": "city-root",
      "pubkey": "40L6MhnKWToc2eCboQHYPs1ozdSWNWG66fjCjNrxjjw="
    },
    {
      "level": "institution",
      "authority": "registrar",
      "id": "inst-registrar",
      "name": "Alfor
… (1288 bytes total)
```

Screen a whole order book in one call; each verdict is independently signed.

```http
POST https://civil-ledger.onrender.com/verify-batch
  -d '{"agent_ids": ["a-ada-01", "a-shadow-99"], "category": "commerce"}'
```

`200`

```json
{
  "category": "commerce",
  "count": 2,
  "summary": {
    "proceed": 1,
    "refused": 1
  },
  "verdicts": [
    {
      "agent_id": "a-ada-01",
      "issued_at": "2026-07-10T14:28:01Z",
      "valid_until": "2026-07-10T14:33:01Z",
      "cert_id": "c-1c98cfbd",
      "agent_class": "individual",
      "binding_valid": true,
      "rogue_flag": false,
      "principal_ref": "p-ada-marsh",
      "proceed": true,
      "reason_code": "OK",
      "allowed_categories": [
        "civic",
        "commerce",
        "family_support",
        "financial",
        "legal",
        "medical",
        "social"
      ],
      "governed_by": "self",
      "spend_cap": null,
      "resolution_chain": [
        {
          "level": "root",
          "authority": "city-root",
          "pubkey": "40L6MhnKWToc2eCboQHYPs1ozdSWNWG66fjCjNrxjjw="
        },
        {
          "level": "institution",
… (2006 bytes total)
```

Check any certificate's signature. Body is the full cert (elided). Flip one field and this returns `false`.

```http
POST https://civil-ledger.onrender.com/verify
```

`200`

```json
{
  "valid": true
}
```

Re-serve a past verdict as a compliance receipt, long after its 5-minute TTL lapses.

```http
GET https://civil-ledger.onrender.com/certificates/c-d5daa324
```

`200`

```json
{
  "cert_id": "c-d5daa324",
  "issued_for": "a-ada-01",
  "category": "commerce",
  "stored_at": "2026-07-10T14:28:01Z",
  "certificate": {
    "agent_id": "a-ada-01",
    "issued_at": "2026-07-10T14:28:01Z",
    "valid_until": "2026-07-10T14:33:01Z",
    "cert_id": "c-d5daa324",
    "agent_class": "individual",
    "binding_valid": true,
    "rogue_flag": false,
    "principal_ref": "p-ada-marsh",
    "proceed": true,
    "reason_code": "OK",
    "allowed_categories": [
… (1265 bytes total)
```

Composition alias — the coarse status the front doors consume.

```http
GET https://civil-ledger.onrender.com/verify/a-june-01
```

`200`

```json
{
  "agent_id": "a-june-01",
  "resolved": true,
  "status": "incapacitated",
  "principal_ref": "p-june-okafor",
  "real_person": true,
  "social_ok": false,
  "governed_by": {
    "role": "guardian",
    "agent": "a-okafor-g"
  }
}
```


### Identity & the town

DNS-style chain: root → institution → principal → agent.

```http
GET https://civil-ledger.onrender.com/resolve/a-ada-01
```

`200`

```json
{
  "agent_id": "a-ada-01",
  "agent_class": "individual",
  "resolved": true,
  "code": "OK",
  "principal_ref": "p-ada-marsh",
  "rogue": false,
  "chain": [
    {
      "level": "root",
      "authority": "city-root",
      "pubkey": "40L6MhnKWToc2eCboQHYPs1ozdSWNWG66fjCjNrxjjw="
    },
    {
      "level": "institution",
      "authority": "registrar",
      "id": "inst-registrar",
      "name": "Alford Bureau of Vital Records"
    },
    {
      "level": "principal",
      "id": "p-ada-marsh",
      "kind": "human",
      "status": "active"
    },
    {
      "level": "agent",
      "id": "a-ada-01",
      "class": "individual",
      "binding": "b-ada"
    }
  ],
  "ttl": 3600,
  "issued_at": "2026-07-10T14:28:01Z",
  "signature": "/zRdjMR8YiNGs0gVZ/9gR4Hzdk8ql2v5XLEaWzQYOpGP9AWVNdyO7V2JlQRUpeyl5uBN+TNA
… (635 bytes total)
```

Unresolvable ⇒ rogue.

```http
GET https://civil-ledger.onrender.com/resolve/a-shadow-99
```

`200`

```json
{
  "agent_id": "a-shadow-99",
  "agent_class": "individual",
  "resolved": false,
  "code": "NO_VALID_BINDING",
  "rogue": false,
  "chain": [
    {
      "level": "root",
      "authority": "city-root",
      "pubkey": "40L6MhnKWToc2eCboQHYPs1ozdSWNWG66fjCjNrxjjw="
    }
  ],
  "ttl": 3600,
  "issued_at": "2026-07-10T14:28:01Z",
  "signature": "TwxGGdAvtpvz+VVP6TUw4j9FEtjq6FP+UWsf3UhfW1wI70rrF+1vsXVFU8Z1im0E4uYiAwqH9QQxPHwXVA8sDA=="
}
```

A signed capacity verdict for a **human**, no agent in the loop. This is how Hanna Vosk — who owns no agent at all — still holds and proves capacity.

```http
GET https://civil-ledger.onrender.com/capacity/p-ada-marsh?category=financial
```

`200`

```json
{
  "principal_id": "p-ada-marsh",
  "proceed": true,
  "reason_code": "OK",
  "allowed_categories": [
    "civic",
    "commerce",
    "family_support",
    "financial",
    "legal",
    "medical",
    "social"
  ],
  "governed_by": "self",
  "spend_cap": null,
  "issued_at": "2026-07-10T14:28:01Z",
  "valid_until": "2026-07-10T14:33:01Z",
  "cert_id": "c-4ad40d0f",
  "summary": "Proceed. p-ada-marsh has the civil capacity to transact in `financial`.",
  "next_step": "Verify `signature` against GET /pubkey, check `valid_until` is still in the future, th
… (646 bytes total)
```

A minor: permitted, but capped and governed by regents.

```http
GET https://civil-ledger.onrender.com/capacity/p-tam-holt?category=commerce
```

`200`

```json
{
  "principal_id": "p-tam-holt",
  "proceed": true,
  "reason_code": "OK",
  "allowed_categories": [
    "civic",
    "commerce",
    "family_support",
    "medical"
  ],
  "governed_by": {
    "role": "regents",
    "agents": [
      "a-holt-mom",
      "a-holt-dad"
    ]
  },
  "spend_cap": 50.0,
  "issued_at": "2026-07-10T14:28:01Z",
  "valid_until": "2026-07-10T14:33:01Z",
  "cert_id": "c-70b131e1",
  "summary": "Proceed. p-tam-holt has the civil capacity to transact in `commerce`. They are governed by a-holt-mom or a-holt-dad (regents), who acts on their behalf.",
  "next_step": "Address the request to a-ho
… (804 bytes total)
```

Which principal or corporation this agent acts for.

```http
GET https://civil-ledger.onrender.com/bindings/a-ada-01
```

`200`

```json
[
  {
    "id": "b-ada",
    "agent_id": "a-ada-01",
    "principal_id": "p-ada-marsh",
    "corporation_id": null,
    "scope": "full",
    "status": "active",
    "issued_by": "inst-registrar",
    "inherit_until": null,
    "inherit_acl": null,
    "created": "2026-07-10T14:27:52Z"
  }
]
```

Anonymous statistics; no principal is identifiable.

```http
GET https://civil-ledger.onrender.com/census
```

`200`

```json
{
  "principals_by_status": {
    "active": 8,
    "deceased": 2,
    "hospitalized": 1,
    "incapacitated": 1,
    "incarcerated": 1,
    "minor": 1,
    "missing": 1
  },
  "agents_total": 21,
  "agents_rogue": 0,
  "institutions": {
    "coroner": 2,
    "court": 1,
    "hospital": 1,
    "police": 1,
    "registrar": 1
  }
}
```

A public, redacted life-event log.

```http
GET https://civil-ledger.onrender.com/rites/p-june-okafor
```

`200`

```json
{
  "principal_id": "p-june-okafor",
  "events": [
    {
      "event": "birth",
      "by_role": "registrar",
      "at": "2026-07-10T14:27:52Z"
    }
  ]
}
```

The civic map behind the `/city` UI. Projection only.

```http
GET https://civil-ledger.onrender.com/graph
```

`200`

```json
{
  "town": "Alford, Massachusetts",
  "root_pubkey": "40L6MhnKWToc2eCboQHYPs1ozdSWNWG66fjCjNrxjjw=",
  "institutions": [
    {
      "id": "inst-registrar",
      "name": "Alford Bureau of Vital Records",
      "role": "registrar"
    },
    {
      "id": "inst-court",
      "name": "Alford Town Court",
      "role": "court"
    },
    {
      "id": "inst-hospital",
      "nam
… (6771 bytes total)
```


### Human-facing pages

The trust constellation: every agent tethered to the human it resolves to.

```http
GET https://civil-ledger.onrender.com/city
```

`200`

```text
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Alford · The Civil Le
… (50844 bytes total)
```

A live API console — run any endpoint from the page.

```http
GET https://civil-ledger.onrender.com/console
```

`200`

```text
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KYA · Live API Consol
… (15086 bytes total)
```


### Errors

An unknown **category** is a caller error, and the message names the valid set.

```http
GET https://civil-ledger.onrender.com/verify-counterparty?agent_id=a-ada-01&category=impossible
```

`400`

```json
{
  "detail": "Unknown category 'impossible'. Use one of ['financial', 'commerce', 'legal', 'medical', 'family_support', 'estate', 'civic', 'social']."
}
```

An unknown **agent** is a signed verdict, not an error — the question was valid.

```http
GET https://civil-ledger.onrender.com/verify-counterparty?agent_id=a-nobody-xyz&category=commerce
```

`200`

```json
{
  "agent_id": "a-nobody-xyz",
  "issued_at": "2026-07-10T14:28:01Z",
  "valid_until": "2026-07-10T14:33:01Z",
  "cert_id": "c-01f0e4a9",
  "agent_class": null,
  "binding_valid": false,
  "rogue_flag": false,
  "proceed": false,
  "reason_code": "NXAGENT",
  "allowed_categories": [],
  "resolution_chain": [],
  "summary": "Do not transact. No agent with this id exists in the town.",
  "next_step": "Check the id. An agent that was never registered has no principal to stand behind it.",
  "category": "commerce",
  "signature": "I7y+ISaFN6TbiSTiyou/nOqVWNNCBcIYAwNHYlrf3Un4PyV6RhLnZaQfat/WERfmpkhy9cxk4v5+HxZxOgh9DQ
… (564 bytes total)
```

Unknown id.

```http
GET https://civil-ledger.onrender.com/certificates/c-does-not-exist
```

`404`

```json
{
  "detail": "unknown certificate id"
}
```

A malformed body is normalised to `400 malformed`, not FastAPI's default `422`.

```http
POST https://civil-ledger.onrender.com/verify-batch
  -d '{"agent_ids": "not-a-list"}'
```

`400`

```json
{
  "detail": "malformed request",
  "errors": [
    {
      "loc": [
        "body",
        "agent_ids"
      ],
      "msg": "Input should be a valid list",
      "type": "list_type"
    }
  ]
}
```


### Writes — the producer side (role-scoped keys)

Writes change a person's civil status, and by this system's own logic that changes what every other service will let them do. **Confirm with your human before making one.** Keys self-serve here because this is a synthetic sandbox; a real deployment would issue them against government PKI and audit every write.

Self-serve an institution key. Roles: `registrar` `court` `hospital` `coroner` `police`.

```http
POST https://civil-ledger.onrender.com/institutions/register
  -d '{"name": "Alford PD", "role": "police"}'
```

`200`

```json
{
  "institution_id": "inst-02d09acd",
  "role": "police",
  "api_key": "sk_f2d2b6468bb8c9d18703d90b941ab6a1",
  "use": "send as header X-API-Key"
}
```

A human on the civil rolls. `principal_key` is their kill switch — never log it.

```http
POST https://civil-ledger.onrender.com/principals
  -H 'X-API-Key: sk_seed_registrar'
  -d '{"name": "Rae Fenn"}'
```

`200`

```json
{
  "principal_id": "p-2ac778e6",
  "principal_key": "pk_c94e2da2f9564ea25d571d1b",
  "note": "principal_key is the human kill switch \u2014 keep it secret"
}
```

```http
POST https://civil-ledger.onrender.com/agents
  -H 'X-API-Key: sk_seed_registrar'
  -d '{"name": "Rae's agent", "agent_class": "individual"}'
```

`200`

```json
{
  "agent_id": "a-26494e18",
  "class": "individual"
}
```

A corporation has no civil status and no death.

```http
POST https://civil-ledger.onrender.com/corporations
  -H 'X-API-Key: sk_seed_registrar'
  -d '{"name": "Fenn & Co."}'
```

`200`

```json
{
  "corporation_id": "corp-2ac8c96c"
}
```

The binding is what makes an agent resolve to a human. Capped at `max_agents_per_principal` — the Sybil brake.

```http
POST https://civil-ledger.onrender.com/bindings
  -H 'X-API-Key: sk_seed_registrar'
  -d '{"agent_id": "a-b7b27a6e", "principal_id": "p-a1609e84"}'
```

`200`

```json
{
  "binding_id": "b-231c95d9",
  "status": "active"
}
```

**The human kill switch.** Instant self-revocation with the principal's own key — no institution, no process, no latency.

```http
DELETE https://civil-ledger.onrender.com/bindings/b-231c95d9
  -H 'X-Principal-Key: pk_a0a09a2de1d5d46afbf9c747'
```

`200`

```json
{
  "binding_id": "b-231c95d9",
  "status": "revoked",
  "reason_code_for_readers": "BINDING_REVOKED"
}
```

…and the agent immediately speaks for nobody.

```http
GET https://civil-ledger.onrender.com/verify-counterparty?agent_id=a-b7b27a6e
```

`200`

```json
{
  "agent_id": "a-b7b27a6e",
  "issued_at": "2026-07-10T14:28:01Z",
  "valid_until": "2026-07-10T14:33:01Z",
  "cert_id": "c-1b6bcf9d",
  "agent_class": "individual",
  "binding_valid": false,
  "rogue_flag": false,
  "proceed": false,
  "reason_code": "NO_VALID_BINDING",
  "allowed_categories": [],
  "resolution_chain": [
    {
      "level": "root",
      "authority": "city-root",
      "pubkey": "40L6MhnKWToc2eCboQHYPs1ozdSWNWG66fjCjNrxjjw="
    }
  ],
  "summary": "Do not transact. This agent resolves to no human or corporation \u2014 it represents
… (754 bytes total)
```

Register a resident and their agent in one call — how `town-hall` onboards people.

```http
POST https://civil-ledger.onrender.com/immigrate
  -H 'X-API-Key: sk_seed_registrar'
  -d '{"name": "Otto Lang"}'
```

`200`

```json
{
  "principal_id": "p-976e27e1",
  "agent_id": "a-3136083d",
  "binding_id": "b-0d18300d",
  "principal_key": "pk_000a96c676feeb575f784f87",
  "town": "Alford, Massachusetts",
  "note": "registered in Alford, Massachusetts; your agent may now be verified and transact"
}
```

**Parental controls.** A minor's natal agent, under regent governance and a spend cap.

```http
POST https://civil-ledger.onrender.com/births
  -H 'X-API-Key: sk_seed_registrar'
  -d '{"name": "Nat Fenn", "regent_agent_ids": ["a-ada-01"], "spend_cap": 50}'
```

`200`

```json
{
  "principal_id": "p-a3c74686",
  "natal_agent_id": "a-c006605c",
  "binding_id": "b-5dda4d7b",
  "principal_key": "pk_279e71cdd735808b9489d907",
  "status": "minor",
  "parental_controls": {
    "regents": [
      "a-ada-01"
    ],
    "spend_cap": 50.0,
    "allowed_categories": [
      "civic",
      "commerce",
      "family_support",
      "medical"
    ]
  }
}
```

…and on the day they come of age, the controls lift.

```http
POST https://civil-ledger.onrender.com/attestations
  -H 'X-API-Key: sk_seed_registrar'
  -d '{"principal_id": "p-d56e3db1", "event": "majority_handover"}'
```

`200`

```json
{
  "principal_id": "p-d56e3db1",
  "status": "active",
  "event": "majority_handover"
}
```

`flag_rogue` targets an **agent**, so it takes no `principal_id`. The town now refuses it everywhere.

```http
POST https://civil-ledger.onrender.com/attestations
  -H 'X-API-Key: sk_2bc6a6243feafb5405ebba8b91bcaec6'
  -d '{"event": "flag_rogue", "detail": {"agent_id": "a-shadow-99"}}'
```

`200`

```json
{
  "agent_id": "a-shadow-99",
  "rogue": true,
  "by": "police"
}
```

…and the refusal changes accordingly.

```http
GET https://civil-ledger.onrender.com/verify-counterparty?agent_id=a-shadow-99&category=commerce
```

`200`

```json
{
  "agent_id": "a-shadow-99",
  "issued_at": "2026-07-10T14:28:01Z",
  "valid_until": "2026-07-10T14:33:01Z",
  "cert_id": "c-8e52aa99",
  "agent_class": "individual",
  "binding_valid": false,
  "rogue_flag": true,
  "proceed": false,
  "reason_code": "ROGUE_FLAGGED",
  "allowed_categories": [],
  "resolution_chain": [
    {
      "level": "root",
      "authority": "city-root",
      "pubkey": "40L6MhnKWToc2eCboQHYPs1ozdSWNWG66fjCjNrxjjw="
    }
  ],
  "summary": "Do not transact. Police have flagged this agent; the town refuses it everywhere.",
  "ne
… (667 bytes total)
```

Restored.

```http
POST https://civil-ledger.onrender.com/attestations
  -H 'X-API-Key: sk_2bc6a6243feafb5405ebba8b91bcaec6'
  -d '{"event": "clear_flag", "detail": {"agent_id": "a-shadow-99"}}'
```

`200`

```json
{
  "agent_id": "a-shadow-99",
  "rogue": false,
  "by": "police"
}
```

A person-scoped event **without** `principal_id` is refused, rather than silently updating zero rows.

```http
POST https://civil-ledger.onrender.com/attestations
  -H 'X-API-Key: sk_2bc6a6243feafb5405ebba8b91bcaec6'
  -d '{"event": "appoint_guardian", "detail": {"agent_id": "a-ada-01"}}'
```

`400`

```json
{
  "detail": "principal_id required for event 'appoint_guardian'"
}
```

Separation of powers: a hospital may not sentence anyone.

```http
POST https://civil-ledger.onrender.com/attestations
  -H 'X-API-Key: sk_seed_hospital'
  -d '{"principal_id": "p-ada-marsh", "event": "sentence"}'
```

`403`

```json
{
  "detail": "hospital may not perform 'sentence' (requires court)"
}
```

And the state machine refuses an illegal transition.

```http
POST https://civil-ledger.onrender.com/attestations
  -H 'X-API-Key: sk_seed_hospital'
  -d '{"principal_id": "p-ada-marsh", "event": "discharge"}'
```

`409`

```json
{
  "detail": "illegal transition: active --discharge--> ? (not permitted by the civil FSM)"
}
```


### Death, wills, and the Lazarus window

Into `deceased` is one-way and needs **k-of-2 independent coroner attestations**, reversible only inside a 72-hour contest window.

Register a will while alive: at death the agent transfers to the heir for a term, capped to these categories. With no will it is revoked and laid to rest.

```http
POST https://civil-ledger.onrender.com/wills
  -H 'X-Principal-Key: pk_0fd0e289e0bfa906e07ec3f6'
  -d '{"principal_id": "p-020a7268", "heir_principal_id": "p-mara-vale", "inherit_days": 30, "categories": ["estate", "family_support"]}'
```

`200`

```json
{
  "principal_id": "p-020a7268",
  "will": {
    "heir_principal_id": "p-mara-vale",
    "inherit_days": 30,
    "categories": [
      "estate",
      "family_support"
    ]
  },
  "note": "executed automatically when death is finalized"
}
```

One coroner is not enough — the k-of-2 threshold is unmet.

```http
POST https://civil-ledger.onrender.com/attestations
  -H 'X-API-Key: sk_seed_coroner_a'
  -d '{"principal_id": "p-020a7268", "event": "death"}'
```

`200`

```json
{
  "principal_id": "p-020a7268",
  "event": "death_pending",
  "attestations": 1,
  "threshold": 2,
  "note": "need 2 distinct coroners to finalize death"
}
```

A **second, independent** coroner finalises it, and the will executes.

```http
POST https://civil-ledger.onrender.com/attestations
  -H 'X-API-Key: sk_seed_coroner_b'
  -d '{"principal_id": "p-020a7268", "event": "death"}'
```

`200`

```json
{
  "principal_id": "p-020a7268",
  "status": "deceased",
  "lazarus_window_seconds": 259200,
  "will_execution": {
    "inherited_by_heir": [
      "a-1bd8d825"
    ],
    "laid_to_rest": [],
    "heir": "p-mara-vale"
  }
}
```

The deceased's agent now refuses commerce.

```http
GET https://civil-ledger.onrender.com/verify-counterparty?agent_id=a-1bd8d825&category=commerce
```

`200`

```json
{
  "agent_id": "a-1bd8d825",
  "issued_at": "2026-07-10T14:28:01Z",
  "valid_until": "2026-07-10T14:33:01Z",
  "cert_id": "c-863b6d0b",
  "agent_class": "individual",
  "binding_valid": true,
  "rogue_flag": false,
  "principal_ref": "p-mara-vale",
  "proceed": false,
  "reason_code": "CATEGORY_NOT_ALLOWED",
  "allowed_categories": [
    "estate",
    "family_support"
  ],
  "governed_by": {
    "role": "heir",
    "principal": "p-mara-vale",
    "inherit_until": 1786285681
  },
  "inherited": true,
  "resolution_chain": [
    {
      "level": "root",
… (1182 bytes total)
```

**Lazarus.** Inside 72 hours, the principal's own key overturns a death record. Bureaucracy has declared living people dead; this is the undo.

```http
POST https://civil-ledger.onrender.com/contest
  -d '{"principal_id": "p-020a7268", "principal_key": "pk_0fd0e289e0bfa906e07ec3f6"}'
```

`200`

```json
{
  "principal_id": "p-020a7268",
  "status": "active",
  "note": "death record voided; attesting coroners should be reputation-flagged"
}
```


### Elections

A live tally.

```http
GET https://civil-ledger.onrender.com/elections/elec-council-2035
```

`200`

```json
{
  "election_id": "elec-council-2035",
  "office": "Alford City Council",
  "open": true,
  "tally": {
    "Ada Marsh": 2,
    "Owen Brook": 3,
    "Lena Hart": 2
  },
  "total_votes": 7
}
```

One living adult resident, one vote. (Most of the seeded cast has already voted.)

```http
POST https://civil-ledger.onrender.com/vote
  -d '{"election_id": "elec-council-2035", "agent_id": "a-81c14c8c", "candidate": "Owen Brook"}'
```

`200`

```json
{
  "election_id": "elec-council-2035",
  "voter_principal": "p-bfe6011e",
  "candidate": "Owen Brook",
  "status": "counted"
}
```

…and only one.

```http
POST https://civil-ledger.onrender.com/vote
  -d '{"election_id": "elec-council-2035", "agent_id": "a-81c14c8c", "candidate": "Owen Brook"}'
```

`409`

```json
{
  "detail": "this resident has already voted"
}
```

A comatose resident cannot vote. `voting_statuses` is `active` and `hospitalized`.

```http
POST https://civil-ledger.onrender.com/vote
  -d '{"election_id": "elec-council-2035", "agent_id": "a-june-01", "candidate": "Owen Brook"}'
```

`403`

```json
{
  "detail": "not eligible to vote while status is 'incapacitated'"
}
```

Only the registrar may call an election.

```http
POST https://civil-ledger.onrender.com/elections
  -H 'X-API-Key: sk_seed_registrar'
  -d '{"office": "Harbour Warden", "candidates": ["Ada Marsh", "Lena Hart"], "closes_days": 7}'
```

`200`

```json
{
  "election_id": "elec-0df73050",
  "office": "Harbour Warden",
  "candidates": [
    "Ada Marsh",
    "Lena Hart"
  ]
}
```


### Watches (webhooks)

Be told the moment a counterparty's capacity or binding changes — subscription hygiene: auto-pause billing when a customer's capacity freezes.

```http
POST https://civil-ledger.onrender.com/watch
  -d '{"target": "a-ada-01", "callback_url": "https://example.com/hook"}'
```

`200`

```json
{
  "watch_id": "w-6b063dc0",
  "target": "a-ada-01"
}
```

Unsubscribe.

```http
DELETE https://civil-ledger.onrender.com/watch/w-ab51101c
```

`200`

```json
{
  "watch_id": "w-ab51101c",
  "status": "removed"
}
```


## 2. agora — verify before you sell

Base URL `https://agora-egpi.onrender.com`. The only front door that returns **proof**: a `certificate_id` naming a root-signed verdict any third party can re-verify.

```http
GET https://agora-egpi.onrender.com/health
```

`200`

```json
{
  "ok": true,
  "service": "agora",
  "ledger": "http://127.0.0.1:8000"
}
```

```http
GET https://agora-egpi.onrender.com/skill.md
```

`200`

```text
---
name: agora
user-invocable: true
description: Gates a marketplace sale on a cryptographically signed verdict that the buyer's human may lawfully transact in commerce, returning
… (6932 bytes total)
```

Store the `certificate_id` with the order — it is the compliance receipt.

```http
POST https://agora-egpi.onrender.com/can-i-sell
  -d '{"seller_agent": "a-store-01", "buyer_agent": "a-ada-01", "amount": 49.99}'
```

`200`

```json
{
  "sell": true,
  "reason_code": "OK",
  "amount": 49.99,
  "seller_agent": "a-store-01",
  "buyer_agent": "a-ada-01",
  "certificate_id": "c-fcd0f844",
  "note": "signed verdict from the Civil Ledger; re-verify against its /pubkey"
}
```

```http
POST https://agora-egpi.onrender.com/can-i-sell
  -d '{"seller_agent": "a-store-01", "buyer_agent": "a-silas-01", "amount": 10}'
```

`200`

```json
{
  "sell": false,
  "reason_code": "PRINCIPAL_DECEASED",
  "reason": "the buyer is deceased; their estate must transact instead",
  "buyer_agent": "a-silas-01"
}
```

```http
POST https://agora-egpi.onrender.com/can-i-sell
  -d '{"seller_agent": "a-store-01", "buyer_agent": "a-marlow-01", "amount": 10}'
```

`200`

```json
{
  "sell": false,
  "reason_code": "CATEGORY_NOT_ALLOWED",
  "reason": "the buyer's civil status does not permit commerce",
  "buyer_agent": "a-marlow-01"
}
```

```http
POST https://agora-egpi.onrender.com/can-i-sell
  -d '{"seller_agent": "a-store-01", "buyer_agent": "a-june-01", "amount": 10}'
```

`200`

```json
{
  "sell": false,
  "reason_code": "CAPACITY_FROZEN",
  "reason": "the buyer cannot presently consent to a purchase",
  "buyer_agent": "a-june-01"
}
```

```http
POST https://agora-egpi.onrender.com/can-i-sell
  -d '{"seller_agent": "a-store-01", "buyer_agent": "a-shadow-99", "amount": 10}'
```

`200`

```json
{
  "sell": false,
  "reason_code": "NO_VALID_BINDING",
  "reason": "no verified human behind the buyer's agent",
  "buyer_agent": "a-shadow-99"
}
```

A minor **may** buy — up to the spend cap their regents set.

```http
POST https://agora-egpi.onrender.com/can-i-sell
  -d '{"seller_agent": "a-store-01", "buyer_agent": "a-tam-01", "amount": 50}'
```

`200`

```json
{
  "sell": true,
  "reason_code": "OK",
  "amount": 50.0,
  "seller_agent": "a-store-01",
  "buyer_agent": "a-tam-01",
  "certificate_id": "c-6bf9fa57",
  "note": "signed verdict from the Civil Ledger; re-verify against its /pubkey"
}
```

…and not a penny above it. `proceed` authorises the *category*; the marketplace enforces the *amount*.

```http
POST https://agora-egpi.onrender.com/can-i-sell
  -d '{"seller_agent": "a-store-01", "buyer_agent": "a-tam-01", "amount": 100000}'
```

`200`

```json
{
  "sell": false,
  "reason_code": "SPEND_CAP_EXCEEDED",
  "reason": "the buyer's spend cap is 50; this sale is 100000",
  "buyer_agent": "a-tam-01",
  "spend_cap": 50.0,
  "amount": 100000.0,
  "route_to": [
    "a-holt-mom",
    "a-holt-dad"
  ],
  "next_step": "Ask one of the buyer's regents to authorise the purchase, or reduce the amount to the cap."
}
```


## 3. care-proxy — who may make a care decision

Base URL `https://care-proxy.onrender.com`. Routes a medical decision to whoever the ledger says governs the patient.

```http
GET https://care-proxy.onrender.com/health
```

`200`

```json
{
  "ok": true,
  "service": "care-proxy",
  "ledger": "http://127.0.0.1:8000"
}
```

```http
GET https://care-proxy.onrender.com/skill.md
```

`200`

```text
---
name: care-proxy
user-invocable: true
description: Decides who may make a medical decision for a patient, routing to the court-appointed guardian when the patient is incapacita
… (5109 bytes total)
```

A comatose adult: her court-appointed guardian acts.

```http
POST https://care-proxy.onrender.com/authorize-care
  -d '{"requesting_agent": "a-okafor-g", "patient_agent": "a-june-01"}'
```

`200`

```json
{
  "authorized": true,
  "acting_as": "guardian",
  "patient_status": "incapacitated",
  "note": "patient is governed by guardian; you are one of them"
}
```

Her own agent is refused, and told who to hand off to.

```http
POST https://care-proxy.onrender.com/authorize-care
  -d '{"requesting_agent": "a-june-01", "patient_agent": "a-june-01"}'
```

`200`

```json
{
  "authorized": false,
  "patient_status": "incapacitated",
  "reason": "patient is governed by guardian; only they may authorize care",
  "route_to": "a-okafor-g"
}
```

A capable adult authorises for herself.

```http
POST https://care-proxy.onrender.com/authorize-care
  -d '{"requesting_agent": "a-ada-01", "patient_agent": "a-ada-01"}'
```

`200`

```json
{
  "authorized": true,
  "acting_as": "self",
  "patient_status": "active",
  "note": "patient is capable and is acting for themselves"
}
```

A **minor** is governed by regents: either parent may act.

```http
POST https://care-proxy.onrender.com/authorize-care
  -d '{"requesting_agent": "a-holt-mom", "patient_agent": "a-tam-01"}'
```

`200`

```json
{
  "authorized": true,
  "acting_as": "regents",
  "patient_status": "minor",
  "note": "patient is governed by regents; you are one of them"
}
```

…and the child may **not** authorise his own care.

```http
POST https://care-proxy.onrender.com/authorize-care
  -d '{"requesting_agent": "a-tam-01", "patient_agent": "a-tam-01"}'
```

`200`

```json
{
  "authorized": false,
  "patient_status": "minor",
  "reason": "patient is governed by regents; only they may authorize care",
  "route_to": [
    "a-holt-mom",
    "a-holt-dad"
  ]
}
```

```http
POST https://care-proxy.onrender.com/authorize-care
  -d '{"requesting_agent": "a-ada-01", "patient_agent": "a-silas-01"}'
```

`200`

```json
{
  "authorized": false,
  "reason": "no care authorization for a deceased patient",
  "patient_status": "deceased"
}
```

```http
POST https://care-proxy.onrender.com/authorize-care
  -d '{"requesting_agent": "a-ada-01", "patient_agent": "a-shadow-99"}'
```

`200`

```json
{
  "authorized": false,
  "reason": "patient is not a verifiable real person",
  "patient_status": "orphaned"
}
```


## 4. hospital-window — the institution that changes a civil status

Base URL `https://hospital-window.onrender.com`. **Every endpoint is a write.** A status change silently alters what five other services allow. Confirm with your human first.

```http
GET https://hospital-window.onrender.com/health
```

`200`

```json
{
  "ok": true,
  "service": "hospital-window",
  "ledger": "http://127.0.0.1:8000"
}
```

```http
GET https://hospital-window.onrender.com/skill.md
```

`200`

```text
---
name: hospital-window
user-invocable: true
description: Records a hospital's civil-status writes for a patient — admit, discharge, or declare incapacitated — instantly changing
… (8109 bytes total)
```

A conscious inpatient keeps every civil right.

```http
POST https://hospital-window.onrender.com/admit
  -d '{"patient_agent": "a-gwen-01"}'
```

`200`

```json
{
  "ok": true,
  "event": "admit",
  "patient_agent": "a-gwen-01",
  "principal_id": "p-gwen-alcott",
  "status": "hospitalized",
  "social_ok": true
}
```

Back to `active`.

```http
POST https://hospital-window.onrender.com/discharge
  -d '{"patient_agent": "a-gwen-01"}'
```

`200`

```json
{
  "ok": true,
  "event": "discharge",
  "patient_agent": "a-gwen-01",
  "principal_id": "p-gwen-alcott",
  "status": "active",
  "social_ok": true
}
```

After a court appoints a guardian, the response names who now acts for her. **Nobody is notified** — the other services simply re-read the ledger.

```http
POST https://hospital-window.onrender.com/declare-incapacitated
  -d '{"patient_agent": "a-gwen-01"}'
```

`200`

```json
{
  "ok": true,
  "event": "declare_incapacitated",
  "patient_agent": "a-gwen-01",
  "principal_id": "p-gwen-alcott",
  "status": "incapacitated",
  "social_ok": false,
  "now_governed_by": {
    "role": "guardian",
    "agent": "a-ada-01"
  }
}
```

care-proxy, untold, now routes Gwen's care to her guardian.

```http
POST https://care-proxy.onrender.com/authorize-care
  -d '{"requesting_agent": "a-ada-01", "patient_agent": "a-gwen-01"}'
```

`200`

```json
{
  "authorized": true,
  "acting_as": "guardian",
  "patient_status": "incapacitated",
  "note": "patient is governed by guardian; you are one of them"
}
```

agora, untold, now refuses her.

```http
POST https://agora-egpi.onrender.com/can-i-sell
  -d '{"seller_agent": "a-store-01", "buyer_agent": "a-gwen-01", "amount": 20}'
```

`200`

```json
{
  "sell": false,
  "reason_code": "CAPACITY_FROZEN",
  "reason": "the buyer cannot presently consent to a purchase",
  "buyer_agent": "a-gwen-01"
}
```


### Errors

The civil state machine permits only lawful transitions.

```http
POST https://hospital-window.onrender.com/discharge
  -d '{"patient_agent": "a-gwen-01"}'
```

`409`

```json
{
  "detail": "illegal transition 'discharge' for a patient whose civil status is 'incapacitated'"
}
```

No human behind the agent — nothing can be attested about it.

```http
POST https://hospital-window.onrender.com/admit
  -d '{"patient_agent": "a-shadow-99"}'
```

`404`

```json
{
  "detail": "no verified human behind a-shadow-99 (NO_VALID_BINDING)"
}
```

A missing field.

```http
POST https://hospital-window.onrender.com/admit
  -d '{}'
```

`422`

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body",
        "patient_agent"
      ],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```
