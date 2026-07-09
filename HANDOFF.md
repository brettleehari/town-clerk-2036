# HANDOFF — publish to GitHub + deploy on Render

Two goals: (A) push a clean, single-commit repo to GitHub with no local history, and
(B) deploy every planned service on Render, including the UI.

Repo: https://github.com/brettleehari/town-clerk-2036.git
Tests are green (139 + 34 + 45 = 218 assertions). `.gitignore` excludes `*.db`,
`*.rootseed`, `__pycache__` — the signing seed and databases stay out of the repo.

---

## A. Clean push to GitHub (one commit, no local dev history)

Run from the repo root.

```bash
# 0) clear any stale git lock files (a prior tooling session may have left these)
rm -f .git/HEAD.lock .git/index.lock

# 1) build a single root commit on an orphan branch (no parent history)
git checkout --orphan public-main
git add -A                                     # respects .gitignore; no db/seed included
git -c user.name="brettleehari" -c user.email="hariprasadsudharsan@gmail.com" \
  commit -m "Initial public release: KYA Civil Ledger and composing town services"

# 2) point at the remote and force-push the single commit to main
git remote add origin https://github.com/brettleehari/town-clerk-2036.git 2>/dev/null || true
git push -u origin public-main:main --force
```

Verify: `git log --oneline origin/main` should show exactly **one** line.
Commit hygiene: plain message, author `brettleehari <hariprasadsudharsan@gmail.com>`, no
AI/assistant attribution or co-author trailers.

---

## B. Deploy everything on Render (one Blueprint)

`render.yaml` already defines all 8 web services and auto-wires each front-door's
`LEDGER_URL` to the `civil-ledger` service. The UI needs no separate service — it is
bundled inside `civil-ledger` and served same-origin.

Steps:

1. Render → **New → Blueprint** → connect the `town-clerk-2036` repo. (Connecting Render to
   GitHub is a one-time OAuth click — that part is manual.)
2. It reads `render.yaml` and creates every service. Wait for **civil-ledger** to go green
   first; the seven front doors retry on cold start until it is up.
3. Record the public URLs.

### What gets deployed

| Service | What it is | Notable URLs |
|---|---|---|
| **civil-ledger** | The foundation + the **UI** | `/city` (trust view), `/console` (live API console), `/graph`, `/docs`, `/skill.md`, `/constitution`, `/verify-counterparty` |
| town-hall | Onboard a new human+agent | `/move-to-town`, `/skill.md` |
| dating | Verify before you meet | `/arrange-meeting`, `/skill.md` |
| babysit | Verify a sitter | `/book-sitter`, `/skill.md` |
| care-proxy | Route a care decision | `/authorize-care`, `/skill.md` |
| hiring | Verify before you hire | `/offer-work`, `/skill.md` |
| agora | Signed commerce receipt | `/can-i-sell`, `/skill.md` |
| hospital-window | Write civil status | `/admit`, `/discharge`, `/declare-incapacitated`, `/skill.md` |

The UI is live the moment `civil-ledger` deploys:
`https://civil-ledger-XXXX.onrender.com/city` and `/console`.

### Free-tier note

`KYA_DB` lives in `/tmp` and is wiped when a service sleeps. Seeded IDs regenerate
deterministically and `KYA_ROOT_SEED` is pinned, so seeded-agent demos and the UI are fine;
data an agent creates at runtime won't survive a sleep.

### Smoke test after deploy

```bash
LEDGER=https://civil-ledger-XXXX.onrender.com
curl "$LEDGER/health"
curl "$LEDGER/verify-counterparty?agent_id=a-ada-01&category=commerce"   # proceed:true, signed
open "$LEDGER/city"        # the UI
open "$LEDGER/console"     # live API console
```
