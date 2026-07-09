# KYA — submission video (record-ready script, v2)

Target: **~120 seconds, 1080p, 16:9.** Theme: **human-centered innovation** — *even when the
world goes agentic, the human (or institution) behind every agent stays at the center.* Almost
the whole video is one continuous screen-recording of `city.html`, whose intro now IS the
philosophy cards. The awe is the live front end re-deciding when one civic fact changes.

## How to record (all free, on your Mac)

- Screen record with `Cmd+Shift+5` (or QuickTime). Ideally two clips: (1) the browser running
  `city.html` end to end, (2) a small terminal for the composition + live-ripple beat.
- Voiceover: read the VO in iMovie's voiceover tool, or TTS (ElevenLabs) and drop it in.
- Edit in iMovie: lay the browser clip down, add VO, cut in the terminal beat, export 1080p.

## Pre-flight (start these, then do one dry run)

```bash
KYA_DB=/tmp/kya.db python3 -m uvicorn app:app --port 8000        # ledger + front end at /  (city.html)
(cd services/hospital-window && LEDGER_URL=http://localhost:8000 python3 -m uvicorn main:app --port 8106)
(cd services/hiring          && LEDGER_URL=http://localhost:8000 python3 -m uvicorn main:app --port 8105)
```
Open the ledger's front end (`city.html`) in the browser. Have the terminal ready.

---

## Shot list  (VO = voiceover · ON-SCREEN = what to show)

### 1 · Cold open — the philosophy cards (0:00–0:16)
- ON-SCREEN: open `city.html`. The built-in prelude plays: *what never changes* (to be known ·
  trusted · loved · cared for · to work · to belong · to be laid to rest) → *the means became
  agentic, the meaning stayed human* → the four principle cards. Press **Space** to sync to VO.
- VO: "A person needs the same things they always have — to be known, trusted, cared for, to
  work, to belong. Technology only ever changes the means. The meaning stays human."

### 2 · The human-centered landing (0:16–0:26)
- ON-SCREEN: the cards fade to the landing — **"Even when the world goes agentic, the human in
  this town stays at the center."** Let it breathe, then click **Enter Alford →**.
- VO: "So we built a town where — even when everything goes agentic — the human or institution
  behind every agent stays at the center."

### 3 · The living town + the lenses (0:26–0:42)
- ON-SCREEN: the town graph. Click the lens **Rogues** — the unrooted agents light up. Then
  **Guardians**, **Heirs**, **Executors** in quick succession.
- VO: "Every dot is an agent, tied to a real person. These"—Rogues—"resolve to no one; the town
  refuses them. And capacity follows real life: guardians act for the incapacitated, heirs and
  executors carry an agent on after its human is gone. Agents even outlive us."

### 4 · MONEY SHOT — the verdict theater (0:42–1:04)
- ON-SCREEN: click **Ada** → *Verify this counterparty*. A golden pulse runs up the resolution
  chain to the root → **✅ PROCEED**. Click **✓ Verify this cert against /pubkey** → *"signature
  valid — a genuine, unforgeable verdict."* Then click the impostor **a-shadow-99** → Verify →
  **⛔ REFUSE · NO_VALID_BINDING**, the node flashes red.
- VO: "Before any deal, an agent asks one question and gets a signed answer. Ada is real — proceed,
  and the verdict is cryptographically unforgeable. This one resolves to no human — refused. An
  impostor, caught, in one call."

### 5 · The law itself is signed (1:04–1:12)
- ON-SCREEN: tap the golden root seal / **Verify this constitution against the root**. It confirms.
- VO: "Even the constitution is signed and generated from the code that enforces it — the law you
  read is exactly the law that runs."

### 6 · Composition — a whole society on one ledger (1:12–1:32)
- ON-SCREEN: cut to the terminal (or `services/README.md` topology). Show the journey:
  ```bash
  curl -s $HALL/move-to-town -H 'Content-Type: application/json' -d '{"name":"Rae Fenn"}'   # -> agent_id
  curl -s $DATING/arrange-meeting -d '{"my_agent":"a-…","their_agent":"a-ada-01"}'           # date
  curl -s $HIRING/offer-work    -d '{"employer_agent":"a-store-01","worker_agent":"a-ada-01","role":"clerk"}'  # hired
  curl -s $AGORA/can-i-sell     -d '{"seller_agent":"a-store-01","buyer_agent":"a-ada-01","amount":49.99}'      # sale + signed cert
  ```
- VO: "It's not one app. A person walks into town hall, gets a verified agent, and that same
  agent lives a whole life here — dating, hiring, a marketplace, childcare, medical care. Seven
  services, each its own SkillMD, every one reading the same ledger. A judge's agent uses one
  SkillMD, with no human help, and it just works."

### 7 · THE AWE — one civic act, the whole town re-decides, LIVE (1:32–1:56)
- ON-SCREEN: hiring says Owen can work:
  ```bash
  curl -s $HIRING/offer-work -d '{"employer_agent":"a-store-01","worker_agent":"a-owen-01","role":"clerk"}'  # hired
  ```
  Then ONE real-world act — Owen is in an accident, hospitalized into a coma:
  ```bash
  curl -s $HOSPITAL/declare-incapacitated -d '{"patient_agent":"a-owen-01"}'
  ```
  Back in `city.html`, click **Verify** on Owen (or re-run hiring) → it flips to **⛔ REFUSE**,
  red pulse. His care now routes to his guardian.
- VO: "Now watch. Owen can take a job. Then one thing happens — the hospital admits him to a coma.
  We change nothing else. No redeploy. Instantly the whole town re-decides: his agent can't take
  the job… but his guardian can now make his medical decisions. Capacity follows real life."

### 8 · Proof (1:56–2:06)
- ON-SCREEN: fast — `python3 test_kya.py` (119) + `test_rubric.py` (33) + `services/test_compose.py`
  (45) scrolling green; a live signed verdict from the deployed URL; a `skill.md` in the browser.
- VO: "Real and live. A hundred and ninety-plus tests green, signed verdicts, no API key — and
  agents that succeed from the SkillMD alone."

### 9 · Close (2:06–2:14)
- ON-SCREEN: back to the landing / a closing card.
- VO: "The means became agentic. The meaning stayed human. That's the town we built."

---

## VO script (read straight through)

> A person needs the same things they always have — to be known, trusted, cared for, to work, to
> belong. Technology only ever changes the means. The meaning stays human.
> So we built a town where, even when everything goes agentic, the human or institution behind
> every agent stays at the center.
> Every dot is an agent, tied to a real person. These resolve to no one — the town refuses them.
> Capacity follows real life: guardians act for the incapacitated; heirs and executors carry an
> agent on after its human is gone. Agents even outlive us.
> Before any deal, an agent asks one question and gets a signed answer. Ada is real — proceed, and
> the verdict is cryptographically unforgeable. This one resolves to no human — refused. An
> impostor, caught, in one call.
> Even the constitution is signed, and generated from the code that enforces it — the law you read
> is exactly the law that runs.
> And it's not one app. A person walks into town hall, gets a verified agent, and that same agent
> lives a whole life here — dating, hiring, a marketplace, childcare, medical care. Seven services,
> each its own SkillMD, all reading one ledger. A judge's agent uses one SkillMD, no human help,
> and it just works.
> Now watch. Owen can take a job. Then one thing happens — the hospital admits him to a coma. We
> change nothing else. No redeploy. Instantly the town re-decides: his agent can't take the job,
> but his guardian can now make his medical decisions. Capacity follows real life.
> Real and live: a hundred and ninety-plus tests green, signed verdicts, no API key, and agents
> that succeed from the SkillMD alone.
> The means became agentic. The meaning stayed human. That's the town we built.

## Shell vars (local; swap for deployed URLs at submission time)

```bash
export LEDGER=http://localhost:8000  HALL=http://localhost:8103  DATING=http://localhost:8100
export HIRING=http://localhost:8105  AGORA=http://localhost:8104 HOSPITAL=http://localhost:8106
# add -H 'Content-Type: application/json' to each POST (trimmed above for the shot list)
```

## Notes
- The cards are built into `city.html` now (auto-advance, or Space to sync to VO, S to skip).
- Whole video can be ONE continuous recording of `city.html` + a short terminal cut for beats 6–7.
- Keep it under ~2:15. Front-load the awe: a refusal or a signed PROCEED should appear by ~0:45.
