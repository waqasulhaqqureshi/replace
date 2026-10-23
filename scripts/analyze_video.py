#!/usr/bin/env python3
"""
analyze_video.py — reproducible 30-minute video keyframe / motion / colour analysis.

Stage 1 of the pipeline. Produces analysis/metrics.json with, for every second:
  lum_mean, lum_p95, sat_mean, sat_p95, motion (mean abs frame delta),
  edge_density, black_ratio (letterbox / title-card detection),
  hue_hist (12-bin dominant-colour fingerprint), text_density (center-band edges),
  audio_rms / audio_db (from the 16 kHz WAV),
plus a scene graph (ffmpeg scene score) and per-5-minute-block rollups.

Usage:
  python3 scripts/analyze_video.py \
      --video "Deepseek strikes again.mp4" --fps-frames analysis/frames --wav analysis/audio.wav
"""
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------- frame metrics
def frame_metrics(path: Path) -> dict:
    im = Image.open(path).convert("RGB")
    a = np.asarray(im, dtype=np.float32)
    h, w, _ = a.shape
    gray = a @ np.array([0.299, 0.587, 0.114], dtype=np.float32)

    lum_mean = float(gray.mean())
    lum_p95 = float(np.percentile(gray, 95))

    mx = a.max(axis=2)
    mn = a.min(axis=2)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
    sat_mean = float(sat.mean())
    sat_p95 = float(np.percentile(sat, 95))

    # near-black pixel ratio (letterbox bars, title cards)
    black_ratio = float((gray < 18).mean())

    # Sobel-ish edge density using numpy gradients
    gy, gx = np.gradient(gray)
    mag = np.hypot(gx, gy)
    edge_density = float((mag > 24).mean())

    # text/UI density: edges in the central band (where UI text lives)
    band = mag[int(h * 0.18):int(h * 0.86), int(w * 0.12):int(w * 0.88)]
    text_density = float((band > 30).mean())

    # 12-bin hue fingerprint, saturation-weighted
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    hue = np.zeros_like(r)
    d = mx - mn + 1e-6
    m = mx == r
    hue[m] = ((g - b)[m] / d[m]) % 6
    m = mx == g
    hue[m] = ((b - r)[m] / d[m]) + 2
    m = mx == b
    hue[m] = ((r - g)[m] / d[m]) + 4
    hue = (hue * 60.0) % 360.0
    wgt = sat.ravel()
    hist, _ = np.histogram(hue.ravel(), bins=12, range=(0, 360), weights=wgt)
    tot = hist.sum() or 1.0
    hue_hist = [round(float(x / tot), 4) for x in hist]

    return dict(
        lum_mean=round(lum_mean, 2),
        lum_p95=round(lum_p95, 2),
        sat_mean=round(sat_mean, 4),
        sat_p95=round(sat_p95, 4),
        black_ratio=round(black_ratio, 4),
        edge_density=round(edge_density, 4),
        text_density=round(text_density, 4),
        hue_hist=hue_hist,
    )


def audio_envelope(wav_path: Path, fps: float = 1.0, win: float = 0.25) -> list[float]:
    """RMS (dBFS) per `fps` sample window."""
    if not wav_path.exists():
        return []
    with wave.open(str(wav_path), "rb") as w:
        sr = w.getframerate()
        nframes = w.getnframes()
        raw = w.readframes(nframes)
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    step = int(sr / fps)
    out = []
    for i in range(0, len(samples) - step + 1, step):
        chunk = samples[i:i + step]
        rms = float(np.sqrt(np.mean(chunk ** 2)) + 1e-9)
        out.append(round(20 * math.log10(rms), 2))
    return out


def scene_cuts(video: Path, threshold: float = 0.12) -> list[float]:
    """ffmpeg scene-score cut list (hard cuts / slideshow transitions)."""
    cmd = [
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(video),
        "-vf", f"select='gt(scene,{threshold})',showinfo",
        "-an", "-f", "null", "-",
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    except Exception:
        return []
    return [round(float(x), 3) for x in re.findall(r"pts_time:([0-9.]+)", res.stderr)]


def rollup(seconds: list[dict], block: int = 300) -> list[dict]:
    """5-minute window summaries."""
    blocks = []
    n = len(seconds)
    for b in range(math.ceil(n / block)):
        lo, hi = b * block, min((b + 1) * block, n)
        chunk = seconds[lo:hi]
        if not chunk:
            continue
        def avg(k):
            return round(float(np.mean([c[k] for c in chunk])), 3)
        def mx(k):
            return round(float(np.max([c.get(k, 0) for c in chunk])), 3)
        # dominant hue sector across the block
        hh = np.array([c["hue_hist"] for c in chunk]).mean(axis=0)
        dom = int(np.argmax(hh)) * 30
        blocks.append(dict(
            block=b + 1,
            t0=lo, t1=hi,
            label=f"{lo // 60:02d}:{lo % 60:02d}-{hi // 60:02d}:{hi % 60:02d}",
            lum_mean=avg("lum_mean"),
            sat_mean=avg("sat_mean"),
            motion_mean=avg("motion"),
            motion_max=mx("motion"),
            motion_p90=round(float(np.percentile([c["motion"] for c in chunk], 90)), 3),
            edge_mean=avg("edge_density"),
            text_density_mean=avg("text_density"),
            black_ratio_mean=avg("black_ratio"),
            dominant_hue_deg=dom,
            audio_db_mean=avg("audio_db") if "audio_db" in chunk[0] else None,
            audio_db_max=mx("audio_db") if "audio_db" in chunk[0] else None,
            # static screens = low motion, high text density
            static_ui_ratio=round(float(np.mean([
                1 if (c["motion"] < 2.0 and c["text_density"] > 0.03) else 0 for c in chunk
            ])), 3),
        ))
    return blocks


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default="Deepseek strikes again.mp4")
    ap.add_argument("--frames", default="analysis/frames")
    ap.add_argument("--wav", default="analysis/audio.wav")
    ap.add_argument("--out", default="analysis/metrics.json")
    ap.add_argument("--src-fps", type=float, default=30.0)
    args = ap.parse_args()

    video = (ROOT / args.video) if not Path(args.video).is_absolute() else Path(args.video)
    frames = sorted((ROOT / args.frames).glob("f_*.jpg"))
    if not frames:
        raise SystemExit(f"no frames in {args.frames}; run ffmpeg fps=1 first")

    print(f"[analysis] {len(frames)} frames from {video.name}")

    prev_gray = None
    seconds: list[dict] = []
    for i, fp in enumerate(frames):
        m = frame_metrics(fp)
        im = Image.open(fp).convert("RGB").resize((160, 90))
        g = np.asarray(im, dtype=np.float32) @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
        motion = 0.0 if prev_gray is None else float(np.abs(g - prev_gray).mean())
        prev_gray = g
        m["t"] = i
        m["motion"] = round(motion, 3)
        seconds.append(m)
        if i % 200 == 0:
            print(f"  t={i:4d}s  lum={m['lum_mean']:5.1f} sat={m['sat_mean']:.2f} "
                  f"mot={motion:5.2f} edge={m['edge_density']:.3f} black={m['black_ratio']:.2f}")

    audio = audio_envelope(ROOT / args.wav, fps=1.0)
    for i, s in enumerate(seconds):
        s["audio_db"] = audio[i] if i < len(audio) else None

    print("[analysis] scene detection…")
    cuts = scene_cuts(video)
    print(f"[analysis] {len(cuts)} cuts")

    # segment plan: merge cuts closer than 1.2 s, tag segment character
    segs = []
    edges = [0.0] + cuts + [float(len(seconds))]
    for a, b in zip(edges[:-1], edges[1:]):
        if b - a < 1.0:
            continue
        lo, hi = int(a), min(int(b) + 1, len(seconds))
        chunk = seconds[lo:hi]
        if not chunk:
            continue
        segs.append(dict(
            t0=lo, t1=hi, dur=hi - lo,
            lum=round(float(np.mean([c["lum_mean"] for c in chunk])), 1),
            sat=round(float(np.mean([c["sat_mean"] for c in chunk])), 3),
            motion=round(float(np.mean([c["motion"] for c in chunk])), 2),
            edge=round(float(np.mean([c["edge_density"] for c in chunk])), 3),
            text=round(float(np.mean([c["text_density"] for c in chunk])), 3),
            black=round(float(np.mean([c["black_ratio"] for c in chunk])), 3),
        ))

    data = dict(
        source=video.name,
        duration_s=len(seconds),
        duration_hms=f"{len(seconds)//60:02d}:{len(seconds)%60:02d}",
        frame_sampled_fps=1,
        source_fps=args.src_fps,
        resolution="1280x720",
        seconds=seconds,
        cuts=cuts,
        segments=segs,
        blocks=rollup(seconds, 300),
    )
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=1))
    print(f"[analysis] wrote {out}  ({out.stat().st_size/1024:.0f} KB)")

    for b in data["blocks"]:
        print(f"  BLOCK {b['block']} {b['label']}  lum={b['lum_mean']:5.1f} "
              f"sat={b['sat_mean']:.2f} mot={b['motion_mean']:.2f}/{b['motion_max']:.1f} "
              f"edge={b['edge_mean']:.3f} text={b['text_density_mean']:.3f} "
              f"staticUI={b['static_ui_ratio']:.2f} hue={b['dominant_hue_deg']}°")


if __name__ == "__main__":
    main()
