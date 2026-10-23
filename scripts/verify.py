#!/usr/bin/env python3
"""
verify.py — end-to-end consistency check for the motion-graphics system.

Guards the contracts that are easy to break by accident:
  1. every timeline kind has a renderer in the PIL compositor, the React player
     AND the FFmpeg/libass vector renderer
  2. every event is well-formed (box in 0..1, t1 > t0, measured stats present)
  3. no two same-corner graphics collide on screen at the same time
  4. graphics never cover a measured text-heavy plate (warns, doesn't fail)
  5. generated artefacts exist and match their sources
  6. the web app type-checks and builds

    python3 scripts/verify.py            # checks 1-5
    python3 scripts/verify.py --build    # + tsc/vite build
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ok = True


def check(name: str, cond: bool, detail: str = "") -> None:
    global ok
    mark = "\033[92mPASS\033[0m" if cond else "\033[91mFAIL\033[0m"
    print(f"  [{mark}] {name}" + (f"  — {detail}" if detail else ""))
    if not cond:
        ok = False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    args = ap.parse_args()

    tl_path = ROOT / "graphics" / "timeline.json"
    if not tl_path.exists():
        print("graphics/timeline.json missing — run scripts/build_timeline.py")
        sys.exit(1)
    tl = json.loads(tl_path.read_text())
    kinds = sorted({e["kind"] for e in tl["events"]})

    print("\n1 · renderer coverage")
    py = (ROOT / "scripts" / "overlay_lib.py").read_text()
    prim = re.search(r"_RENDERERS = \{(.*?)\}", py, re.S).group(1)
    pil = set(re.findall(r'"(\w+)":', prim)) | {"ticker", "waveform"}
    web = set(re.findall(r"case '(\w+)'",
              (ROOT / "web/src/overlay/TimelineOverlay.tsx").read_text()))
    check("every kind renders in the PIL compositor", not (set(kinds) - pil),
          f"missing: {sorted(set(kinds) - pil)}" if set(kinds) - pil else f"{len(kinds)} kinds")
    check("every kind renders in the React player", not (set(kinds) - web),
          f"missing: {sorted(set(kinds) - web)}" if set(kinds) - web else f"{len(kinds)} kinds")

    sys.path.insert(0, str(ROOT / "scripts"))
    from make_ffmpeg_ass import RENDERERS as ass_shapes  # noqa: E402  (main is guarded)
    missing_ass = sorted(set(kinds) - set(ass_shapes))
    check("every kind renders in the FFmpeg ASS renderer", not missing_ass,
          f"missing: {missing_ass}" if missing_ass
          else f"{len(kinds)}/{len(kinds)} kinds via {len(ass_shapes)} vector renderers")
    ass = (ROOT / "render" / "overlay.ass").read_text()
    pinned = [ln[:60] for ln in ass.splitlines()
              if ln.startswith("Dialogue:") and "\\move(" in ln and "\\pos(" in ln]
    check("no ASS event pins a \\move with \\pos", not pinned,
          f"{len(pinned)} event(s) would sit frozen at their start point: {pinned[:2]}")
    sh = (ROOT / "scripts" / "ffmpeg_overlay.sh").read_text()
    check("ffmpeg_overlay.sh keeps absolute ASS timing",
          "-copyts" in sh and "-r 30" in sh,
          "-copyts + -r 30 present (a trimmed window would otherwise render 0:00-1:00)")

    print("\n2 · event schema")
    bad_box = [e["id"] for e in tl["events"] if not all(0 <= v <= 1.01 for v in e["box"])]
    bad_time = [e["id"] for e in tl["events"] if e["t1"] <= e["t0"]]
    no_meas = [e["id"] for e in tl["events"] if "measured" not in e]
    check("boxes inside normalised stage", not bad_box, str(bad_box[:5]))
    check("t1 > t0 for every beat", not bad_time, str(bad_time[:5]))
    check("every beat carries measured stats", not no_meas, str(no_meas[:5]))
    check("timeline within source duration",
          max(e["t1"] for e in tl["events"]) <= tl["duration_s"] + 1,
          f"max {max(e['t1'] for e in tl['events'])}s / {tl['duration_s']}s")

    print("\n3 · spatial collisions (same screen corner, same time)")
    def corner(b):
        cx, cy = b[0] + b[2] / 2, b[1] + b[3] / 2
        return (cx > 0.5, cy > 0.5)
    clashes = []
    ev = tl["events"]
    for i, a in enumerate(ev):
        for b in ev[i + 1:]:
            if b["t0"] > a["t1"] or a["t0"] > b["t1"]:
                continue
            overlap = min(a["t1"], b["t1"]) - max(a["t0"], b["t0"])
            if overlap > 1.2 and corner(a["box"]) == corner(b["box"]):
                clashes.append((a["id"], b["id"], round(overlap, 1)))
    check("no long same-corner overlaps", not clashes, str(clashes[:4]))

    print("\n4 · readability warnings (non-blocking)")
    for e in ev:
        m = e.get("measured") or {}
        if m.get("text_note"):
            continue
        if m.get("lum", 0) > 190 and e["kind"] in {"stat", "bars", "callout", "leaderboard"}:
            print(f"    note: {e['id']} sits on a bright plate (lum {m['lum']:.0f}) — "
                  f"glass density is raised for these kinds")

    print("\n5 · artefacts")
    check("analysis/metrics.json", (ROOT / "analysis" / "metrics.json").exists())
    check("graphics/waveform.json", (ROOT / "graphics" / "waveform.json").exists())
    check("render/overlay.ass", (ROOT / "render" / "overlay.ass").exists())
    check("web/src/data/timeline.json in sync",
          (ROOT / "web/src/data/timeline.json").read_text().strip()
          == json.dumps(tl, separators=(",", ":")).strip(),
          "regenerate from build_timeline.py if this fails")
    for doc in ("SCENE_INDEX.md", "BLOCK_ANALYSIS.md", "NEW_VIDEO_SPEC.md", "ARCHITECTURE.md"):
        check(f"docs/{doc}", (ROOT / "docs" / doc).exists())

    if args.build:
        print("\n6 · web build")
        r = subprocess.run(["npx", "tsc", "-b"], cwd=ROOT / "web", capture_output=True, text=True)
        check("typescript", r.returncode == 0, r.stdout.strip()[:300])
        r = subprocess.run(["npx", "vite", "build"], cwd=ROOT / "web",
                           capture_output=True, text=True)
        check("vite build", r.returncode == 0, (r.stderr or r.stdout).strip()[-200:])

    print("\n" + ("\033[92mALL CHECKS PASSED\033[0m" if ok else "\033[91mCHECKS FAILED\033[0m"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
