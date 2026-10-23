#!/usr/bin/env python3
"""Compose overlay frames over real source frames into a QA sheet.

  python3 scripts/preview_overlay.py --times 24.5,193,1276,1410 --out analysis/blocks/qa1.jpg
"""
from __future__ import annotations
import argparse, subprocess, tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import overlay_lib as OL

ROOT = Path(__file__).resolve().parent.parent
VIDEO = ROOT / "Deepseek strikes again.mp4"
W, H = 1280, 720

ap = argparse.ArgumentParser()
ap.add_argument("--times", default="")
ap.add_argument("--out", required=True)
ap.add_argument("--cols", type=int, default=2)
ap.add_argument("--tw", type=int, default=900)
ap.add_argument("--all", action="store_true", help="one tile per event, at its midpoint")
args = ap.parse_args()

tl = OL.load_timeline()
wf = OL.load_waveform()
events = tl["events"]
times = [float(x) for x in args.times.split(",") if x]
tlw = OL.load_timeline()
if args.all:
    times = [round((e["t0"] + e["t1"]) / 2, 2) for e in tlw["events"]]

tmp = Path(tempfile.mkdtemp())
frames = []
for i, t in enumerate(times):
    fp = tmp / f"{i}.png"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", str(t), "-i", str(VIDEO),
                    "-frames:v", "1", str(fp)], check=True)
    base = Image.open(fp).convert("RGBA").resize((W, H), Image.LANCZOS)
    layer = OL.render_frame(W, H, events, t, wf)
    base.alpha_composite(layer)
    frames.append((t, base.convert("RGB")))

TW = args.tw
TH = int(TW * 9 / 16)
PAD, LAB = 8, 24
rows = (len(frames) + args.cols - 1) // args.cols
sheet = Image.new("RGB", (args.cols * TW + PAD * (args.cols + 1),
                          rows * (TH + LAB + PAD) + PAD), (8, 10, 14))
d = ImageDraw.Draw(sheet)
f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 17)
for i, (t, im) in enumerate(frames):
    r, c = divmod(i, args.cols)
    x = PAD + c * (TW + PAD)
    y = PAD + r * (TH + LAB + PAD)
    sheet.paste(im.resize((TW, TH), Image.LANCZOS), (x, y))
    d.text((x + 6, y + TH + 3), f"{int(t)//60:02d}:{t%60:05.2f}", font=f, fill=(255, 210, 70))
out = ROOT / args.out
out.parent.mkdir(parents=True, exist_ok=True)
sheet.save(out, quality=88)
print(out, sheet.size)
