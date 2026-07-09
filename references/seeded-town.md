# The pre-seeded town — an instant playground

Referenced from `SKILL.md`. Every id below is live on the running service; all reads are open
and need no key, and nothing here requires a write.

| principal | status | bound agent | try |
|---|---|---|---|
| p-ada-marsh | active | a-ada-01 | verify-counterparty → `proceed:true` |
| p-silas-crane | deceased | a-silas-01 | → `PRINCIPAL_DECEASED`; executor a-vane-exec, category `estate` only |
| p-june-okafor | incapacitated (coma) | a-june-01 | financial → `CAPACITY_FROZEN`; medical → guardian a-okafor-g |
| p-marlow-reyes | incarcerated | a-marlow-01 | commerce → `CATEGORY_NOT_ALLOWED`; legal → `proceed:true` |
| p-tam-holt | minor | a-tam-01 | governed by regents; financial frozen |
| p-iris-vane | missing | a-iris-01 | → `PRINCIPAL_MISSING` |
| p-mara-vale | active (heir) | a-mara-01 | inherited Edith Vale's agent a-edith-01 |
| p-edith-vale | deceased (with will) | a-edith-01 | inherited → resolves to heir Mara, capped to estate/family_support |
| corp-marshco | — | a-store-01 | corporate storefront agent, always transacts |
| — | — | a-shadow-99 | unbound impostor → `NO_VALID_BINDING` |
| p-bram-kessler | active | a-bram-01, a-bram-work, a-bram-shop | **one human, three agents** — all resolve to him, share his status, capped at 5 |
| p-hanna-vosk | active | *(none)* | **one human, no agent** — full capacity via `GET /capacity/p-hanna-vosk`; owns no digital twin |
| — | — | a-vosk-99 | claims to be Hanna's assistant; she owns no agent, so → `NO_VALID_BINDING` |

Plus more Alford residents (Owen Brook, Lena Hart, Nora Blau, Cyrus Ford, Gwen Alcott) and
an open election `elec-council-2035` (Alford City Council) with votes already cast.

Seed institution keys (sandbox, for playing every role):
`sk_seed_registrar`, `sk_seed_court`, `sk_seed_hospital`, `sk_seed_coroner_a`,
`sk_seed_coroner_b`, `sk_seed_police`.
