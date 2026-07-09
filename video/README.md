# The demo video — a permanent URL, a fixed format

**Submit this URL:** `https://civil-ledger.onrender.com/video`

It never 404s and never needs editing again. It resolves in this order:

1. **`VIDEO_URL` env var set** → `302` redirect to wherever the latest cut lives.
2. **`video/demo.mp4` present in the repo** → the file is streamed inline (`video/mp4`).
3. **Neither** → a placeholder page pointing at the live UI. Returns `200`.

Today it serves the placeholder. Drop the film in tomorrow and it serves the film.

## Which of the two should you use?

**Use `VIDEO_URL` (recommended).** Set it in the Render dashboard to an unlisted YouTube
link, a Loom, or an S3 object. Repoint it any time from the dashboard — no commit, no
redeploy of the submission.

Serving `video/demo.mp4` from the repo works, but two real limits apply:

- **GitHub rejects files over 100 MB** (and warns above 50 MB). A 2-minute 1080p H.264 clip
  at ~10 Mbps is roughly 150 MB — over the line. Keep a repo-bundled cut under ~40 MB, which
  means ~2.5 Mbps, which is fine for a screen recording of flat UI but soft on gradients.
- **This server does not honour HTTP `Range` requests** (Starlette 0.37.2 `FileResponse`
  returns `200`, not `206`). A viewer who scrubs re-downloads the whole file. Acceptable for
  a small clip; unpleasant for a large one.

So: bundle a small cut as a fallback if you like, and point `VIDEO_URL` at the real one.

## The format — fixed now, so tomorrow's file drops straight in

| | |
|---|---|
| Container | `.mp4` |
| Video | H.264 (AVC), High profile |
| Audio | AAC-LC, 128 kbps, 48 kHz stereo |
| Resolution | 1920×1080 (16:9) |
| Frame rate | 30 fps |
| Faststart | yes — `moov` atom at the front, so it plays before it finishes downloading |
| Filename | `video/demo.mp4` exactly |
| Target length | ~120 s (see `VIDEO_SCRIPT.md`) |

## Producing it on a MacBook, with no installs

**1. Record.** `Cmd+Shift+5` → *Record Selected Portion* → drag a 16:9 region over the
browser → Record. Or QuickTime Player → *File ▸ New Screen Recording*. Both write `.mov`
(H.264 + AAC). Record the browser at a 1920×1080 window so there is no upscaling.

**2. Edit.** iMovie: drop the clip in, record the voiceover (*Windows ▸ Record Voiceover*),
cut in the terminal beat. Share ▸ File ▸ Resolution **1080p**, Quality **High**.

**3. Normalise to the exact format.** macOS ships `avconvert` — no Homebrew needed:

```bash
avconvert --source ~/Desktop/kya-raw.mov \
          --preset Preset1920x1080 \
          --output video/demo.mp4 --replace --progress
```

`Preset1920x1080` produces H.264 + AAC in an MP4 with faststart enabled by default. Do **not**
pass `--disableFastStart`. Prefer `Preset1920x1080` over `PresetHEVC1920x1080`: HEVC will not
play in every browser a judge might use.

**4. Check it.** Before committing:

```bash
python3 video/check_video.py
```

It parses the MP4 boxes directly (no ffprobe) and fails loudly if the container, resolution,
duration, faststart flag, or size would break playback or the GitHub limit.

**5. Ship it.**

```bash
git add video/demo.mp4 && git commit && git push
# then redeploy civil-ledger, or just set VIDEO_URL instead
```

## Why `/video` and not a raw link

A submitted URL is immutable in practice — the form has been sent, the judge has the link.
`/video` puts the indirection on your side of the wire. Recut the film at midnight and repoint
one env var; every link anyone holds still resolves.
