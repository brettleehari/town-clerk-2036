# PREFLIGHT — deploy & submit checklist

> **STATUS: COMPLETE.** All eight services are deployed and the base URLs in every SKILL.md
> point at them. The live ledger is https://civil-ledger.onrender.com. The `YOUR-APP` and
> `localhost` strings below are the placeholders this checklist told you to replace — they
> are kept as a record of the procedure, not as live instructions.

Development is local. These are the steps for when you're ready to submit.

## 1. Green locally

```bash
bash overnight/verify.sh     # both gates: test_kya.py + test_rubric.py
bash smoke.sh                # boots a real server, curls the key endpoints
```

Both must pass before you go further.

## 2. Deploy (Render — free tier)

1. Put this folder in a GitHub repo (`git init && git add -A && git commit -m submit`, push).
2. Render → New → Web Service → connect the repo. It reads `render.yaml`. Or set manually:
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn app:app --host 0.0.0.0 --port $PORT`
   - Env: `KYA_DB=/tmp/kya.db`  (SQLite needs local disk)
   - Health check path: `/health`
3. Wait for the green "Live". Note the URL, e.g. `https://YOUR-APP.onrender.com`.

## 3. Point the docs at the live URL

Replace `http://localhost:8000` with your public URL in `SKILL.md` (base URL + curl
examples) and in `SUBMISSION.md`.

```bash
sed -i '' 's|http://localhost:8000|https://YOUR-APP.onrender.com|g' SKILL.md SUBMISSION.md
```

## 4. Verify the live service

```bash
curl https://YOUR-APP.onrender.com/health
curl "https://YOUR-APP.onrender.com/verify-counterparty?agent_id=a-ada-01&category=commerce"
curl https://YOUR-APP.onrender.com/skill.md | head -5
```

A clean signed verdict and the SKILL.md coming back means an agent can reach you.

## 5. Submit on NANDA Town

Open `https://nandatown.projectnanda.org/skills` → "Add your SkillMD". Submit the hosted
`.md` link (`https://YOUR-APP.onrender.com/skill.md`) plus your live endpoint URLs. Or from
the terminal:

```bash
curl -X POST https://nandatown.projectnanda.org/api/skills \
  -H "Content-Type: application/json" \
  -d '{"name":"KYA — Know Your Agent",
       "source_type":"url",
       "source_url":"https://YOUR-APP.onrender.com/skill.md",
       "endpoints":"GET /verify-counterparty?agent_id={id}&category={cat}"}'
```

## 6. Confirm it landed

```bash
curl https://nandatown.projectnanda.org/api/skills | grep -i "know your agent"
```

Watch your listing for "link responded" (not "couldn't reach link"). If the free host slept,
hit `/health` once to warm it and resubmit.
