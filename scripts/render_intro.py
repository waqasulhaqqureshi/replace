#!/usr/bin/env python3
"""
render_intro.py — renders the NEW standalone video (48 s · 1920×1080 · 60 fps).

Design: two layers, exactly like the burn-in pipeline.
  1. BACKGROUND — procedural, scene-driven (ignition point, graticule globe,
     mesh morph, shadow geometry, title bowl). Drawn with numpy/PIL.
  2. TYPOGRAPHY — the *same* declarative primitives used for the 27-minute
     burn-in (overlay_lib), fed a dedicated event list below.

That means the new film inherits the brand system for free: identical accent
tokens, easing curves, tracking and card chrome.

    python3 scripts/render_intro.py --out render/intro_1017.mp4
"""
from __future__ import annotations

import argparse
import math
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import overlay_lib as OL  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
W, H = 1920, 1080
FPS = 60
DUR = 48.0

CYAN = (47, 233, 255)
LIME = (182, 255, 60)
AMBER = (255, 176, 32)
ELECTRIC = (77, 107, 254)
MAGENTA = (255, 45, 111)
PAPER = (242, 246, 255)
VOID = (5, 7, 13)


# ---------------------------------------------------------------- scene timing
S = [
    ("ignition", 0.0, 4.2),
    ("graticule", 4.2, 10.5),
    ("kinetic", 10.5, 18.0),
    ("numbers", 18.0, 24.0),
    ("mesh", 24.0, 30.0),
    ("shadow", 30.0, 36.0),
    ("title", 36.0, 43.5),
    ("outro", 43.5, 48.0),
]


def seg(t: float) -> tuple[str, float, float]:
    for name, a, b in S:
        if a <= t < b:
            return name, a, b
    return S[-1][0], S[-1][1], S[-1][2]


def ease_out(p: float) -> float:
    return OL.ease_out(p)


# --------------------------------------------------------------- backgrounds
_BG_CACHE: dict[int, Image.Image] = {}

# 8 pre-rendered grain plates, cycled each frame — reads as continuous film grain
GRAIN = [
    np.random.default_rng(100 + i).normal(0, 2.6, (H, W, 1)).astype(np.int16)
    for i in range(8)
]


def bg_base(t: float) -> Image.Image:
    """Deep navy field with a slow-moving volumetric wash + vignette.

    The washes drift at <0.05 Hz, so the plate is cached on a 0.25 s grid:
    invisible to the eye, ~15x cheaper than rebuilding the blur per frame.
    """
    key = int(t * 4)
    if key in _BG_CACHE:
        return _BG_CACHE[key].copy()
    img = _bg_build(key / 4.0)
    if len(_BG_CACHE) > 64:
        _BG_CACHE.clear()
    _BG_CACHE[key] = img
    return img.copy()


def _bg_build(t: float) -> Image.Image:
    """Uncached plate construction.

    Large-radius blurs are computed at quarter resolution and upscaled: a
    Gaussian at 1/4 scale is visually identical for a 240 px wash but ~16x
    cheaper, which is what makes a 60 fps 1080p render tractable.
    """
    qw, qh = W // 4, H // 4
    img = Image.new("RGB", (W, H), VOID)
    d = ImageDraw.Draw(img)

    # horizon glow (cheap gradient, full res)
    for i in range(70):
        y0 = H * 0.58 + i * 7
        a = int(11 * (1 - i / 70))
        d.rectangle([0, y0, W, y0 + 8], fill=(5 + a, 8 + a, 15 + a * 2))

    # volumetric washes — quarter-res + blur + upscale
    glow = Image.new("RGB", (qw, qh), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for cx, cy, rx, ry, col in (
        (qw * (0.24 + 0.03 * math.sin(t * 0.2)), qh * 0.22, qw * 0.40, qh * 0.34, (26, 38, 96)),
        (qw * (0.84 + 0.02 * math.cos(t * 0.17)), qh * 0.9, qw * 0.34, qh * 0.26, (10, 46, 58)),
    ):
        gd.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=col)
    glow = glow.filter(ImageFilter.GaussianBlur(28)).resize((W, H), Image.BILINEAR)
    img = Image.fromarray(np.clip(np.asarray(img, dtype=np.int16)
                                  + np.asarray(glow, dtype=np.int16), 0, 255).astype(np.uint8))

    # graticule grid
    d = ImageDraw.Draw(img)
    for x in range(0, W, 96):
        d.line([x, 0, x, H], fill=(9, 13, 23))
    for y in range(0, H, 96):
        d.line([0, y, W, y], fill=(8, 12, 21))

    # vignette at quarter res
    v = Image.new("L", (qw, qh), 0)
    ImageDraw.Draw(v).ellipse([-qw * 0.32, -qh * 0.32, qw * 1.32, qh * 1.32], fill=255)
    v = v.filter(ImageFilter.GaussianBlur(56)).resize((W, H), Image.BILINEAR)
    return Image.composite(img, Image.new("RGB", (W, H), (0, 0, 0)), v)


def draw_ignition(img: Image.Image, p: float, t: float) -> None:
    """A single point of light that opens into a horizon line."""
    d = ImageDraw.Draw(img, "RGBA")
    cx, cy = W / 2, H * 0.54
    r = 2 + 190 * ease_out(min(p * 1.6, 1))
    for i in range(18, 0, -1):
        a = int(120 * (1 - i / 18) ** 2)
        rr = r * (i / 18) * 1.6
        d.ellipse([cx - rr, cy - rr * 0.42, cx + rr, cy + rr * 0.42], fill=CYAN + (max(a, 0),))
    d.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=(255, 255, 255, 255))
    # horizon line sweeps out
    lw = W * 1.05 * ease_out(OL.clamp01((p - 0.25) / 0.75))
    if lw > 2:
        d.line([cx - lw / 2, cy, cx + lw / 2, cy], fill=CYAN + (140,), width=2)
        d.line([cx - lw / 2, cy, cx + lw / 2, cy], fill=CYAN + (40,), width=6)


def draw_graticule(img: Image.Image, p: float, t: float) -> None:
    """Wireframe sphere: meridians + parallels, rotating."""
    d = ImageDraw.Draw(img, "RGBA")
    cx, cy = W * 0.5, H * 0.52
    R = 300 * (0.85 + 0.15 * ease_out(p))
    alpha = int(200 * ease_out(OL.clamp01(p * 2)))
    rot = t * 0.42
    # parallels
    for i in range(1, 7):
        lat = -math.pi / 2 + math.pi * i / 7
        ry = R * math.cos(lat) * 0.34
        y = cy + R * math.sin(lat)
        rw = R * math.cos(lat)
        d.ellipse([cx - rw, y - ry, cx + rw, y + ry], outline=CYAN + (alpha // 3,), width=1)
    # meridians
    for i in range(12):
        ang = rot + i * math.pi / 6
        rw = abs(math.cos(ang)) * R
        d.ellipse([cx - max(rw, 1), cy - R, cx + max(rw, 1), cy + R],
                  outline=(CYAN + (alpha // 3,)) if i % 3 else (CYAN + (alpha,)), width=1)
    d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=CYAN + (alpha,), width=2)
    # rotating orbit ticks
    for i in range(48):
        a = rot * 1.6 + i * math.pi / 24
        r0, r1 = R * 1.06, R * (1.11 if i % 4 else 1.16)
        d.line([cx + math.cos(a) * r0, cy + math.sin(a) * r0,
                cx + math.cos(a) * r1, cy + math.sin(a) * r1],
               fill=CYAN + (110,), width=1)


def draw_mesh(img: Image.Image, p: float, t: float) -> None:
    """Cube wireframe that relaxes toward a sphere — 'wish → built artefact'."""
    d = ImageDraw.Draw(img, "RGBA")
    cx, cy = W * 0.68, H * 0.52
    R = 168
    rot = t * 0.55
    verts = []
    for i in range(8):
        x = R if i & 1 else -R
        y = R if i & 2 else -R
        z = R if i & 4 else -R
        # rotate on Y
        xr = x * math.cos(rot) - z * math.sin(rot)
        zr = x * math.sin(rot) + z * math.cos(rot)
        # perspective
        f = 1.55 / (1.55 + zr / R)          # gentler perspective → stays in frame
        verts.append((cx + xr * 0.62 * f, cy + y * 0.62 * f, zr))
    # morph: blend cube vertices toward a sphere (interpolate with p)
    sphere = []
    for i, (x, y, z) in enumerate(verts):
        ang = i / 8 * 2 * math.pi
        sx = cx + math.cos(ang + rot) * R * 0.68
        sy = cy + math.sin(ang + rot * 1.3) * R * 0.68
        q = ease_out(OL.clamp01((p - 0.45) / 0.55))
        sphere.append((x + (sx - x) * q, y + (sy - y) * q))
    edges = []
    for i in range(8):
        for j in range(i + 1, 8):
            if bin(i ^ j).count("1") == 1:
                edges.append((i, j))
    a = int(255 * ease_out(OL.clamp01(p * 2.4)))
    for i, j in edges:
        d.line([sphere[i][0], sphere[i][1], sphere[j][0], sphere[j][1]],
               fill=CYAN + (int(a * 0.62),), width=2)
    for i, (x, y) in enumerate(sphere):
        rr = 4.2
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=LIME + (a,))


def draw_shadow(img: Image.Image, p: float, t: float) -> None:
    """The Eratosthenes callback: vertical stick, sun ray, 7.2° wedge."""
    d = ImageDraw.Draw(img, "RGBA")
    bx, by = W * 0.56, H * 0.74
    stick_h = 380
    d.line([bx, by, bx, by - stick_h], fill=PAPER + (220,), width=3)
    # sun rays
    for i in range(5):
        y = by - stick_h + 26 + i * 62
        ln = 200 + 40 * math.sin(t * 0.6 + i)
        d.line([bx + 120, y, bx + 120 + ln, y], fill=AMBER + (90,), width=1)
    # angle wedge, drawn progressively
    sweep = ease_out(OL.clamp01(p * 1.3)) * 7.2
    if sweep > 0.1:
        r = 150
        bbox = [bx - r, by - stick_h - r, bx + r, by - stick_h + r]
        d.arc(bbox, 90 - sweep, 90, fill=AMBER + (240,), width=3)
        # shadow on the ground
        sh = math.tan(math.radians(sweep)) * stick_h
        d.line([bx, by, bx + sh * 3.2, by], fill=CYAN + (200,), width=2)
    d.line([bx - 60, by, bx + 420, by], fill=(255, 255, 255, 60), width=1)


def draw_title_bowl(img: Image.Image, p: float, t: float) -> None:
    """Concentric rings + sweeping arc behind the title lockup."""
    d = ImageDraw.Draw(img, "RGBA")
    cx, cy = W * 0.5, H * 0.5
    for i in range(6):
        rad = 260 + i * 96
        a = int((110 - i * 14) * ease_out(OL.clamp01(p * 1.2)))
        d.ellipse([cx - rad, cy - rad * 0.62, cx + rad, cy + rad * 0.62],
                  outline=CYAN + (max(a, 0),), width=1)
    ang = t * 40
    d.arc([cx - 700, cy - 430, cx + 700, cy + 430], ang, ang + 60,
          fill=LIME + (180,), width=2)


# ------------------------------------------------------------- typography list
# Same event schema as graphics/timeline.json → same primitives, same motion.
EVENTS = [
    dict(id="i01", t0=0.6, t1=4.2, kind="corner", box=[0.055, 0.80, 0.36, 0.12],
         motion="slide_up", accent="cyan", kicker="BUILD 1017 · OCT 17",
         title="a new model, released in public"),
    dict(id="i02", t0=4.4, t1=10.2, kind="chapter", box=[0.075, 0.30, 0.62, 0.34],
         motion="slide_up", accent="paper", kicker="01 · THE FIELD", hero=True,
         title="Every model predicts.", sub="Few can build."),
    dict(id="i03", t0=10.7, t1=13.6, kind="chapter", box=[0.075, 0.34, 0.55, 0.28],
         motion="slide_up", accent="paper", kicker="02 · THE LOOP", title="Prompt."),
    dict(id="i04", t0=13.7, t1=16.0, kind="chapter", box=[0.075, 0.34, 0.55, 0.28],
         motion="slide_up", accent="paper", kicker="02 · THE LOOP", title="Agent."),
    dict(id="i05", t0=16.1, t1=17.9, kind="chapter", box=[0.075, 0.34, 0.62, 0.28],
         motion="slide_up", accent="lime", kicker="02 · THE LOOP", title="Artefact."),
    dict(id="i06", t0=18.3, t1=24.0, kind="stat", box=[0.075, 0.22, 0.26, 0.20],
         motion="pop", accent="cyan", value=155, suffix="T", fmt="comma",
         label="tokens / day", sub="single cluster"),
    dict(id="i07", t0=18.7, t1=24.0, kind="stat", box=[0.365, 0.22, 0.26, 0.20],
         motion="pop", accent="lime", value=1000000, fmt="compact",
         label="context window", sub="in one pass"),
    dict(id="i08", t0=19.1, t1=24.0, kind="stat", box=[0.655, 0.22, 0.26, 0.20],
         motion="pop", accent="amber", value=42.0, suffix="%", fmt="comma",
         label="HLE (no tools)", sub="42.6 with tools"),
    dict(id="i09", t0=24.3, t1=30.0, kind="callout", box=[0.06, 0.30, 0.30, 0.24],
         motion="slide_up", accent="lime", kicker="WISH-DRIVEN",
         title="Say the outcome.", sub="the harness finds the path",
         items=[dict(label="intent", value="→"), dict(label="tools", value="12")]),
    dict(id="i10", t0=30.3, t1=36.0, kind="equation", box=[0.06, 0.26, 0.30, 0.20],
         motion="slide_up", accent="amber", title="7.2° = 1/50",
         sub="two cities · one shadow"),
    dict(id="i11", t0=36.4, t1=43.3, kind="chapter", box=[0.115, 0.33, 0.77, 0.40],
         motion="pop", accent="paper", kicker="DEEPSEEK", hero=True,
         title="V4.1-Flash 1017", sub="wish-driven programming"),
    dict(id="i12", t0=43.7, t1=47.9, kind="chapter", box=[0.115, 0.34, 0.77, 0.34],
         motion="pop", accent="paper", kicker="OPEN SOURCE · MIT LICENSE", hero=True,
         title="Weights, harness, DeepInfer.", sub="MIT · published today"),
    dict(id="i13", t0=43.9, t1=47.9, kind="corner", box=[0.055, 0.845, 0.44, 0.11],
         motion="slide_up", accent="lime", kicker="DEEPSEEK V4.1-FLASH · 1017",
         title="wish-driven programming"),
]


def render_frame(t: float) -> Image.Image:
    name, a, b = seg(t)
    p = OL.clamp01((t - a) / max(b - a, 1e-3))
    img = bg_base(t)
    if name == "ignition":
        draw_ignition(img, p, t)
    elif name == "graticule":
        draw_graticule(img, p, t)
    elif name == "kinetic":
        draw_graticule(img, OL.clamp01(0.6 + p * 0.6), t)  # keep the globe as a ghost
    elif name == "numbers":
        draw_graticule(img, 0.3, t * 0.4)
    elif name == "mesh":
        draw_mesh(img, p, t)
    elif name == "shadow":
        draw_shadow(img, p, t)
    elif name == "title":
        draw_title_bowl(img, p, t)
    else:
        draw_title_bowl(img, 1.0, t)

    # typographic layer, authored on the same 1280×720 grid → scaled to 1920×1080
    frame = img.convert("RGBA")
    typo = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    for ev in EVENTS:
        if ev["t0"] <= t <= ev["t1"]:
            lay, pos = OL.render_event(1280, 720, ev, t, None)
            if lay is not None:
                typo.alpha_composite(lay, pos)
    typo = typo.resize((W, H), Image.LANCZOS)
    frame.alpha_composite(typo)

    # film finish: subtle grain (tiles precomputed once, cycled per frame)
    arr = np.asarray(frame.convert("RGB"), dtype=np.int16)
    grain = GRAIN[int(t * FPS) % len(GRAIN)]
    arr = np.clip(arr + grain, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="render/intro_1017.mp4")
    ap.add_argument("--audio", default="render/intro_bed.m4a")
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--seconds", type=float, default=DUR)
    args = ap.parse_args()

    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    audio = ROOT / args.audio
    total = int(args.seconds * FPS)

    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "pipe:0"]
    if audio.exists():
        cmd += ["-i", str(audio)]
    cmd += ["-map", "0:v:0"]
    if audio.exists():
        cmd += ["-map", "1:a:0", "-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", str(args.crf),
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-g", str(FPS * 2), str(out)]

    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE, bufsize=W * H * 3 * 4)
    t0 = time.time()
    try:
        for i in range(total):
            enc.stdin.write(render_frame(i / FPS).tobytes())
            if i % (FPS * 4) == 0:
                el = time.time() - t0
                fps = (i + 1) / max(el, 1e-6)
                print(f"  {i/total*100:5.1f}%  {i}/{total}  {fps:4.1f} fps  "
                      f"eta {(total-i)/max(fps,1e-6)/60:4.1f} min", flush=True)
    finally:
        enc.stdin.close()
        enc.wait()
    print(f"[intro] wrote {out}  {out.stat().st_size/1e6:.1f} MB  "
          f"in {(time.time()-t0)/60:.1f} min")


if __name__ == "__main__":
    main()
