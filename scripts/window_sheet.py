#!/usr/bin/env python3
"""Extract frames at a list of timestamps and tile them into one labelled sheet.

Usage:  python3 scripts/window_sheet.py --start 150 --end 240 --step 2 --out analysis/blocks/w_title.jpg
"""
from __future__ import annotations
import argparse, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
VIDEO = ROOT / "Deepseek strikes again.mp4"

ap = argparse.ArgumentParser()
ap.add_argument("--start", type=float, required=True)
ap.add_argument("--end", type=float, required=True)
ap.add_argument("--step", type=float, default=2)
ap.add_argument("--out", required=True)
ap.add_argument("--cols", type=int, default=4)
ap.add_argument("--tw", type=int, default=420)
args = ap.parse_args()

def font(sz):
    p = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    return ImageFont.truetype(p, sz) if Path(p).exists() else ImageFont.load_default()

times = []
t = args.start
while t < args.end:
    times.append(round(t, 2))
    t += args.step

tmp = Path(tempfile.mkdtemp())
imgs = []
for i, tt in enumerate(times):
    fp = tmp / f"{i:04d}.jpg"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", str(tt),
                    "-i", str(VIDEO), "-frames:v", "1", "-vf", "scale=640:360",
                    "-q:v", "3", str(fp)], check=False)
    if fp.exists():
        imgs.append((tt, fp))

TW, TH, PAD, LAB = args.tw, int(args.tw * 9 / 16), 6, 22
rows = (len(imgs) + args.cols - 1) // args.cols
W = args.cols * TW + PAD * (args.cols + 1)
H = rows * (TH + LAB + PAD) + PAD
sheet = Image.new("RGB", (W, H), (10, 12, 18))
d = ImageDraw.Draw(sheet)
f = font(18)
for i, (tt, fp) in enumerate(imgs):
    r, c = divmod(i, args.cols)
    x = PAD + c * (TW + PAD)
    y = PAD + r * (TH + LAB + PAD)
    sheet.paste(Image.open(fp).convert("RGB").resize((TW, TH), Image.LANCZOS), (x, y))
    label = f"{int(tt)//60:02d}:{tt%60:05.2f}"
    d.rectangle([x, y, x + 92, y + LAB], fill=(0, 0, 0))
    d.text((x + 5, y + 2), label, font=f, fill=(255, 225, 80))
out = ROOT / args.out
out.parent.mkdir(parents=True, exist_ok=True)
sheet.save(out, quality=84)
print(out, sheet.size, len(imgs), "frames")
