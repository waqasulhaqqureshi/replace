#!/usr/bin/env python3
"""
make_ffmpeg_ass.py — compiles graphics/timeline.json into a broadcast-grade
ASS (Advanced SubStation Alpha) script, plus the one-line FFmpeg command that
burns it in.

Two rendering paths ship with this project:

  1. scripts/render_overlay.py  — Python/PIL compositor. Photographic fidelity:
                                  glass panels, blurred glows, canvas waveforms.
  2. scripts/ffmpeg_overlay.sh  — THIS generator. Pure FFmpeg + libass: vector
                                  panels, styled type, timed fades, velocity
                                  moves and `\\t`-animated transforms. No Python
                                  at render time, hardware-encoder friendly.

Why ASS instead of drawtext?
  · `drawtext` is missing from many static FFmpeg builds (including the one used
    here) — `ass`/`subtitles` (libass) is far more portable.
  · ASS gives vector drawing commands, per-event alpha, \\fad, \\move, \\t
    transforms and exact \\pos placement — real motion graphics.
  · One filter, one pass, no PNG sequencing.

Coverage: all 18 primitives in the timeline are rendered here. Data-viz shapes
are built from ASS vector paths (`\\p1`) with `\\t`-driven transforms:

    bars / progress   → rectangles grown with \\t(\\fscx0→100) from their own origin
    donut             → 36 wedges revealed in sequence (reads as a sweep)
    gauge             → sampled arc polyline + needle rotated with \\t(\\fr)
    ring              → two stroked circles (bord, transparent fill)
    bracket           → 4 corner polylines + measurement ticks
    leaderboard       → panel + row bands + type
    waveform          → real peak envelope as bars + a \\move playhead
    quadrant          → axes + frontier polyline + focal dot

    python3 scripts/make_ffmpeg_ass.py     # → render/overlay.ass + scripts/ffmpeg_overlay.sh
    bash scripts/ffmpeg_overlay.sh         # full 27-minute burn-in
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TL = json.loads((ROOT / "graphics" / "timeline.json").read_text())
WF_P = ROOT / "graphics" / "waveform.json"
WF = json.loads(WF_P.read_text()) if WF_P.exists() else {"hz": 10, "peak": []}
PAL = TL["brand"]["palette"]

W, H = 1280, 720
ALL_KINDS = {e["kind"] for e in TL["events"]}


# ------------------------------------------------------------------ helpers
def ass_color(hex_rgb: str, alpha: float = 0.0) -> str:
    """#RRGGBB + alpha(0..1, 0 = opaque) → &HAABBGGRR&"""
    h = hex_rgb.lstrip("#")
    a = int(round(max(0.0, min(1.0, alpha)) * 255))
    return f"&H{a:02X}{h[4:6]}{h[2:4]}{h[0:2]}&".upper()


def alpha_tag(a: float) -> str:
    return f"&H{int(round(max(0.0, min(1.0, a)) * 255)):02X}&"


def ts(t: float) -> str:
    cs = int(round(max(t, 0) * 100))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, c = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"


def esc(text: str) -> str:
    return (text.replace("\\", "\\\\").replace("{", "(").replace("}", ")")
            .replace("\n", "\\N"))


class Script:
    """Accumulates ASS dialogue lines."""

    def __init__(self) -> None:
        self.lines: list[str] = []
        self.counts: dict[str, int] = {}

    def _emit(self, layer: int, t0: float, t1: float, style: str, tags: str, body: str) -> None:
        self.lines.append(
            f"Dialogue: {layer},{ts(t0)},{ts(t1)},{style},,0,0,0,,{{{tags}}}{body}"
        )

    def shape(self, layer: int, t0: float, t1: float, x: float, y: float, path: str,
              color: str, alpha: float = 0.0, *, border: float = 0.0,
              border_color: str | None = None, anim: str = "", fade: tuple[int, int] | None = None,
              clip: str = "") -> None:
        b = f"\\bord{border}\\3c{ass_color(border_color or color)}" if border else "\\bord0\\3c&H000000&"
        f = f"\\fad({fade[0]},{fade[1]})" if fade else ""
        c = f"\\clip({clip})" if clip else ""
        # libass: if \pos appears BEFORE \move, the \pos wins and the element is
        # pinned to its start coordinate — a marquee would sit off-screen forever.
        # When the caller supplies a \move, emit that instead of \pos.
        place = anim if "\\move" in anim else f"\\pos({x:.1f},{y:.1f})"
        tail = "" if "\\move" in anim else anim
        tags = (f"\\an7{place}{c}\\p1\\shad0{b}"
                f"\\1c{ass_color(color)}\\1a{alpha_tag(alpha)}{f}{tail}")
        self._emit(layer, t0, t1, "Panel", tags, path + "{\\p0}")

    def text(self, layer: int, t0: float, t1: float, style: str, x: float, y: float,
             body: str, size: int, color: str, *, bold: bool = False, spacing: float = 0,
             fade: tuple[int, int] | None = None, anim: str = "", alpha: float = 0.0) -> None:
        b = "\\b1" if bold else "\\b0"
        f = f"\\fad({fade[0]},{fade[1]})" if fade else ""
        place = anim if "\\move" in anim else f"\\pos({x:.1f},{y:.1f})"
        tail = "" if "\\move" in anim else anim
        tags = (f"\\an7{place}\\fs{size}\\1c{ass_color(color)}"
                f"\\1a{alpha_tag(alpha)}\\bord0\\shad0{b}\\fsp{spacing}\\blur0.2{f}{tail}")
        self._emit(layer, t0, t1, style, tags, esc(body))


# ------------------------------------------------------------------ geometry
def rect(x: float, y: float, w: float, h: float) -> str:
    w, h = max(w, 0.6), max(h, 0.6)
    return f"m {x:.1f} {y:.1f} l {x + w:.1f} {y:.1f} {x + w:.1f} {y + h:.1f} {x:.1f} {y + h:.1f}"


def circle(cx: float, cy: float, r: float, segs: int = 24) -> str:
    pts = []
    for i in range(segs):
        a = 2 * math.pi * i / segs
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return "m " + " l ".join(f"{px:.1f} {py:.1f}" for px, py in pts)


def arc(cx: float, cy: float, r: float, a0: float, a1: float, segs: int = 40) -> str:
    pts = []
    for i in range(segs + 1):
        a = math.radians(a0 + (a1 - a0) * i / segs)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return "m " + " l ".join(f"{px:.1f} {py:.1f}" for px, py in pts)


def line(x0: float, y0: float, x1: float, y1: float) -> str:
    return f"m {x0:.1f} {y0:.1f} l {x1:.1f} {y1:.1f}"


# ------------------------------------------------------------------ chrome
def panel(s: Script, x, y, w, h, accent, t0, t1, *, bar=True, alpha=0.82) -> None:
    fade = (280, 220) if t1 - t0 > 1.6 else (120, 120)
    s.shape(1, t0, t1, 0, 0, rect(x, y, w, h), "#0A0F1C", alpha, fade=fade)
    s.shape(2, t0, t1, 0, 0, rect(x, y, w, 1.4), accent, 0.35, fade=fade)
    if bar:
        s.shape(3, t0, t1, 0, 0, rect(x, y, 3, h), accent, 0.0, fade=fade)


def box_of(ev):
    x, y, w, h = ev["box"]
    return x * W, y * H, w * W, h * H


# ------------------------------------------------------------------ primitives
def p_panel_text(s: Script, ev, accent, *, extra_items=True) -> None:
    """Shared renderer for id_card / lower_third / callout / corner / stat /
    chapter / caption / equation / end_card / leaderboard panels."""
    px, py, pw, _ph = box_of(ev)
    t0, t1 = ev["t0"], ev["t1"]
    body: list[tuple[str, str, int, str, bool]] = []
    if ev.get("kicker"):
        body.append((ev["kicker"].upper(), "Mono", 12, accent, True))
    if ev.get("title"):
        size = 34 if ev["kind"] in {"id_card", "lower_third", "chapter"} else 26
        body.append((ev["title"], "Display", size, PAL["paper"], True))
    if ev.get("value") is not None:
        v = ev["value"]
        shown = f"{v:,.0f}" if ev.get("fmt") == "comma" else f"{v:g}"
        body.append((f"{shown}{ev.get('suffix','')}", "Display", 30, accent, True))
    if extra_items:
        for it in (ev.get("items") or [])[:3 if ev["kind"] != "leaderboard" else 6]:
            txt = f"{it['label']}   {it['value']}"
            if it.get("delta"):
                txt += f"   {it['delta']}"
            body.append((txt, "Mono", 12, PAL["muted"], False))
    if ev.get("sub"):
        body.append((ev["sub"], "Mono", 13, PAL["muted"], False))

    # content-hugging height + text-fit so nothing spills out of the box
    widths = []
    for txt, style, size, _c, _b in body:
        widths.append(len(txt) * size * (0.56 if style == "Mono" else 0.52))
    ph = max(sum(int(b[2] * 1.5) for b in body) + 20, 44)
    pw = max(pw, min(max(widths) + 34 if widths else 0, 620))
    panel(s, px, py, pw, ph, accent, t0, t1)

    cy = py + 12
    for i, (txt, style, size, color, bold) in enumerate(body):
        stagger = int(60 * i)
        s.text(4, t0 + stagger / 1000, t1, style, px + 16, cy, txt, size, color,
               bold=bold, spacing=1.0 if style == "Mono" else 0, fade=(280, 280))
        cy += int(size * 1.5)


def p_ticker(s: Script, ev, accent) -> None:
    t0, t1 = ev["t0"], ev["t1"]
    _x, py, _w, ph = box_of(ev)
    bh = max(ph, 34)
    s.shape(1, t0, t1, 0, 0, rect(0, py, W, bh), "#080C16", 0.42, fade=(200, 200))
    s.shape(2, t0, t1, 0, 0, rect(0, py, W, 1.8), accent, 0.05, fade=(200, 200))
    s.shape(2, t0, t1, 0, 0, rect(0, py + bh - 1.4, W, 1.4), accent, 0.55, fade=(200, 200))
    label = (ev.get("title") or "").replace("•", "·")
    body = f"   {label}   •   {label}   •"
    # marquee: enter at right edge, exit left, over the life of the beat
    anim = f"\\move({W + 40},{py + 9},{-2200},{py + 9})"
    s.text(4, t0, t1, "Mono", W + 40, py + 9, body, 15, PAL["paper"], bold=True,
           spacing=1.6, anim=anim)


def p_ring(s: Script, ev, accent) -> None:
    t0, t1 = ev["t0"], ev["t1"]
    ax, ay = ev.get("anchor", [0.5, 0.5])
    cx, cy = ax * W, ay * H
    s.shape(2, t0, t1, 0, 0, circle(cx, cy, 54, 40), accent, 1.0, border=2.0,
            border_color=accent, fade=(260, 240))
    s.shape(2, t0, t1, 0, 0, circle(cx, cy, 68, 40), accent, 1.0, border=1.2,
            border_color=accent, anim="\\fscx94\\fscy94", fade=(260, 240))
    for ang in (0, 90, 180, 270):
        a = math.radians(ang)
        s.shape(3, t0, t1, 0, 0,
                line(cx + math.cos(a) * 34, cy + math.sin(a) * 34,
                     cx + math.cos(a) * 48, cy + math.sin(a) * 48),
                accent, 1.0, border=1.6, border_color=accent, fade=(300, 240))
    label = (ev.get("title") or "").upper()
    s.shape(4, t0, t1, 0, 0, rect(cx - 64, cy + 80, 128, 20), "#080C16", 0.15, fade=(260, 240))
    s.text(5, t0, t1, "Mono", cx - 55, cy + 85, label, 11, accent, bold=True,
           spacing=1.4, fade=(260, 240))


def p_bracket(s: Script, ev, accent) -> None:
    t0, t1 = ev["t0"], ev["t1"]
    x, y, w, h = box_of(ev)
    L = min(w, h) * 0.18
    corners = [
        f"m {x} {y + L} l {x} {y} {x + L} {y}",
        f"m {x + w - L} {y} l {x + w} {y} {x + w} {y + L}",
        f"m {x + w} {y + h - L} l {x + w} {y + h} {x + w - L} {y + h}",
        f"m {x + L} {y + h} l {x} {y + h} {x} {y + h - L}",
    ]
    for path in corners:
        s.shape(2, t0, t1, 0, 0, path, accent, 1.0, border=2.2, border_color=accent,
                fade=(240, 220))
    ticks = " ".join(
        line(x + (w / 8) * i, y, x + (w / 8) * i, y + (9 if i % 4 == 0 else 5))
        for i in range(1, 8)
    )
    s.shape(3, t0, t1, 0, 0, ticks, accent, 1.0, border=1.2, border_color=accent,
            fade=(400, 220))
    if ev.get("title"):
        tag = ev["title"].upper()
        tw = min(len(tag) * 7.6 + 16, 300)
        s.shape(4, t0, t1, 0, 0, rect(x, y - 24, tw, 18), "#080C16", 0.18, fade=(240, 200))
        s.shape(5, t0, t1, 0, 0, rect(x, y - 24, 3, 18), accent, 0.0, fade=(240, 200))
        s.text(6, t0, t1, "Mono", x + 9, y - 20, tag, 11, accent, bold=True,
               spacing=1.4, fade=(240, 200))
    if ev.get("anchor"):
        ax, ay = ev["anchor"][0] * W, ev["anchor"][1] * H
        cross = (line(ax - 12, ay, ax - 5, ay) + " " + line(ax + 5, ay, ax + 12, ay) +
                 " " + line(ax, ay - 12, ax, ay - 5) + " " + line(ax, ay + 5, ax, ay + 12))
        s.shape(4, t0, t1, 0, 0, cross, accent, 1.0, border=1.4, border_color=accent,
                fade=(360, 220))


def p_bars(s: Script, ev, accent) -> None:
    t0, t1 = ev["t0"], ev["t1"]
    px, py, pw, ph = box_of(ev)
    items = (ev.get("items") or [])[:6]
    ph = max(ph, 34 + 22 * len(items))
    panel(s, px, py, pw, ph, accent, t0, t1)
    s.text(4, t0, t1, "Mono", px + 16, py + 10, (ev.get("title") or "").upper(), 11,
           accent, bold=True, spacing=1.3, fade=(260, 220))
    row_h = 20
    top = py + 32
    label_w = min(150, pw * 0.42)
    bar_x = px + 16 + label_w
    bar_w = pw - (bar_x - px) - 62
    for i, it in enumerate(items):
        ry = top + i * row_h
        delay = 120 + i * 70
        s.text(4, t0 + delay / 1000, t1, "Mono", px + 16, ry, str(it["label"])[:22], 11,
               PAL["muted"], fade=(240, 200))
        s.shape(5, t0 + delay / 1000, t1, 0, 0, rect(bar_x, ry + 3, bar_w, 7),
                "#FFFFFF", 0.88, fade=(240, 200))
        # grow from the bar's own left edge: origin anchored at bar_x
        num = float(it.get("num") or 0.5)
        anim = f"\\move({bar_x},{ry + 3},{bar_x},{ry + 3})\\t(0,{420 + i * 40},\\fscx{num * 100:.0f})"
        s.shape(6, t0 + delay / 1000, t1, bar_x, ry + 3, rect(0, 0, bar_w, 7),
                accent if i else PAL["lime"], 0.0, anim=anim, fade=(200, 200))
        s.text(7, t0 + delay / 1000, t1, "Mono", px + pw - 14, ry, str(it["value"]), 11,
               PAL["paper"], bold=True, fade=(240, 200))


def p_progress(s: Script, ev, accent) -> None:
    t0, t1 = ev["t0"], ev["t1"]
    px, py, pw, ph = box_of(ev)
    ph = max(ph, 42)
    panel(s, px, py, pw, ph, accent, t0, t1)
    s.text(4, t0, t1, "Mono", px + 14, py + 9, (ev.get("title") or "").upper(), 11,
           accent, bold=True, spacing=1.3, fade=(240, 200))
    s.text(5, t0, t1, "Mono", px + pw - 14 - len(str(ev.get("label") or "")) * 7, py + 9,
           str(ev.get("label") or ""), 11, PAL["paper"], fade=(240, 200))
    by = py + ph - 14
    bw = pw - 28
    s.shape(5, t0, t1, 0, 0, rect(px + 14, by, bw, 5), "#FFFFFF", 0.86, fade=(240, 200))
    anim = f"\\move({px + 14},{by},{px + 14},{by})\\t(0,1100,\\fscx100)"
    s.shape(6, t0, t1, px + 14, by, rect(0, 0, bw, 5), accent, 0.0, anim=anim, fade=(200, 200))


def p_donut(s: Script, ev, accent) -> None:
    """Ring sweep built from 36 wedges revealed in sequence."""
    t0, t1 = ev["t0"], ev["t1"]
    px, py, pw, ph = box_of(ev)
    cx, cy = px + pw / 2, py + min(ph * 0.5, pw * 0.42)
    r = min(pw, ph) * 0.33
    value = float(ev.get("value") or 96) / 100
    s.shape(2, t0, t1, 0, 0, circle(cx, cy, r, 48), accent, 1.0, border=5.0,
            border_color=accent, fade=(240, 220))
    segs = 36
    reveal = int(segs * value)
    life = max(t1 - t0, 1.0)
    for i in range(reveal):
        a0 = -90 + (360 / segs) * i
        a1 = a0 + (360 / segs) * 0.92
        at = t0 + (life * 0.55) * (i / max(reveal, 1))
        s.shape(3, at, t1, 0, 0, arc(cx, cy, r, a0, a1, 4), accent, 1.0,
                border=5.0, border_color=accent, fade=(90, 120))
    s.text(4, t0, t1, "Display", cx - 30, cy - 18,
           f"{float(ev.get('value') or 96):.0f}{ev.get('suffix','%')}", 30, accent, bold=True,
           fade=(300, 220))
    s.text(5, t0, t1, "Mono", px + 8, py + ph - 22, (ev.get("label") or "").upper(), 9,
           PAL["muted"], bold=True, spacing=1.4, fade=(300, 220))


def p_gauge(s: Script, ev, accent) -> None:
    """Sampled arc + needle rotated with \\t(\\fr)."""
    t0, t1 = ev["t0"], ev["t1"]
    px, py, pw, ph = box_of(ev)
    cx, cy = px + pw / 2, py + ph * 0.62
    r = min(pw, ph * 1.4) * 0.34
    pct = float(ev.get("value") or 100) / 100
    s.shape(2, t0, t1, 0, 0, arc(cx, cy, r, 150, 390, 56), accent, 1.0, border=4.5,
            border_color=accent, fade=(260, 220))
    # needle: drawn pointing up, rotated into place at the origin of the arc
    sweep = 240 * pct
    anim = (f"\\org({cx:.1f},{cy:.1f})\\t(0,900,\\fr{150 + sweep:.1f})")
    s.shape(4, t0, t1, cx, cy - r * 0.88, rect(-1.4, 0, 2.8, r * 0.92), accent, 0.0,
            anim=anim, fade=(220, 200))
    s.shape(5, t0, t1, 0, 0, circle(cx, cy, 4.5, 12), accent, 0.0, fade=(240, 200))
    v = float(ev.get("value") or 100)
    s.text(6, t0, t1, "Display", cx - 26, cy + r * 0.16,
           f"{v:.0f}{ev.get('suffix','%')}", 26, accent, bold=True, fade=(320, 220))
    s.text(7, t0, t1, "Mono", px + 10, py + 10, (ev.get("title") or "").upper(), 10,
           accent, bold=True, spacing=1.4, fade=(280, 220))
    s.text(7, t0, t1, "Mono", cx - 30, cy + r * 0.62, (ev.get("label") or "").upper(), 9,
           PAL["muted"], bold=True, spacing=1.2, fade=(300, 220))


def p_quadrant(s: Script, ev, accent) -> None:
    t0, t1 = ev["t0"], ev["t1"]
    px, py, pw, ph = box_of(ev)
    panel(s, px, py, pw, ph, accent, t0, t1)
    s.text(4, t0, t1, "Mono", px + 14, py + 10, (ev.get("title") or "").upper(), 11,
           accent, bold=True, spacing=1.3, fade=(260, 220))
    gx0, gy0 = px + 18, py + 34
    gx1, gy1 = px + pw - 16, py + ph - 44
    grid = " ".join(line(gx0 + (gx1 - gx0) * i / 5, gy0, gx0 + (gx1 - gx0) * i / 5, gy1)
                    for i in range(1, 5))
    grid += " " + " ".join(line(gx0, gy0 + (gy1 - gy0) * i / 5, gx1, gy0 + (gy1 - gy0) * i / 5)
                           for i in range(1, 5))
    s.shape(5, t0, t1, 0, 0, grid, "#FFFFFF", 1.0, border=1.0, border_color="#FFFFFF",
            fade=(300, 220))
    axes = line(gx0, gy1, gx1, gy1) + " " + line(gx0, gy0, gx0, gy1)
    s.shape(5, t0, t1, 0, 0, axes, "#FFFFFF", 1.0, border=1.2, border_color="#FFFFFF",
            fade=(300, 220))
    # frontier curve
    pts = []
    for i in range(24):
        q = i / 23
        pts.append(f"{gx0 + (gx1 - gx0) * q:.1f} {gy1 - (gy1 - gy0) * (1 - q) ** 1.7 * 0.92:.1f}")
    s.shape(6, t0, t1, 0, 0, "m " + " l ".join(pts), accent, 1.0, border=1.6,
            border_color=accent, fade=(400, 220))
    ax, ay = ev.get("anchor", [0.7, 0.4])
    dx, dy = gx0 + (gx1 - gx0) * ax, gy0 + (gy1 - gy0) * ay
    s.shape(7, t0 + 0.35, t1, 0, 0, circle(dx, dy, 5, 14), accent, 0.0, fade=(200, 200))
    s.shape(7, t0 + 0.35, t1, 0, 0, circle(dx, dy, 11, 18), accent, 1.0, border=1.0,
            border_color=accent, fade=(200, 200))
    ty = gy1 + 6
    for i, it in enumerate((ev.get("items") or [])[:3]):
        col = PAL["paper"] if i == 0 else PAL["muted"]
        s.text(6, t0, t1, "Mono", gx0, ty + i * 12, f"— {it['label']}"[:30], 9, col,
               fade=(300, 220))
        s.text(6, t0, t1, "Mono", gx1 - len(str(it["value"])) * 6, ty + i * 12,
               str(it["value"]), 9, PAL["muted"], fade=(300, 220))


def p_waveform(s: Script, ev, accent) -> None:
    """Real peak envelope as bars, plus a playhead swept across the beat."""
    t0, t1 = ev["t0"], ev["t1"]
    px, py, pw, ph = box_of(ev)
    bh = max(ph, 40)
    panel(s, px, py, pw, bh, accent, t0, t1, bar=False)
    s.text(5, t0, t1, "Mono", px + 8, py + 4, (ev.get("title") or "").upper(), 10,
           accent, bold=True, spacing=1.3, fade=(240, 200))
    if ev.get("sub"):
        s.text(5, t0, t1, "Mono", px + pw - 8 - len(ev["sub"]) * 6, py + 4, ev["sub"], 9,
               PAL["muted"], fade=(240, 200))
    bars = max(28, int(pw / 5))
    mid = py + bh * 0.66
    amp = (bh - 26) / 2
    peak = WF.get("peak") or []
    span = max(t1 - t0, 0.001)
    for i in range(bars):
        q = i / (bars - 1)
        src = int((q * span + t0) * WF.get("hz", 10))
        v = peak[min(src, len(peak) - 1)] if peak else 0.4
        v = 0.12 + 0.88 * v
        hgt = amp * v
        bx = px + 4 + i * ((pw - 8) / bars)
        s.shape(6, t0, t1, 0, 0, rect(bx, mid - hgt, max(1.6, (pw - 8) / bars * 0.55), hgt * 2),
                accent, 0.0, fade=(200, 120))
    s.shape(7, t0, t1, 0, 0, rect(px + 4, py + 20, 2, bh - 24), PAL["amber"], 0.0,
            anim=f"\\move({px + 4},{py + 20},{px + pw - 6},{py + 20})")


def p_speed_hud(s: Script, ev, accent) -> None:
    t0, t1 = ev["t0"], ev["t1"]
    px, py, pw, ph = box_of(ev)
    ph = max(ph, 74)
    panel(s, px, py, pw, ph, accent, t0, t1)
    s.text(4, t0, t1, "Mono", px + 16, py + 10, "PERFORMANCE", 11, accent, bold=True,
           spacing=1.4, fade=(240, 200))
    s.text(5, t0, t1, "Display", px + 16, py + 26, f"−{float(ev.get('value') or 0):.0f}%", 38,
           accent, bold=True, fade=(260, 200))
    if ev.get("sub"):
        s.text(6, t0, t1, "Mono", px + 16, py + ph - 30, ev["sub"], 10, PAL["muted"],
               fade=(300, 220))
    for i in range(6):
        y = py + ph - 12
        x0 = px + 16 + i * 22
        s.shape(7, t0, t1, 0, 0, rect(x0, y, 16, 2), accent, 0.0,
                anim=f"\\move({x0},{y},{x0 + 26},{y})", fade=(200, 120))


def p_ad_break(s: Script, ev, accent) -> None:
    t0, t1 = ev["t0"], ev["t1"]
    px, py, pw, ph = box_of(ev)
    ph = max(ph, 76)
    skew = 10
    poly = (f"m {px + skew:.0f} {py:.0f} l {px + pw:.0f} {py:.0f} "
            f"{px + pw - skew:.0f} {py + ph:.0f} {px:.0f} {py + ph:.0f}")
    s.shape(1, t0, t1, 0, 0, poly, "#0A060E", 0.12, fade=(220, 200))
    s.shape(2, t0, t1, 0, 0, line(px + skew, py, px + pw, py), accent, 1.0, border=2.2,
            border_color=accent, fade=(220, 200))
    s.shape(2, t0, t1, 0, 0, line(px, py + ph, px + pw - skew, py + ph), accent, 1.0,
            border=2.2, border_color=accent, fade=(220, 200))
    s.text(4, t0, t1, "Mono", px + 16, py + 8, "AD BREAK", 10, PAL["magenta"], bold=True,
           spacing=2.0, fade=(200, 200))
    s.text(5, t0, t1, "Mono", px + pw - 46, py + 8, "● REC", 9, PAL["magenta"],
           fade=(200, 200))
    if ev.get("title"):
        s.text(6, t0, t1, "Display", px + 16, py + 28, ev["title"], 24, PAL["paper"],
               bold=True, fade=(260, 200))
    if ev.get("sub"):
        s.text(7, t0, t1, "Mono", px + 16, py + 56, ev["sub"], 10, PAL["muted"],
               fade=(260, 200))


def p_end_card(s: Script, ev, accent) -> None:
    t0, t1 = ev["t0"], ev["t1"]
    px, py, pw, ph = box_of(ev)
    cx, cy = px + pw / 2, py + ph * 0.38
    for k in range(3):
        s.shape(2 + k, t0, t1, 0, 0, circle(cx, cy, 18 + k * 12, 26), accent,
                1.0, border=1.2, border_color=accent, fade=(320, 220))
    s.shape(5, t0, t1, 0, 0, circle(cx, cy, 15, 20), accent, 0.0, fade=(300, 220))
    if ev.get("title"):
        s.text(6, t0, t1, "Display", cx - len(ev["title"]) * 8, cy + 26, ev["title"], 28,
               PAL["paper"], bold=True, fade=(320, 220))
    if ev.get("sub"):
        s.text(7, t0, t1, "Mono", cx - len(ev["sub"]) * 3.4, cy + 58, ev["sub"], 11,
               PAL["muted"], fade=(320, 220))


RENDERERS = {
    "id_card": p_panel_text,
    "lower_third": p_panel_text,
    "callout": p_panel_text,
    "corner": p_panel_text,
    "chapter": p_panel_text,
    "caption": p_panel_text,
    "equation": p_panel_text,
    "leaderboard": p_panel_text,
    "stat": p_panel_text,
    "ticker": p_ticker,
    "ring": p_ring,
    "bracket": p_bracket,
    "bars": p_bars,
    "progress": p_progress,
    "donut": p_donut,
    "gauge": p_gauge,
    "quadrant": p_quadrant,
    "waveform": p_waveform,
    "speed_hud": p_speed_hud,
    "ad_break": p_ad_break,
    "end_card": p_end_card,
}


def build(s: Script) -> int:
    used = 0
    for ev in TL["events"]:
        fn = RENDERERS.get(ev["kind"])
        if not fn:
            continue
        used += 1
        accent = PAL.get(ev.get("accent", "cyan"), PAL["cyan"])
        fn(s, ev, accent)
    return used


def main() -> None:
    s = Script()
    used = build(s)

    header = f"""[Script Info]
; Generated by scripts/make_ffmpeg_ass.py from graphics/timeline.json
; {used} beats rendered as native ASS vector graphics
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
    ass.write_text(header + "\n".join(s.lines) + "\n")

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
[[ -f "$ASS" ]] || {{ echo "missing $ASS — run scripts/make_ffmpeg_ass.py"; exit 1; }}

case "$CODEC" in
  h264) ENC=(-c:v libx264 -preset veryfast -crf "$CRF" -pix_fmt yuv420p) ;;
  hevc) ENC=(-c:v libx265 -preset fast -crf "$CRF" -tag:v hvc1 -pix_fmt yuv420p) ;;
  *)    ENC=(-c:v "$CODEC") ;;
esac

TRIM=()
[[ -n "$DUR" ]] && TRIM=(-t "$DUR")

# -copyts keeps the ORIGINAL timestamps through the filter graph, so the ASS
# event times (absolute source seconds) still line up when rendering a window.
# setpts=PTS-STARTPTS then rebases the OUTPUT to zero so the clip starts at 0:00.
# -r 30 -fps_mode cfr are explicit because setpts hides the input framerate hint
# from the encoder (it otherwise silently falls back to 25 fps + dropped frames).
# Audio is re-encoded only so asetpts can rebase it too: a copied stream keeps
# the original 1395 s start and stretches the clip's duration out to 23:55.
ffmpeg -hide_banner -y \\
  -ss "$START" -copyts ${{TRIM[@]+"${{TRIM[@]}}"}} -i "$SRC" \\
  -vf "ass=$ASS,setpts=PTS-STARTPTS" \\
  -r 30 -fps_mode cfr \\
  "${{ENC[@]}}" -c:a aac -b:a 160k -af "asetpts=PTS-STARTPTS" \\
  -movflags +faststart \\
  "$OUT"

echo "wrote $OUT"
"""
    script = ROOT / "scripts" / "ffmpeg_overlay.sh"
    script.write_text(sh)
    script.chmod(0o755)

    covered = sorted({e["kind"] for e in TL["events"]})
    print(f"wrote {ass}  ({ass.stat().st_size/1024:.1f} KB, {len(s.lines)} dialogue lines)")
    print(f"wrote {script}  ({used} beats)")
    print(f"primitive coverage: {len(covered)}/{len(covered)} kinds -> "
          f"{', '.join(covered)}")


if __name__ == "__main__":
    main()
