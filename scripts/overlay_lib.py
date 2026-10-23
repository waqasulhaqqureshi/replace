#!/usr/bin/env python3
"""
overlay_lib.py — resolution-independent motion-graphics renderer.

Every event in graphics/timeline.json is a declarative record:
    {kind, t0, t1, box, accent, motion, copy…}
and this module turns `(event, t)` into an RGBA layer.

Design rules (mirrored 1:1 by the React components in web/src/overlay):
  · all geometry in normalised 0..1 frame coordinates
  · one accent colour per beat, taken from the brand palette
  · 460 ms enter / 340 ms exit, cubic easing, 55 ms stagger per child
  · graphics never cover the measured safe area of the source plate
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")

PALETTE = {
    "void": "#05070D", "ink": "#0B1020", "panel": "#0F1526", "line": "#22304B",
    "cyan": "#2FE9FF", "electric": "#4D6BFE", "lime": "#B6FF3C", "amber": "#FFB020",
    "magenta": "#FF2D6F", "paper": "#F2F6FF", "muted": "#8FA2C4",
}
FACES = {
    "bold": "DejaVuSans-Bold.ttf", "sans": "DejaVuSans.ttf",
    "mono": "DejaVuSansMono.ttf", "mono_bold": "DejaVuSansMono-Bold.ttf",
    "serif": "DejaVuSerif.ttf", "serif_bold": "DejaVuSerif-Bold.ttf",
}

ENTER, EXIT, STAGGER = 0.46, 0.34, 0.055
# current render scale, set once per frame by render_event(); all primitives read it
s = 1.0


def hexrgb(c: str, a: int = 255) -> tuple:
    c = c.lstrip("#")
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), a)


def mix(c1: tuple, c2: tuple, p: float) -> tuple:
    """Blend two RGB (3-tuple) colours."""
    return tuple(int(c1[i] + (c2[i] - c1[i]) * p) for i in range(3))


def mix4(c1: tuple, c2: tuple, p: float) -> tuple:
    """Blend two RGBA colours (keeps alpha)."""
    return tuple(int(c1[i] + (c2[i] - c1[i]) * p) for i in range(4))


# ------------------------------------------------------------------- easing
def clamp01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def ease_out(p: float) -> float:
    p = clamp01(p)
    return 1 - (1 - p) ** 3


def ease_in(p: float) -> float:
    p = clamp01(p)
    return p ** 3


def ease_out_back(p: float, s: float = 1.7) -> float:
    p = clamp01(p) - 1
    return 1 + p * p * ((s + 1) * p + s)


def ease_in_out(p: float) -> float:
    p = clamp01(p)
    return 4 * p ** 3 if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2


def envelope(t: float, t0: float, t1: float, ein: float = ENTER, eout: float = EXIT):
    """Return (alpha, pin, pout) for a beat; pin/pout are 0..1 eased."""
    if t < t0 or t > t1:
        return 0.0, 0.0, 0.0
    pin = clamp01((t - t0) / max(ein, 1e-3))
    pout = clamp01((t1 - t) / max(eout, 1e-3))
    a = ease_out(pin) * (ease_in(pout) if pout < 1 else 1.0)
    return a, ease_out(pin), (ease_in(pout) if pout < 1 else 1.0)


@lru_cache(maxsize=256)
def font(face: str, size: int) -> ImageFont.FreeTypeFont:
    p = FONT_DIR / FACES[face]
    return ImageFont.truetype(str(p), size)


def tw(d: ImageDraw.ImageDraw, s: str, f: ImageFont.FreeTypeFont) -> float:
    if not s:
        return 0.0
    b = d.textbbox((0, 0), s, font=f)
    return b[2] - b[0]


def lh(f) -> float:
    """True line height (ascent + descent) — the safe vertical advance."""
    a, d = f.getmetrics()
    return float(a + d)


def th(f, txt: str) -> float:
    """Measured pixel height of a rendered string (ascender→descender)."""
    b = f.getbbox(txt or "Ag")
    return float(b[3] - b[1])


def fit_size(d, s, face, size, maxw, min_size=9):
    while size > min_size and tw(d, s, font(face, size)) > maxw:
        size -= 1
    return size


def wrap(d, s: str, f, maxw: float) -> list[str]:
    words, lines, cur = s.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if tw(d, trial, f) <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def tracked(d, xy, s: str, f, fill, tracking: float = 0.0, anchor_y="top"):
    """Draw text with letter tracking; returns advance width."""
    x, y = xy
    for ch in s:
        d.text((x, y), ch, font=f, fill=fill, anchor="l" + anchor_y[0])
        x += tw(d, ch, f) + tracking
    return x - xy[0] - tracking


# ------------------------------------------------------------------- surfaces
def _grad(w: int, h: int, top: tuple, bot: tuple) -> Image.Image:
    g = Image.new("RGBA", (1, h))
    px = g.load()
    for y in range(h):
        p = y / max(h - 1, 1)
        px[0, y] = mix4(top, bot, p)
    return g.resize((w, h), Image.BILINEAR)


def glass(w: int, h: int, accent: tuple, strength: float = 1.0,
          radius: int = 12, bar: int = 0) -> Image.Image:
    """Dark-glass panel with accent hairline, inner highlight and optional edge bar."""
    w, h = max(int(w), 4), max(int(h), 4)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    r = min(radius, h // 2)
    body = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(body)
    d.rounded_rectangle([0, 0, w - 1, h - 1], r, fill=(10, 15, 28, int(236 * strength)))
    # top sheen
    sheen = _grad(w, max(2, h // 2), (255, 255, 255, int(18 * strength)), (255, 255, 255, 0))
    body.alpha_composite(sheen, (0, 0))
    # mask to rounded rect
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], r, fill=255)
    body.putalpha(Image.composite(body.getchannel("A"), Image.new("L", (w, h), 0), mask))
    layer.alpha_composite(body)
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle([0, 0, w - 1, h - 1], r, outline=(accent[0], accent[1], accent[2], int(120 * strength)), width=1)
    # corner ticks
    t = max(5, int(min(w, h) * 0.055))
    for cx, cy, dx, dy in ((0, 0, 1, 1), (w - 1, 0, -1, 1), (0, h - 1, 1, -1), (w - 1, h - 1, -1, -1)):
        d.line([cx, cy, cx + dx * t, cy], fill=(accent[0], accent[1], accent[2], int(230 * strength)), width=1)
        d.line([cx, cy, cx, cy + dy * t], fill=(accent[0], accent[1], accent[2], int(230 * strength)), width=1)
    if bar:
        d.rounded_rectangle([0, 0, bar, h - 1], r, fill=(accent[0], accent[1], accent[2], 255))
        d.rectangle([bar // 2, 0, bar, h - 1], fill=(accent[0], accent[1], accent[2], 255))
    return layer


def glow_dot(size: int, color: tuple) -> Image.Image:
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([0, 0, size - 1, size - 1], fill=color)
    return im.filter(ImageFilter.GaussianBlur(size * 0.18))


# ------------------------------------------------------------------- helpers
def kicker_row(layer, d, x, y, kicker, accent, s=1.0, maxw=None):
    """Small tracked mono label with an accent bullet. Returns the next y."""
    size = int(11 * s)
    f = font("mono_bold", size)
    txt = kicker.upper()
    if maxw:
        while size > int(7 * s) and tw(d, txt, font("mono_bold", size)) + 11 * s > maxw:
            size -= 1
            f = font("mono_bold", size)
        # hard truncate as a last resort
        while txt and tw(d, txt, font("mono_bold", size)) + 14 * s > maxw:
            txt = txt[:-1]
    d.rectangle([x, y + 2 * s, x + 5 * s, y + 7 * s], fill=accent)
    tracked(d, (x + 11 * s, y), txt, f, accent, 1.6 * s)
    return y + size + 7 * s


def fmt_num(v: float, fmt: str = "comma", suffix: str = "") -> str:
    if fmt == "comma":
        return f"{v:,.0f}{suffix}"
    if fmt == "compact":
        return (f"{v/1e6:.0f}M" if v >= 1e6 else f"{v/1e3:.0f}K") + suffix
    if fmt == "pct":
        return f"{v:.1f}%"
    return f"{v:g}{suffix}"


def count_at(target: float, p: float, dur_decay: bool = True) -> float:
    """Count-up that decelerates into the final value."""
    p = clamp01(p)
    e = 1 - (1 - p) ** 2.2
    return target * e


def draw_pointer(d: ImageDraw.ImageDraw, from_box, anchor, accent, p=1.0, s=1.0):
    """Elbow leader line from a panel edge to the focal point + ring at the tip."""
    if p <= 0:
        return
    fx = (from_box[0] + from_box[2] / 2)
    fy = (from_box[1] + from_box[3] / 2)
    ax, ay = anchor
    midx = fx + (ax - fx) * 0.55
    pts = [(fx, fy), (midx, fy), (midx, ay), (ax, ay)]
    # partial draw along the polyline
    total = 0.0
    segs = [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    lens = [math.dist(a, b) for a, b in segs]
    total = sum(lens)
    want = total * ease_out(p)
    acc = 0.0
    for (a, b), L in zip(segs, lens):
        if acc >= want:
            break
        f = min(1.0, (want - acc) / max(L, 1e-6))
        d.line([a, (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)],
               fill=accent + (210,), width=max(1, int(1.4 * s)))
        acc += L
    if p > 0.92:
        rr = 5 * s * (1 + 0.25 * math.sin(p * 12))
        d.ellipse([ax - rr, ay - rr, ax + rr, ay + rr], fill=accent + (255,))
        d.ellipse([ax - rr * 1.9, ay - rr * 1.9, ax + rr * 1.9, ay + rr * 1.9],
                  outline=accent + (120,), width=max(1, int(s)))


# ------------------------------------------------------------------- renderers
def _box_px(box, W, H):
    x, y, w, h = box
    return [x * W, y * H, w * W, h * H]


def r_id_card(W, H, ev, t, pin, accent):
    """Nameplate: accent bar, tracked kicker, headline, strapline."""
    x, y, w, _h = _box_px(ev["box"], W, H)
    pad, inner = 18 * s, w - 36 * s
    probe = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    k_size = int(11 * s)
    kick = (ev.get("kicker") or "").upper()
    while k_size > int(7 * s) and tw(probe, kick, font("mono_bold", k_size)) + 14 * s > inner:
        k_size -= 1
    fs_t = fit_size(probe, ev.get("title", ""), "bold", int(29 * s), inner)
    fs_s = fit_size(probe, ev.get("sub", ""), "mono", int(11.5 * s), inner) if ev.get("sub") else 0
    need = pad + k_size + 7 * s
    need += th(font("bold", fs_t), ev.get("title", "")) + 5 * s
    if fs_s:
        need += th(font("mono", fs_s), ev["sub"])
    hh = max(need + pad * 0.9, 62 * s)
    lay = Image.new("RGBA", (int(w), int(hh)), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    lay.alpha_composite(glass(int(w), int(hh), accent, 1.0, int(14 * s), bar=int(max(3, 3 * s))))
    yy = kicker_row(lay, d, pad, pad, kick, accent, s, inner)
    ft = font("bold", fs_t)
    d.text((pad, yy), ev.get("title", ""), font=ft, fill=hexrgb(PALETTE["paper"]), anchor="lt")
    yy += th(ft, ev.get("title", "")) + 5 * s
    if fs_s:
        d.text((pad, yy), ev["sub"], font=font("mono", fs_s),
               fill=hexrgb(PALETTE["muted"]), anchor="lt")
    d.rectangle([pad, hh - 9 * s, pad + (w - pad * 2) * 0.42 * ease_out(pin), hh - 7 * s],
                fill=accent)
    return lay, (x, y)


def r_lower_third(W, H, ev, t, pin, accent):
    return r_id_card(W, H, ev, t, pin, accent)


def r_ticker(W, H, ev, t, p_in, accent, dur, s=1.0):
    x, y, w, h = _box_px(ev["box"], W, H)
    lay = Image.new("RGBA", (int(W), int(max(h, 26 * s))), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    hh = lay.size[1]
    d.rectangle([0, 0, W, hh], fill=(8, 12, 22, 205))
    d.rectangle([0, 0, W, max(1, int(1.5 * s))], fill=accent + (235,))
    d.rectangle([0, hh - max(1, int(1.5 * s)), W, hh], fill=accent + (60,))
    f = font("mono_bold", int(12.5 * s))
    txt = "   •   ".join([ev.get("title", "")] * 3)
    adv = tw(d, ev.get("title", ""), f) + tw(d, "   •   ", f)
    off = (t * 46 * s) % max(adv, 1)
    # scissor by drawing into a mask
    band = Image.new("RGBA", lay.size, (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    cx = -off
    while cx < W:
        bd.text((cx, hh / 2), ev.get("title", ""), font=f, fill=hexrgb(PALETTE["paper"], 235), anchor="lm")
        bd.text((cx + tw(d, ev.get("title", ""), f), hh / 2), "   •   ", font=f,
                fill=accent, anchor="lm")
        cx += adv
    lay.alpha_composite(band)
    # edge fades
    fade = Image.new("RGBA", (int(60 * s), hh), (0, 0, 0, 0))
    for i in range(fade.size[0]):
        a = int(205 * (1 - i / fade.size[0]))
        ImageDraw.Draw(fade).line([(i, 0), (i, hh)], fill=(8, 12, 22, a))
    lay.alpha_composite(fade, (0, 0))
    lay.alpha_composite(fade.transpose(Image.FLIP_LEFT_RIGHT), (int(W - 60 * s), 0))
    return lay, (0, y)


def r_callout(W, H, ev, t, pin, accent):
    """Glass card that hugs its content, laid out in a strict vertical flow."""
    x, y, w, _h = _box_px(ev["box"], W, H)
    pad, inner = 16 * s, w - 32 * s
    # --- measure pass (no drawing) --------------------------------------
    probe = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    k_size = int(11 * s)
    kick = (ev.get("kicker") or "").upper()
    while k_size > int(7 * s) and tw(probe, kick, font("mono_bold", k_size)) + 14 * s > inner:
        k_size -= 1
    need = pad + k_size + 7 * s
    fs_t = fs_v = fs_s = 0
    if ev.get("title"):
        fs_t = fit_size(probe, ev["title"], "bold", int(24 * s), inner)
        need += th(font("bold", fs_t), ev["title"]) + 6 * s
    if "value" in ev:
        vtxt = f"{ev['value']:g}{ev.get('suffix', '')}"
        fs_v = fit_size(probe, vtxt, "bold", int(32 * s), inner)
        need += th(font("bold", fs_v), vtxt) + 5 * s
    n_items = len(ev.get("items", [])[:3])
    need += n_items * 16 * s
    if ev.get("sub"):
        fs_s = fit_size(probe, ev["sub"], "mono", int(11 * s), inner)
        need += th(font("mono", fs_s), ev["sub"])
    hh = max(need + pad * 0.8, 54 * s)
    # --- draw pass ------------------------------------------------------
    lay = Image.new("RGBA", (int(w + 44 * s), int(hh + 34 * s)), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    lay.alpha_composite(glass(int(w), int(hh), accent, 1.0, int(14 * s), bar=int(max(3, 3 * s))))
    yy = kicker_row(lay, d, pad, pad, kick, accent, s, inner)
    if ev.get("title"):
        ft = font("bold", fs_t)
        d.text((pad, yy), ev["title"], font=ft, fill=hexrgb(PALETTE["paper"]), anchor="lt")
        yy += th(ft, ev["title"]) + 6 * s
    if "value" in ev:
        fv = font("bold", fs_v)
        d.text((pad, yy), vtxt, font=fv, fill=accent, anchor="lt")
        yy += th(fv, vtxt) + 5 * s
    for it in ev.get("items", [])[:3]:
        d.rectangle([pad, yy + 4 * s, pad + 3 * s, yy + 7 * s], fill=accent)
        d.text((pad + 10 * s, yy), it["label"], font=font("mono", int(11 * s)),
               fill=hexrgb(PALETTE["muted"]), anchor="lt")
        d.text((w - pad, yy), str(it["value"]), font=font("mono_bold", int(11 * s)),
               fill=hexrgb(PALETTE["paper"]), anchor="rt")
        yy += 16 * s
    if ev.get("sub"):
        f = font("mono", fs_s)
        d.text((pad, yy), ev["sub"], font=f, fill=hexrgb(PALETTE["muted"]), anchor="lt")
    if ev.get("pointer") and ev.get("anchor"):
        ax, ay = ev["anchor"][0] * W - x, ev["anchor"][1] * H - y
        draw_pointer(ImageDraw.Draw(lay), (0, 0, w, hh), (ax, ay), accent, pin, s)
    return lay, (x, y)


def r_stat(W, H, ev, t, pin, accent):
    """Big number, label, optional sub — vertically centred, count-up on entry."""
    x, y, w, h = _box_px(ev["box"], W, H)
    lay = Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    lay.alpha_composite(glass(int(w), int(h), accent, 0.94, int(14 * s), bar=int(max(3, 3 * s))))
    pad, inner = 15 * s, w - 30 * s
    target = float(ev.get("value", 0))
    txt = fmt_num(count_at(target, pin), ev.get("fmt", "comma"), ev.get("suffix", ""))
    fs = fit_size(d, txt, "bold", int(38 * s), inner)
    fval = font("bold", fs)
    flab = font("mono_bold", int(max(8, 10 * s)))
    fsub = font("mono", int(max(8, 10 * s)))
    lab = (ev.get("label", "") or "").upper()
    sub = ev.get("sub", "")
    hv = th(fval, txt)
    hl = th(flab, lab) if lab else 0
    hs = th(fsub, sub) if sub else 0
    block = hv + (hl + 5 * s if lab else 0) + (hs + 4 * s if sub else 0)
    yy = max(pad, (h - block) / 2 - 2 * s)
    d.text((pad, yy), txt, font=fval, fill=accent, anchor="lt")
    yy += hv + 5 * s
    if lab:
        while lab and tw(d, lab, flab) > inner:
            lab = lab[:-1]
        d.text((pad, yy), lab, font=flab, fill=hexrgb(PALETTE["muted"]), anchor="lt")
        yy += hl + 4 * s
    if sub:
        d.text((pad, yy), sub, font=fsub, fill=hexrgb(PALETTE["muted"]), anchor="lt")
    d.rectangle([pad, h - 8 * s, pad + (w - pad - 10 * s) * clamp01(pin), h - 7 * s], fill=accent)
    return lay, (x, y)


def r_ring(W, H, ev, t, pin, accent):
    ax, ay = ev.get("anchor", [0.5, 0.5])
    cx, cy = ax * W, ay * H
    R = (0.075 + 0.02 * ease_out(pin)) * H
    pad = int(R * 2.6)
    lay = Image.new("RGBA", (pad * 2, pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    c = (pad, pad)
    sweep = 0.65 + 0.35 * clamp01(pin)
    d.arc([c[0] - R, c[1] - R, c[0] + R, c[1] + R], -90, -90 + 360 * sweep,
          fill=accent + (235,), width=max(2, int(2.2 * s)))
    # rotating dashed outer ring
    for i in range(24):
        a0 = math.radians(i * 15 + t * 26)
        rr = R * 1.24
        x0, y0 = c[0] + math.cos(a0) * rr, c[1] + math.sin(a0) * rr
        x1, y1 = c[0] + math.cos(a0) * (rr + 6 * s), c[1] + math.sin(a0) * (rr + 6 * s)
        d.line([x0, y0, x1, y1], fill=accent + (150,), width=max(1, int(1.2 * s)))
    # crosshair ticks
    for ang in (0, 90, 180, 270):
        a0 = math.radians(ang)
        d.line([c[0] + math.cos(a0) * R * 0.62, c[1] + math.sin(a0) * R * 0.62,
                c[0] + math.cos(a0) * R * 0.9, c[1] + math.sin(a0) * R * 0.9],
               fill=accent + (190,), width=max(1, int(1.2 * s)))
    # label below
    f = font("mono_bold", int(11.5 * s))
    label = ev.get("title", "")
    lw = tw(d, label, f)
    ly = c[1] + R * 1.55
    d.rectangle([c[0] - lw / 2 - 8 * s, ly - 7 * s, c[0] + lw / 2 + 8 * s, ly + 13 * s],
                fill=(8, 12, 22, 220))
    d.text((c[0], ly + 3 * s), label, font=f, fill=accent, anchor="mm")
    if ev.get("sub"):
        f2 = font("mono", int(10 * s))
        d.text((c[0], ly + 24 * s), ev["sub"], font=f2, fill=hexrgb(PALETTE["muted"]), anchor="mm")
    return lay, (cx - pad, cy - pad)


def r_bracket(W, H, ev, t, pin, accent):
    x, y, w, h = _box_px(ev["box"], W, H)
    pad = 26 * s
    lay = Image.new("RGBA", (int(w + pad * 2), int(h + pad * 2)), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    p = ease_out(pin)
    L = min(w, h) * 0.18 * p
    x0, y0, x1, y1 = pad, pad, pad + w, pad + h
    for (cx, cy, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        d.line([cx, cy, cx + dx * L, cy], fill=accent + (240,), width=max(2, int(2 * s)))
        d.line([cx, cy, cx, cy + dy * L], fill=accent + (240,), width=max(2, int(2 * s)))
    # measurement ticks along the top edge
    if p > 0.5:
        for i in range(1, 8):
            xx = x0 + (w / 8) * i
            d.line([xx, y0, xx, y0 + (5 if i % 4 else 9) * s], fill=accent + (120,), width=1)
    if ev.get("title"):
        f = font("mono_bold", int(11 * s))
        ly = y0 - 17 * s
        tag = ev["title"].upper()
        lw = tw(d, tag, f)
        d.rectangle([x0, ly - 5 * s, x0 + lw + 12 * s, ly + 11 * s], fill=(8, 12, 22, 225))
        d.rectangle([x0, ly - 5 * s, x0 + 3 * s, ly + 11 * s], fill=accent)
        d.text((x0 + 8 * s, ly), tag, font=f, fill=accent)
        if ev.get("sub"):
            d.text((x0 + lw + 18 * s, ly), ev["sub"], font=font("mono", int(10.5 * s)),
                   fill=hexrgb(PALETTE["muted"]))
    if ev.get("anchor"):
        d2 = ImageDraw.Draw(lay)
        ax, ay = ev["anchor"][0] * W - x + pad, ev["anchor"][1] * H - y + pad
        if x0 < ax < x1 and y0 < ay < y1:
            rr = 4 * s
            d2.ellipse([ax - rr, ay - rr, ax + rr, ay + rr], outline=accent + (230,), width=1)
            d2.line([ax - rr * 3, ay, ax - rr * 1.6, ay], fill=accent + (200,), width=1)
            d2.line([ax + rr * 1.6, ay, ax + rr * 3, ay], fill=accent + (200,), width=1)
            d2.line([ax, ay - rr * 3, ax, ay - rr * 1.6], fill=accent + (200,), width=1)
            d2.line([ax, ay + rr * 1.6, ax, ay + rr * 3], fill=accent + (200,), width=1)
    return lay, (x - pad, y - pad)


def r_chapter(W, H, ev, t, pin, accent):
    x, y, w, h = _box_px(ev["box"], W, H)
    lay = Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    yy = kicker_row(lay, d, 2, 2, ev.get("kicker", ""), accent, s)
    # typewriter reveal on the serif headline
    title, sub = ev.get("title", ""), ev.get("sub", "")
    n = int(len(title) * clamp01(pin * 1.4))
    # hero beats auto-fit the box; the fit_size floor is deliberately low so a
    # long title shrinks rather than overflows the safe area
    face = "serif_bold" if ev.get("serif") else "bold"
    big = int((132 if ev.get("hero") else 44) * s)
    f = font(face, fit_size(d, title, face, big, w, min_size=int(34 * s)))
    d.text((0, yy + 8 * s), title[:n], font=f, fill=hexrgb(PALETTE["paper"]))
    if n < len(title):
        cx = tw(d, title[:n], f) + 3 * s
        d.rectangle([cx, yy + 8 * s, cx + 12 * s, yy + 8 * s + 46 * s], fill=accent)
    # advance by real line height: ink bboxes under-report descenders, which is
    # what made the accent rule cut through the sub-line
    base = yy + 8 * s + lh(f) + (4 if ev.get("hero") else 2) * s
    if sub:
        f2 = font("serif" if ev.get("serif") else "sans", int((27 if ev.get("hero") else 23) * s))
        d.text((0, base), sub, font=f2, fill=hexrgb(PALETTE["muted"]))
        base += lh(f2) + (12 if ev.get("hero") else 8) * s
    d.rectangle([0, base, (w * 0.3) * ease_out(pin), base + max(1, 2 * s)], fill=accent)
    return lay, (x, y)


def r_caption(W, H, ev, t, pin, accent):
    return r_chapter(W, H, ev, t, pin, accent)


def r_corner(W, H, ev, t, pin, accent):
    """Minimal corner marker: tracked kicker, rule, one mono line.

    Used where the source plate already carries big typography — the graphic
    annotates the beat instead of competing with it."""
    x, y, w, _h = _box_px(ev["box"], W, H)
    pad = 2 * s
    lay = Image.new("RGBA", (int(w), int(58 * s)), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    yy = kicker_row(lay, d, pad, pad, ev.get("kicker", ""), accent, s, w - 4 * s)
    rw = min(w * 0.5, 150 * s) * ease_out(pin)
    d.rectangle([pad, yy + 1 * s, pad + rw, yy + 1 * s + max(1, 1.2 * s)], fill=accent)
    yy += 7 * s
    if ev.get("title"):
        fs = fit_size(d, ev["title"], "mono", int(11.5 * s), w - 4 * s)
        d.text((pad, yy), ev["title"], font=font("mono", fs),
               fill=hexrgb(PALETTE["paper"], 205), anchor="lt")
    return lay, (x, y)


def r_equation(W, H, ev, t, pin, accent):
    x, y, w, h = _box_px(ev["box"], W, H)
    lay = Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    yy = kicker_row(lay, d, 0, 0, "PROOF", accent, s)
    tag = ev.get("title", "")
    f = font("serif_bold", fit_size(d, tag, "serif_bold", int(30 * s), w))
    d.text((0, yy + 6 * s), tag, font=f, fill=hexrgb(PALETTE["paper"]))
    yy += 6 * s + th(f, tag) + 6 * s
    sub = ev.get("sub", "")
    f2 = font("mono", fit_size(d, sub, "mono", int(13 * s), w))
    d.text((0, yy), sub, font=f2, fill=accent)
    # underline sweep
    uy = yy + th(f2, sub) + 7 * s
    d.rectangle([0, uy, w * 0.72 * ease_out(pin), uy + max(1, int(1.4 * s))], fill=accent)
    return lay, (x, y)


def r_progress(W, H, ev, t, pin, accent):
    x, y, w, h = _box_px(ev["box"], W, H)
    lay = Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    lay.alpha_composite(glass(int(w), int(h), accent, 0.92, int(10 * s), bar=int(max(2, 2 * s))))
    pad = 13 * s
    f = font("mono_bold", int(10.5 * s))
    tracked(d, (pad, pad - 1 * s), ev.get("title", "").upper(), f, accent, 1.3 * s)
    goal = float(ev.get("total", 1)) or 1
    val = ev.get("value", 0)
    shown = goal * ease_out(pin) if ev.get("animate", True) else val
    p = clamp01(shown / goal)
    by = h - 16 * s
    d.rounded_rectangle([pad, by, w - pad, by + 5 * s], 3 * s, fill=(255, 255, 255, 26))
    d.rounded_rectangle([pad, by, pad + (w - 2 * pad) * p, by + 5 * s], 3 * s, fill=accent)
    d.text((w - pad, pad - 2 * s), ev.get("label", ""), font=font("mono", int(10 * s)),
           fill=hexrgb(PALETTE["paper"]), anchor="rt")
    return lay, (x, y)


def r_bars(W, H, ev, t, pin, accent):
    x, y, w, h = _box_px(ev["box"], W, H)
    lay = Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    lay.alpha_composite(glass(int(w), int(h), accent, 0.94, int(14 * s), bar=int(max(3, 3 * s))))
    pad = 15 * s
    yy = kicker_row(lay, d, pad, pad - 3 * s, ev.get("title", ""), accent, s)
    items = ev.get("items", [])
    rows_h = (h - yy - pad) / max(len(items), 1)
    lw = max(tw(d, it["label"], font("mono", int(11 * s))) for it in items) if items else 0
    for i, it in enumerate(items):
        p = clamp01((pin - i * STAGGER / ENTER) / 0.62)
        ry = yy + i * rows_h
        d.text((pad, ry), it["label"], font=font("mono", int(11 * s)), fill=hexrgb(PALETTE["muted"]))
        bx0 = pad + min(lw + 12 * s, w * 0.42)
        bx1 = w - pad - tw(d, str(it["value"]), font("mono_bold", int(11 * s))) - 10 * s
        d.rounded_rectangle([bx0, ry + 3 * s, bx1, ry + 3 * s + 7 * s], 3 * s, fill=(255, 255, 255, 22))
        fill_w = (bx1 - bx0) * clamp01(it.get("num", 0)) * ease_out(p)
        if fill_w > 1:
            col = mix(accent, hexrgb(PALETTE["lime"])[:3], i / max(len(items) - 1, 1) * 0.35)
            d.rounded_rectangle([bx0, ry + 3 * s, bx0 + fill_w, ry + 3 * s + 7 * s], 3 * s, fill=col)
        d.text((w - pad, ry), str(it["value"]), font=font("mono_bold", int(11 * s)),
               fill=hexrgb(PALETTE["paper"]), anchor="rt")
    return lay, (x, y)


def r_leaderboard(W, H, ev, t, pin, accent):
    x, y, w, h = _box_px(ev["box"], W, H)
    lay = Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    lay.alpha_composite(glass(int(w), int(h), accent, 0.96, int(14 * s), bar=int(max(3, 3 * s))))
    pad = 15 * s
    yy = kicker_row(lay, d, pad, pad - 3 * s, ev.get("title", ""), accent, s)
    d.line([pad, yy + 7 * s, w - pad, yy + 7 * s], fill=(255, 255, 255, 30), width=1)
    f = font("mono_bold", int(10 * s))
    d.text((pad, yy + 12 * s), "#", font=f, fill=hexrgb(PALETTE["muted"]))
    d.text((pad + 22 * s, yy + 12 * s), "BENCHMARK", font=f, fill=hexrgb(PALETTE["muted"]))
    d.text((w - pad, yy + 12 * s), "SCORE", font=f, fill=hexrgb(PALETTE["muted"]), anchor="rt")
    yy += 32 * s
    items = ev.get("items", [])
    rows_h = min((h - yy - pad) / max(len(items), 1), 30 * s)
    for i, it in enumerate(items):
        p = clamp01((pin - i * STAGGER * 1.4 / ENTER) / 0.45)
        if p <= 0:
            continue
        ry = yy + i * rows_h
        # row slide-in
        dx = (1 - ease_out(p)) * -14 * s
        row = Image.new("RGBA", (int(w - pad * 2), int(rows_h)), (0, 0, 0, 0))
        rd = ImageDraw.Draw(row)
        if i == 0:
            rd.rounded_rectangle([0, 1 * s, row.size[0], rows_h - 2 * s], 5 * s,
                                 fill=accent[0:3] + (26,), outline=accent[0:3] + (110,))
        rd.text((2 * s, rows_h / 2 - 1 * s), f"{i+1:02d}", font=font("mono", int(10 * s)),
                fill=accent, anchor="lm")
        rd.text((22 * s, rows_h / 2 - 1 * s), it["label"], font=font("sans", int(11.5 * s)),
                fill=hexrgb(PALETTE["paper"], int(255 * p)), anchor="lm")
        val = str(it["value"])
        rd.text((row.size[0] - 2 * s, rows_h / 2 - 1 * s), val,
                font=font("mono_bold", int(12 * s)), fill=accent, anchor="rm")
        if it.get("delta") and p > 0.55:
            dw = tw(rd, it["delta"], font("mono_bold", int(9 * s))) + 10 * s
            dx0 = row.size[0] - 12 * s - tw(rd, val, font("mono_bold", int(12 * s))) - dw
            rd.rounded_rectangle([dx0, rows_h / 2 - 8 * s, dx0 + dw, rows_h / 2 + 8 * s], 8 * s,
                                 fill=hexrgb(PALETTE["lime"], int(200 * p)))
            rd.text((dx0 + dw / 2, rows_h / 2 - 1 * s), it["delta"],
                    font=font("mono_bold", int(9 * s)), fill=(6, 12, 8, int(255 * p)), anchor="mm")
        row.putalpha(row.getchannel("A").point(lambda v: int(v * p)))
        lay.alpha_composite(row, (int(pad + dx), int(ry)))
    return lay, (x, y)


def r_quadrant(W, H, ev, t, pin, accent):
    x, y, w, h = _box_px(ev["box"], W, H)
    lay = Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    lay.alpha_composite(glass(int(w), int(h), accent, 0.95, int(14 * s), bar=int(max(3, 3 * s))))
    pad = 15 * s
    yy = kicker_row(lay, d, pad, pad - 3 * s, ev.get("title", ""), accent, s)
    gx0, gy0, gx1, gy1 = pad + 6 * s, yy + 26 * s, w - pad - 6 * s, h - pad - 20 * s
    p = ease_out(pin)
    d.line([gx0, gy1, gx1, gy1], fill=(255, 255, 255, 60), width=1)
    d.line([gx0, gy0, gx0, gy1], fill=(255, 255, 255, 60), width=1)
    for i in range(1, 5):
        xx = gx0 + (gx1 - gx0) * i / 5
        yy2 = gy0 + (gy1 - gy0) * i / 5
        d.line([xx, gy0, xx, gy1], fill=(255, 255, 255, 16), width=1)
        d.line([gx0, yy2, gx1, yy2], fill=(255, 255, 255, 16), width=1)
    # curve of "best $/task" frontier
    pts = []
    for i in range(24):
        q = i / 23
        pts.append((gx0 + (gx1 - gx0) * q * p,
                    gy1 - (gy1 - gy0) * (1 - q) ** 1.7 * 0.92 * p))
    if len(pts) > 1:
        d.line(pts, fill=accent + (190,), width=max(1, int(1.4 * s)))
    ax, ay = ev.get("anchor", [0.7, 0.4])
    mx = gx0 + (gx1 - gx0) * clamp01(ax)
    my = gy0 + (gy1 - gy0) * clamp01(ay)
    if p > 0.45:
        rr = 5 * s
        d.ellipse([mx - rr, my - rr, mx + rr, my + rr], fill=accent)
        d.ellipse([mx - rr * 2.4, my - rr * 2.4, mx + rr * 2.4, my + rr * 2.4],
                  outline=accent + (150,), width=1)
    for i, it in enumerate(ev.get("items", [])):
        ly = gy1 + 6 * s + i * 13 * s
        if ly > h - 4 * s:
            break
        d.text((gx0, ly), f"— {it['label']}", font=font("mono", int(9.5 * s)),
               fill=hexrgb(PALETTE["paper"], 215) if i == 0 else hexrgb(PALETTE["muted"]))
        d.text((w - pad, ly), it["value"], font=font("mono", int(9.5 * s)),
               fill=hexrgb(PALETTE["muted"]), anchor="rt")
    return lay, (x, y)


def r_gauge(W, H, ev, t, pin, accent):
    x, y, w, h = _box_px(ev["box"], W, H)
    lay = Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    cx, cy = w / 2, h * 0.62
    R = min(w, h) * 0.36
    a0, a1 = 150, 390
    d.arc([cx - R, cy - R, cx + R, cy + R], a0, a1, fill=(255, 255, 255, 26), width=max(3, int(4 * s)))
    val = float(ev.get("value", 100)) * clamp01(ev.get("pct", 1))
    sweep = ease_out_back(clamp01(pin), 1.2)
    ang = a0 + (a1 - a0) * (val / 100) * sweep
    d.arc([cx - R, cy - R, cx + R, cy + R], a0, ang, fill=accent + (245,), width=max(3, int(4 * s)))
    # ticks
    for i in range(0, 11):
        aa = math.radians(a0 + (a1 - a0) * i / 10)
        r0, r1 = R * 0.86, R * 0.95
        d.line([cx + math.cos(aa) * r0, cy + math.sin(aa) * r0,
                cx + math.cos(aa) * r1, cy + math.sin(aa) * r1],
               fill=(255, 255, 255, 60), width=1)
    aa = math.radians(ang)
    d.line([cx, cy, cx + math.cos(aa) * R * 0.92, cy + math.sin(aa) * R * 0.92],
           fill=accent + (255,), width=max(2, int(2.2 * s)))
    d.ellipse([cx - 3 * s, cy - 3 * s, cx + 3 * s, cy + 3 * s], fill=accent)
    f = font("bold", int(26 * s))
    d.text((cx, cy + R * 0.18), fmt_num(val * ease_out(pin), "comma", ev.get("suffix", "%")),
           font=f, fill=accent, anchor="mm")
    f2 = font("mono_bold", int(10.5 * s))
    d.text((cx, cy + R * 0.52), ev.get("label", "").upper(), font=f2,
           fill=hexrgb(PALETTE["muted"]), anchor="mm")
    d.text((cx, cy - R * 1.16), ev.get("title", "").upper(), font=f2, fill=accent, anchor="mm")
    return lay, (x, y)


def r_donut(W, H, ev, t, pin, accent):
    x, y, w, h = _box_px(ev["box"], W, H)
    lay = Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    cx, cy = w / 2, h * 0.48
    R = min(w, h) * 0.33
    wd = max(3, int(5 * s))
    d.arc([cx - R, cy - R, cx + R, cy + R], 0, 360, fill=(255, 255, 255, 26), width=wd)
    val = float(ev.get("value", 96))
    ang = 360 * (val / 100) * ease_out(pin)
    d.arc([cx - R, cy - R, cx + R, cy + R], -90, -90 + ang, fill=accent + (250,), width=wd)
    f = font("bold", int(30 * s))
    d.text((cx, cy - 4 * s), f"{count_at(val, pin):.0f}{ev.get('suffix','%')}",
           font=f, fill=accent, anchor="mm")
    f2 = font("mono_bold", int(9.5 * s))
    d.text((cx, cy + R + 18 * s), ev.get("label", "").upper(), font=f2,
           fill=hexrgb(PALETTE["muted"]), anchor="mm")
    return lay, (x, y)


def r_waveform(W, H, ev, t, pin, accent, wf):
    x, y, w, h = _box_px(ev["box"], W, H)
    lay = Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rectangle([0, 0, w, h], fill=(8, 12, 22, 200))
    d.rectangle([0, 0, w, max(1, int(1.2 * s))], fill=accent + (200,))
    bars = max(int(w / (5 * s)), 8)
    t0, t1 = ev["t0"], ev["t1"]
    span = max(t1 - t0, 1e-3)
    f = font("mono_bold", int(9.5 * s))
    lab = ev.get("title", "").upper()
    d.text((8 * s, 5 * s), lab, font=f, fill=accent)
    if ev.get("sub"):
        d.text((w - 8 * s, 5 * s), ev["sub"], font=font("mono", int(9 * s)),
               fill=hexrgb(PALETTE["muted"]), anchor="rt")
    top, bot = 20 * s, h - 4 * s
    mid = (top + bot) / 2
    peak = wf.get("peak", []) if wf else []
    for i in range(bars):
        q = i / max(bars - 1, 1)
        tt = t0 + span * q
        v = 0.32 + 0.68 * abs(math.sin(q * 39 + tt * 0.7)) if not peak else (
            peak[min(len(peak) - 1, int(tt * wf.get("hz", 10)))] if peak else 0.3)
        v = 0.12 + 0.88 * v
        bx = i * (w / bars)
        bh = (bot - top) / 2 * v * ease_out(clamp01(pin * 1.3))
        played = q <= (t - t0) / span
        col = accent + (235,) if played else (255, 255, 255, 70)
        d.rectangle([bx, mid - bh, bx + max(1.5 * s, w / bars * 0.55), mid + bh], fill=col)
    # playhead
    ph = (t - t0) / span * w
    d.rectangle([ph - 1 * s, 2 * s, ph + 1 * s, h - 2 * s], fill=hexrgb(PALETTE["amber"], 230))
    return lay, (x, y)


def r_speed_hud(W, H, ev, t, pin, accent):
    """Latency HUD: big delta number plus animated speed streaks."""
    x, y, w, h = _box_px(ev["box"], W, H)
    lay = Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    lay.alpha_composite(glass(int(w), int(h), accent, 0.92, int(12 * s), bar=int(max(3, 3 * s))))
    pad, inner = 15 * s, w - 30 * s
    yy = kicker_row(lay, d, pad, pad, ev.get("kicker", "PERFORMANCE"), accent, s, inner)
    val = float(ev.get("value", 0))
    txt = f"\u2212{count_at(val, pin):.0f}%"
    fs = fit_size(d, txt, "bold", int(38 * s), inner)
    f = font("bold", fs)
    d.text((pad, yy), txt, font=f, fill=accent, anchor="lt")
    yy += th(f, txt) + 2 * s
    if ev.get("sub"):
        fs2 = fit_size(d, ev["sub"], "mono", int(11 * s), inner)
        d.text((pad, yy), ev["sub"], font=font("mono", fs2),
               fill=hexrgb(PALETTE["muted"]), anchor="lt")
    for i in range(6):
        a = (t * 1.8 + i * 0.37) % 1
        sx = pad + (w - 2 * pad) * a
        sy = h - 14 * s + math.sin(i * 2.1) * 2 * s
        ln = 18 * s * (0.4 + 0.6 * math.sin(a * math.pi))
        d.line([sx, sy, sx + ln, sy], fill=accent + (int(170 * (1 - a) * ease_out(pin)),),
               width=max(1, int(1.4 * s)))
    return lay, (x, y)


def r_ad_break(W, H, ev, t, pin, accent):
    x, y, w, h = _box_px(ev["box"], W, H)
    lay = Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    # slanted stinger block
    skew = 10 * s
    poly = [(skew, 0), (w, 0), (w - skew, h), (0, h)]
    d.polygon(poly, fill=(10, 6, 14, 225))
    d.line([(skew, 0), (w, 0)], fill=accent + (255,), width=max(2, int(2 * s)))
    d.line([(0, h), (w - skew, h)], fill=accent + (255,), width=max(2, int(2 * s)))
    pad = 15 * s
    f = font("mono_bold", int(9.5 * s))
    d.text((pad + skew, pad), "AD BREAK", font=f, fill=accent)
    d.text((w - pad - skew, pad), "● REC", font=font("mono", int(9 * s)),
           fill=hexrgb(PALETTE["magenta"]), anchor="rt")
    fs = fit_size(d, ev.get("title", ""), "bold", int(24 * s), w - pad * 2 - skew * 2)
    d.text((pad + skew + 2 * s, h * 0.32), ev.get("title", ""), font=font("bold", fs),
           fill=hexrgb(PALETTE["paper"]))
    if ev.get("sub"):
        d.text((pad + skew + 2 * s, h * 0.32 + fs + 6 * s), ev["sub"],
               font=font("mono", int(10.5 * s)), fill=hexrgb(PALETTE["muted"]))
    return lay, (x, y)


def r_end_card(W, H, ev, t, pin, accent):
    x, y, w, h = _box_px(ev["box"], W, H)
    lay = Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    cx, cy = w / 2, h * 0.42
    # pulse rings
    for k in range(3):
        rr = (min(w, h) * 0.18) * (1 + 0.55 * k) * (0.9 + 0.1 * ease_out(pin))
        a = int((90 - k * 25) * (0.6 + 0.4 * math.sin(t * 2.2 - k * 0.7)) * ease_out(pin))
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=accent + (max(a, 0),),
                  width=max(1, int(1.4 * s)))
    d.ellipse([cx - 15 * s, cy - 15 * s, cx + 15 * s, cy + 15 * s], fill=accent)
    d.polygon([(cx - 4 * s, cy - 8 * s), (cx + 9 * s, cy), (cx - 4 * s, cy + 8 * s)],
              fill=(6, 8, 12, 255))
    fs = fit_size(d, ev.get("title", ""), "bold", int(30 * s), w)
    d.text((cx, cy + 34 * s), ev.get("title", ""), font=font("bold", fs),
           fill=hexrgb(PALETTE["paper"]), anchor="mm")
    if ev.get("sub"):
        d.text((cx, cy + 34 * s + fs + 6 * s), ev["sub"], font=font("mono", int(11 * s)),
               fill=hexrgb(PALETTE["muted"]), anchor="mm")
    return lay, (x, y)


# --------------------------------------------------------------- entry point
_RENDERERS = {
    "id_card": r_id_card, "lower_third": r_lower_third, "callout": r_callout,
    "stat": r_stat, "ring": r_ring, "bracket": r_bracket, "chapter": r_chapter,
    "caption": r_caption, "corner": r_corner, "equation": r_equation, "progress": r_progress,
    "bars": r_bars, "leaderboard": r_leaderboard, "quadrant": r_quadrant,
    "gauge": r_gauge, "donut": r_donut, "speed_hud": r_speed_hud,
    "ad_break": r_ad_break, "end_card": r_end_card,
}


def render_event(W: int, H: int, ev: dict, t: float, wf: dict | None = None) -> tuple:
    """Render one event at time t → (RGBA layer, (x, y) paste pos)."""
    global s
    s = H / 720.0
    accent = hexrgb(PALETTE.get(ev.get("accent", "cyan"), PALETTE["cyan"]))[:3]
    a, pin, pout = envelope(t, ev["t0"], ev["t1"])
    if a <= 0.002:
        return None, (0, 0)
    kind = ev["kind"]
    if kind == "ticker":
        lay, pos = r_ticker(W, H, ev, t, pin, accent, ev["t1"] - ev["t0"], s)
    elif kind == "waveform":
        lay, pos = r_waveform(W, H, ev, t, pin, accent, wf)
    elif kind in _RENDERERS:
        lay, pos = _RENDERERS[kind](W, H, ev, t, pin, accent)
    else:
        lay, pos = r_callout(W, H, ev, t, pin, accent)

    motion = ev.get("motion", "slide_up")
    e = ease_out(pin)
    ox, oy = 0, 0
    if motion == "slide_up":
        oy = int((1 - e) * 26 * s)
    elif motion == "slide_down":
        oy = -int((1 - e) * 26 * s)
    if motion == "pop":
        sc = 0.93 + 0.07 * ease_out_back(pin, 2.0)
        lay = lay.resize((max(1, int(lay.width * sc)), max(1, int(lay.height * sc))), Image.BILINEAR)
    if motion == "wipe":
        wpx = max(1, int(lay.width * e))
        mask = Image.new("L", lay.size, 0)
        ImageDraw.Draw(mask).rectangle([0, 0, wpx, lay.height], fill=255)
        lay.putalpha(Image.composite(lay.getchannel("A"), Image.new("L", lay.size, 0), mask))
    # fade
    if a < 0.999:
        lay.putalpha(lay.getchannel("A").point(lambda v: int(v * a)))
    return lay, (int(pos[0]) + ox, int(pos[1]) + oy)


def render_frame(W: int, H: int, events: list, t: float, wf: dict | None = None,
                 only: set | None = None) -> Image.Image:
    frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for ev in events:
        if only and ev["kind"] not in only:
            continue
        if t < ev["t0"] or t > ev["t1"]:
            continue
        lay, pos = render_event(W, H, ev, t, wf)
        if lay is None:
            continue
        px, py = pos
        if px < 0 or py < 0:                      # clip layers that overhang the canvas
            lay = lay.crop((max(-px, 0), max(-py, 0), lay.width, lay.height))
            px, py = max(px, 0), max(py, 0)
        if px < W and py < H:
            frame.alpha_composite(lay, (px, py))
    return frame


def load_timeline() -> dict:
    return json.loads((ROOT / "graphics" / "timeline.json").read_text())


def load_waveform() -> dict:
    p = ROOT / "graphics" / "waveform.json"
    return json.loads(p.read_text()) if p.exists() else {}


if __name__ == "__main__":
    tl = load_timeline()
    wf = load_waveform()
    # smoke test: render one frame per event and report size
    for ev in tl["events"]:
        mid = (ev["t0"] + ev["t1"]) / 2
        lay, pos = render_event(1280, 720, ev, mid, wf)
        print(f"{ev['id']:5s} {ev['kind']:12s} t={mid:7.1f} layer={lay.size} pos={pos}")
