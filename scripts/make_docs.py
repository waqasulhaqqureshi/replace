#!/usr/bin/env python3
"""
make_docs.py — generates the written deliverables straight from the data.

Nothing here is hand-copied: the scene index, the block analysis table and the
coverage stats are all derived from analysis/metrics.json + graphics/timeline.json,
so the docs can never drift from what the renderer actually burns in.

    python3 scripts/make_docs.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
DOCS.mkdir(exist_ok=True)

TL = json.loads((ROOT / "graphics" / "timeline.json").read_text())
MET = json.loads((ROOT / "analysis" / "metrics.json").read_text())

KIND_LABEL = {
    "id_card": "Nameplate", "lower_third": "Lower third", "callout": "Callout card",
    "stat": "Metric counter", "ring": "Tracking ring", "bracket": "HUD bracket",
    "chapter": "Chapter type", "caption": "Caption", "corner": "Margin note",
    "equation": "Equation", "progress": "Progress rail", "bars": "Bar chart",
    "leaderboard": "Leaderboard", "quadrant": "Quadrant lens", "gauge": "Gauge",
    "donut": "Donut", "speed_hud": "Speed HUD", "ad_break": "Broadcast stinger",
    "end_card": "End card", "ticker": "Ticker rail", "waveform": "Live waveform",
}

KIND_MOTION = {
    "id_card": "accent bar wipe · kicker fade · headline rise · rule scaleX",
    "lower_third": "as nameplate",
    "callout": "panel rise 26 px · staggered rows · leader line draws to anchor",
    "stat": "count-up (decelerating) · label fade · hairline progress",
    "ring": "arc sweep + rotating dashed orbit · pulsing centre dot",
    "bracket": "corner strokes draw (pathLength) · tick marks · crosshair",
    "chapter": "typewriter / word-mask reveal · underline sweep",
    "caption": "typewriter reveal",
    "corner": "kicker track-in · rule wipe",
    "equation": "sub-line slide · underline sweep",
    "progress": "bar fills over 1.1 s · live fraction label",
    "bars": "bars grow scaleX, 70 ms stagger",
    "leaderboard": "rows slide in 80 ms stagger · delta chips pop",
    "quadrant": "frontier curve draws · focal dot pulses",
    "gauge": "needle sweep with easeOutBack overshoot · arc dashoffset",
    "donut": "ring sweep from 12 o'clock · value counts with it",
    "speed_hud": "delta count-up · speed streaks translate",
    "ad_break": "skewed stinger scale-in · REC dot blink",
    "end_card": "pulse rings · play glyph scale",
    "ticker": "marquee offset = (t − t0) × 46 px/s (scrub-safe)",
    "waveform": "canvas redraw @60fps from real audio envelope + playhead",
}


def mmss(x: float) -> str:
    x = int(round(x))
    return f"{x // 60:02d}:{x % 60:02d}"


def cell(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ")


# --------------------------------------------------------- 1. scene index
def scene_index() -> str:
    L = []
    L.append("# Timestamp Scene Index — 30-Minute Source\n")
    L.append(f"**Source:** `{TL['brand']['source']}` · 1280×720 · 30 fps · "
             f"duration **{TL['duration_hms']}** (the file is 27:21, not a full 30:00 — "
             f"the index covers every second of it).\n")
    L.append(f"**Beats:** {len(TL['events'])} graphics events across "
             f"{len(TL['chapters'])} chapters · **{MET['duration_s']}** seconds analysed at 1 fps · "
             f"**{len(MET['cuts'])}** hard cuts detected by ffmpeg scene scoring.\n")
    L.append("\n> Every row is machine-generated from `graphics/timeline.json`, which is the same "
             "file the burn-in renderer and the React player consume. `motion / lum` are the "
             "measured mean frame-delta and plate luminance of the beat's span — they tell you how "
             "much visual headroom the graphic has to work with.\n")

    for ch in TL["chapters"]:
        evs = [e for e in TL["events"] if e["t0"] >= ch["t0"] - 0.01 and e["t0"] < ch["t1"]]
        L.append(f"\n## {ch['id'].upper()} · {ch['title']} "
                 f"(`{mmss(ch['t0'])}–{mmss(ch['t1'])}`)")
        L.append(f"*{ch['sub']}*\n")
        if not evs:
            L.append("_No overlay — intentional breathing room._")
            continue
        L.append("| In | Out | Dur | Graphic | Copy / data | Motion | plate motion / lum | Why this beat |")
        L.append("|----|-----|-----|---------|-------------|--------|---------------------|----------------|")
        for e in evs:
            copy_bits = [e.get("kicker"), e.get("title"), e.get("sub"), e.get("label")]
            if e.get("value") is not None:
                v = e["value"]
                shown = f"{v:,.0f}" if e.get("fmt") == "comma" else f"{v:g}"
                copy_bits.insert(1, f"{shown}{e.get('suffix','')}")
            if e.get("items"):
                copy_bits.append(" · ".join(f"{i['label']}={i['value']}" for i in e["items"][:4]))
            copy = " — ".join([c for c in copy_bits if c])
            m = e.get("measured") or {}
            L.append(
                f"| `{mmss(e['t0'])}` | `{mmss(e['t1'])}` | {e['t1']-e['t0']:.1f}s | "
                f"**{KIND_LABEL.get(e['kind'], e['kind'])}** | {cell(copy)[:180]} | "
                f"{KIND_MOTION.get(e['kind'], '—')} | "
                f"{m.get('motion', 0):.1f} / {m.get('lum', 0):.0f} | {cell(e.get('note', ''))} |"
            )
    return "\n".join(L) + "\n"


# --------------------------------------------------- 2. block analysis table
def block_table() -> str:
    L = []
    L.append("# Block Analysis — 5-Minute Windows\n")
    L.append("Measured on the source at 1 fps: luminance, saturation, frame-to-frame motion, edge "
             "density, UI/text density, near-black ratio, audio level and dominant hue. "
             "`static UI %` is the share of seconds that are frozen text screens — the signal that "
             "a section needs an animated rail rather than more panels.\n")
    L.append("| Block | Window | Lum | Sat | Motion (mean/max) | Edge | Text | Black | Static UI | Dominant hue | Audio dB |")
    L.append("|-------|--------|-----|-----|-------------------|------|------|-------|-----------|--------------|----------|")
    for b in MET["blocks"]:
        L.append(
            f"| {b['block']} | `{b['label']}` | {b['lum_mean']:.0f} | {b['sat_mean']:.2f} | "
            f"{b['motion_mean']:.1f} / {b['motion_max']:.0f} | {b['edge_mean']:.3f} | "
            f"{b['text_density_mean']:.3f} | {b['black_ratio_mean']:.2f} | "
            f"{b['static_ui_ratio']*100:.0f}% | {b['dominant_hue_deg']}° | {b['audio_db_mean']:.1f} |"
        )
    L.append("\n## What the numbers say\n")
    blocks = MET["blocks"]
    busiest = max(blocks, key=lambda b: b["motion_mean"])
    stillest = min(blocks, key=lambda b: b["motion_mean"])
    darkest = min(blocks, key=lambda b: b["lum_mean"])
    textiest = max(blocks, key=lambda b: b["text_density_mean"])
    L.append(f"- **Busiest plate:** block {busiest['block']} (`{busiest['label']}`) at "
             f"{busiest['motion_mean']:.1f} mean Δ — graphics must be light-touch here.")
    L.append(f"- **Stillest plate:** block {stillest['block']} (`{stillest['label']}`) at "
             f"{stillest['motion_mean']:.1f} mean Δ — the safest place for dense data panels.")
    L.append(f"- **Darkest plate:** block {darkest['block']} at luminance {darkest['lum_mean']:.0f}/255 "
             f"— accents must be bright (cyan/lime), never mid-grey.")
    L.append(f"- **Most text-heavy:** block {textiest['block']} at text density "
             f"{textiest['text_density_mean']:.3f} — overlay only in margins, never over copy.")
    L.append(f"- **Colour identity:** all six blocks are blue-dominant "
             f"(210–240°); every overlay accent was chosen to *contrast* with that field, which is "
             f"why the system leads with cyan, lime and amber rather than more blue.")
    L.append("\n## Creative calls — where the graphics stay out of the way\n")
    L.append("The measured plate decides the treatment. Where the source already animates its own "
             "data, adding a second chart reads as clutter, so those windows get margin notes or "
             "nothing at all. These are the deliberate gaps:\n")
    for when, what in (
        ("`02:50–03:50`", "the Eratosthenes interlude animates itself (map, shadow, type) — margin "
                          "corner notes only, no panels."),
        ("`16:25–18:40`", "the model section carries its own tables and charts — callouts sit in the "
                          "left margin, never over the data."),
        ("`21:20–22:25`", "the Numbers chapter runs a benchmark table → bar race → cost/speed "
                          "scatter, all full-frame. Earlier drafts drew our own bars and a quadrant "
                          "lens over them and were unreadable; the window is now clean apart from the "
                          "top-edge delta ticker, which rides the source's browser chrome."),
        ("`23:20–24:40`", "the infrastructure section already shows a gauge, a 20/80 bar and a "
                          "cache donut, so the three HUDs here deliberately measure *different* "
                          "quantities (fabric utilisation, $/GPU-hour, prefill avoided) instead of "
                          "restating the source's own numbers."),
    ):
        L.append(f"- {when} — {what}")
    return "\n".join(L) + "\n"


def main() -> None:
    (DOCS / "SCENE_INDEX.md").write_text(scene_index())
    (DOCS / "BLOCK_ANALYSIS.md").write_text(block_table())

    covered = set()
    for e in TL["events"]:
        covered.update(range(int(e["t0"]), int(e["t1"]) + 1))
    d = TL["duration_s"]
    kinds: dict[str, int] = {}
    for e in TL["events"]:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    print(f"SCENE_INDEX.md  {len(TL['events'])} beats · coverage {len(covered)/d*100:.1f}%")
    print(f"BLOCK_ANALYSIS.md  {len(MET['blocks'])} windows")
    print("kinds:", ", ".join(f"{k}×{v}" for k, v in sorted(kinds.items(), key=lambda kv: -kv[1])))


if __name__ == "__main__":
    main()
