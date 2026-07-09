#!/usr/bin/env python3
"""
check_video.py — validate video/demo.mp4 before you commit it.

Parses the MP4 box structure directly; no ffprobe, no installs. Checks the things that
actually break a submission: wrong container, missing faststart (the video will not play
until it fully downloads), wrong resolution, and a file GitHub will refuse.

    python3 video/check_video.py [path]
"""
import struct
import sys
from pathlib import Path

PATH = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent / "demo.mp4")
WANT_W, WANT_H = 1920, 1080
GITHUB_HARD_LIMIT = 100 * 1024 * 1024
GITHUB_WARN = 50 * 1024 * 1024

fails, warns = [], []


def boxes(data, start=0, end=None):
    """Yield (name, payload_start, payload_end) for top-level boxes in a byte range."""
    end = len(data) if end is None else end
    i = start
    while i + 8 <= end:
        size = struct.unpack(">I", data[i:i + 4])[0]
        name = data[i + 4:i + 8].decode("latin-1")
        if size == 1:                                   # 64-bit extended size
            size = struct.unpack(">Q", data[i + 8:i + 16])[0]
            body = i + 16
        elif size == 0:                                 # extends to EOF
            size = end - i
            body = i + 8
        else:
            body = i + 8
        if size < 8:
            break
        yield name, body, min(i + size, end)
        i += size


def find(data, path, start=0, end=None):
    """Descend a slash-path of box names, e.g. moov/trak/tkhd."""
    head, _, rest = path.partition("/")
    for name, b, e in boxes(data, start, end):
        if name == head:
            return (b, e) if not rest else find(data, rest, b, e)
    return None


if not PATH.exists():
    print(f"✗ {PATH} does not exist.")
    print("  Record it, then: avconvert -s raw.mov -p Preset1920x1080 -o video/demo.mp4 --replace")
    sys.exit(1)

raw = PATH.read_bytes()
size = len(raw)
print(f"checking {PATH}  ({size / 1024 / 1024:.1f} MB)")

# --- container ---------------------------------------------------------------
top = [n for n, _, _ in boxes(raw)]
if not top or top[0] != "ftyp":
    fails.append(f"not an MP4: first box is {top[:1] or ['<none>']}, expected 'ftyp'")
else:
    b, e = find(raw, "ftyp")
    brand = raw[b:b + 4].decode("latin-1", "replace")
    print(f"  brand: {brand}")
    if brand not in ("isom", "mp42", "M4V ", "avc1", "iso2"):
        warns.append(f"unusual major brand {brand!r}; most players want isom/mp42")

# --- faststart: moov must precede mdat ---------------------------------------
if "moov" in top and "mdat" in top:
    if top.index("moov") > top.index("mdat"):
        fails.append("no faststart: 'moov' comes after 'mdat', so the video will not play "
                     "until it has fully downloaded. Re-encode without --disableFastStart.")
    else:
        print("  faststart: yes (moov before mdat)")
elif "moov" not in top:
    fails.append("no 'moov' box — the file is truncated or not a movie")

# --- duration ----------------------------------------------------------------
mvhd = find(raw, "moov/mvhd")
if mvhd:
    b, _ = mvhd
    version = raw[b]
    if version == 0:
        timescale, duration = struct.unpack(">II", raw[b + 12:b + 20])
    else:
        timescale = struct.unpack(">I", raw[b + 20:b + 24])[0]
        duration = struct.unpack(">Q", raw[b + 24:b + 32])[0]
    secs = duration / timescale if timescale else 0
    print(f"  duration: {secs:.1f}s")
    if secs < 5:
        fails.append(f"duration is {secs:.1f}s — that is not a demo")
    elif secs > 300:
        warns.append(f"duration is {secs:.0f}s; most judges cap at 2-3 minutes")

# --- resolution: the largest tkhd wins (skips the audio track) ----------------
best = (0, 0)
for name, b, e in boxes(raw):
    if name != "moov":
        continue
    for n2, b2, e2 in boxes(raw, b, e):
        if n2 != "trak":
            continue
        tk = find(raw, "tkhd", b2, e2)
        if not tk:
            continue
        tb, _ = tk
        off = 84 if raw[tb] == 0 else 96          # version 0 vs 1 header length
        if tb + off + 8 <= len(raw):
            w = struct.unpack(">I", raw[tb + off:tb + off + 4])[0] >> 16
            h = struct.unpack(">I", raw[tb + off + 4:tb + off + 8])[0] >> 16
            if w * h > best[0] * best[1]:
                best = (w, h)
if best != (0, 0):
    w, h = best
    print(f"  resolution: {w}x{h}")
    if (w, h) != (WANT_W, WANT_H):
        warns.append(f"resolution is {w}x{h}, expected {WANT_W}x{WANT_H}")
    if h and abs(w / h - 16 / 9) > 0.02:
        fails.append(f"aspect ratio is not 16:9 ({w}x{h})")
else:
    warns.append("could not read a video track resolution")

# --- size --------------------------------------------------------------------
if size > GITHUB_HARD_LIMIT:
    fails.append(f"{size/1024/1024:.0f} MB exceeds GitHub's 100 MB hard limit — "
                 f"host it and set VIDEO_URL instead")
elif size > GITHUB_WARN:
    warns.append(f"{size/1024/1024:.0f} MB — GitHub warns above 50 MB; prefer VIDEO_URL")

# --- verdict -----------------------------------------------------------------
print()
for w_ in warns:
    print(f"  ! {w_}")
for f_ in fails:
    print(f"  ✗ {f_}")
if not fails:
    print("\n✓ ready to commit. `git add video/demo.mp4`, then redeploy or set VIDEO_URL.")
sys.exit(1 if fails else 0)
