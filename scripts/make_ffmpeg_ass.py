#!/usr/bin/env python3
"""
make_ffmpeg_ass.py — compiles graphics/timeline.json into a broadcast-grade
ASS (Advanced SubStation Alpha) script, plus the one-line FFmpeg command that
burns it in.

Two rendering paths ship with this project:

  1. scripts/render_overlay.py  — Python/PIL compositor. Full fidelity: gauges,
                                  live canvas waveforms, leader lines, tickers.
                                  Slower, needs Pillow.
  2. scripts/ffmpeg_overlay.sh  — THIS generator. Pure FFmpeg + libass: vector
                                  panels, styled type, timed fades, velocity
                                  moves. No Python at render time, GPU/hardware
                                  encoder friendly, easy to slot into an
                                  existing encode farm.

Why ASS instead of drawtext?
  · `drawtext` is absent from many static FFmpeg builds (including the one used
    here) — `ass`/`subtitles` (libass) is far more universally available.
  · ASS gives vector drawing commands, per-event alpha, \fad, \move, letter
    spacing and exact \pos placement, i.e. real motion graphics rather than a
    stack of boxes.
  · One filter, one pass, no PNG sequencing.

The ASS path renders the typographic subset of the timeline (nameplates, lower
thirds, tickers, chapter cards, callout panels, stat cards, margin notes).
Data-viz primitives (bars, gauges, donuts, waveforms, leaderboards) stay on the
Python path.

    python3 scripts/make_ffmpeg_ass.py     # → render/overlay.ass + scripts/ffmpeg_overlay.sh
    bash scripts/ffmpeg_overlay.sh         # full 27-minute burn-in
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TL = json.loads((ROOT / "graphics" / "timeline.json").read_text())
PAL = TL["brand"]["palette"]

W, H = 1280, 720
SUPPORTED = {"ticker", "lower_third", "id_card", "chapter", "callout",
             "corner", "stat", "caption", "equation", "end_card", "ad_break"}


def ass_color(hex_rgb: str, alpha: float = 0.0) -> str:
    """#RRGGBB + alpha(0..1, 0 = opaque) → &HAABBGGRR& (ASS override syntax)."""
    h = hex_rgb.lstrip("#")
    r, g, b = h[0:2], h[2:4], h[4:6]
    a = int(round(max(0.0, min(1.0, alpha)) * 255))
    return f"&H{a:02X}{b}{g}{r}&".upper()


def ts(t: float) -> str:
    cs = int(round(t * 100))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, c = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"


def esc(text: str) -> str:
    return (text.replace("\\", "\\\\").replace("{", "(").replace("}", ")")
            .replace("\n", "\\N"))


def rect(x: int, y: int, w: int, h: int) -> str:
    """ASS vector drawing: a filled rectangle at absolute coords."""
    return (f"m {x} {y} l {x + w} {y} {x + w} {y + h} {x} {y + h}")


def panel(x: int, y: int, w: int, h: int, accent: str, layers: list[str],
          start: float, end: float, bar: bool = True) -> None:
    fade = 320 if end - start > 1.6 else 120
    layers.append(
        f"Dialogue: 1,{ts(start)},{ts(end)},Panel,,0,0,0,,"
        f"{{\\an7\\pos(0,0)\\p1\\bord0\\shad0\\1c{ass_color('#0A0F1C', 0.18)}"
        f"\\fad({fade},220)}}{rect(x, y, w, h)}{{\\p0}}"
    )
    # hairline top edge
    layers.append(
        f"Dialogue: 2,{ts(start)},{ts(end)},Panel,,0,0,0,,"
        f"{{\\an7\\pos(0,0)\\p1\\bord0\\shad0\\1c{ass_color(accent, 0.45)}\\fad({fade},220)}}"
        f"{rect(x, y, w, 1)}{{\\p0}}"
    )
    if bar:
        layers.append(
            f"Dialogue: 3,{ts(start)},{ts(end)},Panel,,0,0,0,,"
            f"{{\\an7\\pos(0,0)\\p1\\bord0\\shad0\\1c{ass_color(accent, 0.0)}\\fad({fade},220)}}"
            f"{rect(x, y, 3, h)}{{\\p0}}"
        )


def text(out: list[str], copy_lines: list[str], style: str, x: int, y: int,
         start: float, end: float, size: int, color: str, *,
         bold: bool = False, spacing: float = 0,
         move: tuple[int, int] | None = None, marquee: tuple[int, int] | None = None,
         fade: int = 320, alpha: float = 0.0, italic: bool = False,
         layer: int = 4) -> None:
    """Emit one ASS dialogue line. `out` is the dialogue accumulator."""
    if marquee:
        anim = f"\\move({marquee[0]},{y},{marquee[1]},{y})"
        fade_tag = ""
    elif move:
        anim = f"\\pos({x},{y})\\move({x},{y},{x},{y + move[1]})"
        fade_tag = f"\\fad({fade},{fade})"
    else:
        anim = f"\\pos({x},{y})"
        fade_tag = f"\\fad({fade},{fade})"
    bold_tag = "\\b1" if bold else "\\b0"
    ital_tag = "\\i1" if italic else ""
    joined = "\\N".join(esc(l) for l in copy_lines)
    out.append(
        f"Dialogue: {layer},{ts(start)},{ts(end)},{style},,0,0,0,,"
        f"{{\\an7\\fs{size}\\1c{ass_color(color, alpha)}\\3c&H000000&"
        f"\\bord0\\shad0{bold_tag}{ital_tag}{fade_tag}"
        f"\\fsp{spacing}\\blur0.2{anim}}}{joined}"
    )


def build(layers: list[str]) -> int:
    used = 0
    for ev in TL["events"]:
        if ev["kind"] not in SUPPORTED:
            continue
        used += 1
        t0, t1 = ev["t0"], ev["t1"]
        accent = PAL.get(ev.get("accent", "cyan"), PAL["cyan"])
        x, y, w, h = ev["box"]
        px, py = int(x * W), int(y * H)
        pw, ph = int(w * W), int(h * H)

        if ev["kind"] == "ticker":
            bar_h = 34
            panel(0, py, W, bar_h, accent, layers, t0, t1, bar=False)
            label = ev.get("title", "")
            # a marquee via \move: enters right edge, exits left, over the beat
            text(out=layers, copy_lines=[f"   {label}   •   {label}   •"],
                 style="Mono", x=0, y=py + 9, start=t0, end=t1, size=15,
                 color=PAL["paper"], bold=True, spacing=1.6,
                 marquee=(W + 40, -2400), layer=4)
            continue

        if ev["kind"] == "ad_break":
            ph = max(ph, 74)
            panel(px, py, pw, ph, accent, layers, t0, t1, bar=True)
            text(layers, ["AD BREAK"], "Mono", px + 16, py + 10, t0, t1, 12,
                 PAL["magenta"], bold=True, spacing=2.0, fade=160)
            if ev.get("title"):
                text(layers, [ev["title"]], "Display", px + 16, py + 30, t0, t1, 26,
                     PAL["paper"], bold=True)
            continue

        # ---- generic panel stack -------------------------------------------
        body: list[tuple[str, str, int, str, bool]] = []  # text, style, size, color, bold
        if ev.get("kicker"):
            body.append((ev["kicker"].upper(), "Mono", 12, accent, True))
        if ev.get("title"):
            size = 34 if ev["kind"] in {"id_card", "lower_third", "chapter"} else 26
            body.append((ev["title"], "Display", size, PAL["paper"], True))
        if ev.get("value") is not None:
            v = ev["value"]
            shown = f"{v:,.0f}" if ev.get("fmt") == "comma" else f"{v:g}"
            body.append((f"{shown}{ev.get('suffix','')}", "Display", 30, accent, True))
        for it in (ev.get("items") or [])[:3]:
            body.append((f"{it['label']}   {it['value']}", "Mono", 12, PAL["muted"], False))
        if ev.get("sub"):
            body.append((ev["sub"], "Mono", 13, PAL["muted"], False))

        needed = sum(int(b[2] * 1.5) for b in body) + 20
        ph = max(ph, needed)
        panel(px, py, pw, ph, accent, layers, t0, t1)

        cy = py + 12
        for i, (txt, style, size, color, bold) in enumerate(body):
            stagger = int(60 * i)
            text(layers, [txt], style, px + 16, cy, t0 + stagger / 1000, t1, size, color,
                 bold=bold, spacing=1.0 if style == "Mono" else 0,
                 move=(12, 0) if i == 0 else None,
                 fade=280)
            cy += int(size * 1.5)
    return used


def main() -> None:
    layers: list[str] = []
    used = build(layers)

    header = f"""[Script Info]
; Generated by scripts/make_ffmpeg_ass.py from graphics/timeline.json
; {used} beats · {len(TL['events'])} events in the source timeline
Title: DeepSeek V4.1-Flash 1017 — motion overlay
ScriptType: v4.00+
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: {W}
PlayResY: {H}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Display,DejaVu Sans,30,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
Style: Mono,DejaVu Sans Mono,13,&H00C4A28F,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
Style: Panel,DejaVu Sans,20,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ass = ROOT / "render" / "overlay.ass"
    ass.parent.mkdir(parents=True, exist_ok=True)
    ass.write_text(header + "\n".join(layers) + "\n")

    sh = f"""#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# ffmpeg_overlay.sh — GENERATED by scripts/make_ffmpeg_ass.py
#
# Burns the motion-graphics timeline into the source with ONE native FFmpeg
# pass (libass). No Python, no NLE, no intermediate frames.
#
#   {used} beats compiled from graphics/timeline.json  →  render/overlay.ass
#   regenerate:  python3 scripts/make_ffmpeg_ass.py
#
# usage:
#   bash scripts/ffmpeg_overlay.sh                        # full render
#   bash scripts/ffmpeg_overlay.sh 0 60 out/clip.mp4      # start(s) dur(s) out
#   CODEC=hevc bash scripts/ffmpeg_overlay.sh             # swap encoder
# ---------------------------------------------------------------------------
set -euo pipefail

SRC="${{SRC:-Deepseek strikes again.mp4}}"
START="${{1:-0}}"
DUR="${{2:-}}"                     # empty = to EOF
OUT="${{3:-render/deepseek_overlay_ffmpeg.mp4}}"
CODEC="${{CODEC:-h264}}"
CRF="${{CRF:-20}}"
mkdir -p "$(dirname "$OUT")"

ASS="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/.." && pwd)/render/overlay.ass"

case "$CODEC" in
  h264) ENC=(-c:v libx264 -preset veryfast -crf "$CRF" -pix_fmt yuv420p) ;;
  hevc) ENC=(-c:v libx265 -preset fast -crf "$CRF" -tag:v hvc1 -pix_fmt yuv420p) ;;
  *)    ENC=(-c:v "$CODEC") ;;
esac

TRIM=()
[[ -n "$DUR" ]] && TRIM=(-t "$DUR")

ffmpeg -hide_banner -y \\
  -ss "$START" ${{TRIM[@]+"${{TRIM[@]}}"}} -i "$SRC" \\
  -vf "ass=$ASS" \\
  "${{ENC[@]}}" -c:a copy -movflags +faststart \\
  "$OUT"

echo "wrote $OUT"
"""
    script = ROOT / "scripts" / "ffmpeg_overlay.sh"
    script.write_text(sh)
    script.chmod(0o755)
    print(f"wrote {ass}  ({ass.stat().st_size/1024:.1f} KB, {len(layers)} dialogue lines)")
    print(f"wrote {script}  ({used} beats)")


if __name__ == "__main__":
    main()
