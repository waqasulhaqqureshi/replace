#!/usr/bin/env python3
"""Build per-block contact sheets (with burned-in timecodes) for visual review."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import re

ROOT = Path(__file__).resolve().parent.parent
SHEETS = ROOT / "analysis" / "sheets"
OUT = ROOT / "analysis" / "blocks"
OUT.mkdir(parents=True, exist_ok=True)

STEP = 20  # seconds between sampled keyframes
kf = sorted(SHEETS.glob("k_*.jpg"), key=lambda p: int(re.findall(r"\d+", p.stem)[0]))
# k_0001 -> t=0.0s (fps=1/20 starts at 0)
frames = [(i * STEP, p) for i, p in enumerate(kf)]

def font(size):
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()

BLOCK = 300
COLS, ROWS = 4, 4
TW, TH = 480, 270
PAD, LABEL, HEADER = 8, 26, 54

for b in range(6):
    lo, hi = b * BLOCK, min((b + 1) * BLOCK, 27 * 60 + 21)
    sel = [(t, p) for t, p in frames if lo <= t < hi]
    if not sel:
        continue
    n = len(sel)
    rows = max(1, (n + COLS - 1) // COLS)
    W = COLS * TW + PAD * (COLS + 1)
    H = HEADER + rows * (TH + LABEL + PAD) + PAD
    sheet = Image.new("RGB", (W, H), (12, 14, 20))
    d = ImageDraw.Draw(sheet)
    hf = font(30)
    tf = font(22)
    d.text((PAD + 4, 12), f"BLOCK {b+1}   {lo//60:02d}:{lo%60:02d} - {hi//60:02d}:{hi%60:02d}"
           f"   ({n} samples @ {STEP}s)", font=hf, fill=(120, 230, 255))
    for i, (t, p) in enumerate(sel):
        r, c = divmod(i, COLS)
        x = PAD + c * (TW + PAD)
        y = HEADER + r * (TH + LABEL + PAD)
        try:
            im = Image.open(p).convert("RGB").resize((TW, TH), Image.LANCZOS)
        except Exception:
            continue
        sheet.paste(im, (x, y))
        ts = f"{int(t)//60:02d}:{int(t)%60:02d}"
        d.rectangle([x, y, x + 78, y + LABEL], fill=(0, 0, 0))
        d.text((x + 7, y + 3), ts, font=tf, fill=(255, 235, 90))
    out = OUT / f"block{b+1}.jpg"
    sheet.save(out, quality=82)
    print(out, sheet.size)
