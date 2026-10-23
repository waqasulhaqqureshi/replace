#!/usr/bin/env python3
"""
render_overlay.py — burn the timeline's motion graphics into the source video.

    source ──ffmpeg decode──▶ raw RGB frames ──▶ overlay compositor ──▶ ffmpeg x264 ──▶ mp4

The compositor draws whatever graphics/timeline.json says is active at each
frame's timestamp, so the render is deterministic and seekable: any frame can
be reproduced from (timeline, t) alone.

Examples
--------
# 30 s proof-of-concept (fast, same pipeline as the full render)
python3 scripts/render_overlay.py --range 0-30 --out out/preview_0_30.mp4

# full 27-minute burn-in, 30 fps (source rate)
python3 scripts/render_overlay.py --out out/deepseek_overlay_full.mp4

# 2× temporal resolution: overlay motion is authored at 60 fps while the
# source plate is frame-doubled, so counters/rings/rails animate smoothly.
python3 scripts/render_overlay.py --range 1240-1310 --render-fps 60 \
        --out out/preview_bench_60fps.mp4
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import overlay_lib as OL  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SRC = ROOT / "Deepseek strikes again.mp4"


def probe_fps(path: Path) -> float:
    cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0",
           "-show_entries", "stream=r_frame_rate,width,height", "-of", "json", str(path)]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
        st = json.loads(out)["streams"][0]
        num, den = st["r_frame_rate"].split("/")
        return float(num) / float(den)
    except Exception:
        return 30.0


def build_encoder(out: Path, W: int, H: int, fps: float, crf: int, preset: str,
                  audio_src: Path | None, duration: float | None) -> list[str]:
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
           "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", f"{fps:g}",
           "-i", "pipe:0"]
    if audio_src is not None:
        cmd += ["-ss", str(getattr(build_encoder, "_start", 0.0)), "-i", str(audio_src)]
    cmd += ["-map", "0:v:0"]
    if audio_src is not None:
        cmd += ["-map", "1:a:0", "-c:a", "copy"]
    if duration:
        cmd += ["-t", f"{duration:.3f}", "-shortest"]
    cmd += ["-c:v", "libx264", "-preset", preset, "-crf", str(crf),
            "-pix_fmt", "yuv420p", "-profile:v", "high", "-movflags", "+faststart",
            "-g", str(int(fps * 2)), "-bf", "2"]
    cmd += [str(out)]
    return cmd


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(DEFAULT_SRC))
    ap.add_argument("--out", default="out/deepseek_overlay.mp4")
    ap.add_argument("--timeline", default="graphics/timeline.json")
    ap.add_argument("--range", default=None, help="START-END in seconds, e.g. 612-690")
    ap.add_argument("--segments", default="", help="comma list of START-END ranges to render "
                                                  "as one concatenated film")
    ap.add_argument("--render-fps", type=float, default=0, help="0 = keep source fps")
    ap.add_argument("--crf", type=int, default=19)
    ap.add_argument("--preset", default="veryfast")
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--only", default="", help="comma list of kinds to render (debug)")
    ap.add_argument("--progress-every", type=float, default=5.0)
    args = ap.parse_args()

    src = Path(args.src)
    if not src.exists():
        raise SystemExit(f"source not found: {src}")
    out = ROOT / args.out if not Path(args.out).is_absolute() else Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    if args.segments:
        # render each range independently, then concat (stream copy) into one film
        segs = [x.strip() for x in args.segments.split(",") if x.strip()]
        parts = []
        for i, seg in enumerate(segs):
            part = out.parent / f".part{i:02d}.mp4"
            parts.append(part)
            cmd = [sys.executable, str(Path(__file__).resolve()), "--src", str(src),
                   "--timeline", args.timeline, "--range", seg, "--out", str(part),
                   "--crf", str(args.crf), "--preset", args.preset,
                   "--progress-every", str(args.progress_every)]
            if args.render_fps:
                cmd += ["--render-fps", str(args.render_fps)]
            if args.no_audio:
                cmd += ["--no-audio"]
            if args.only:
                cmd += ["--only", args.only]
            print(f"[segments] {i+1}/{len(segs)}  {seg}", flush=True)
            subprocess.run(cmd, check=True)
        lst = out.parent / ".concat.txt"
        lst.write_text("".join(f"file '{p.name}'\n" for p in parts))
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                        "-f", "concat", "-safe", "0", "-i", str(lst),
                        "-c", "copy", "-movflags", "+faststart", str(out)], check=True)
        for p in parts:
            p.unlink(missing_ok=True)
        lst.unlink(missing_ok=True)
        print(f"[segments] wrote {out}  {out.stat().st_size/1e6:.1f} MB")
        return

    tl = json.loads((ROOT / args.timeline).read_text())
    wf = OL.load_waveform()
    events = tl["events"]
    only = set(x.strip() for x in args.only.split(",") if x.strip()) or None

    src_fps = probe_fps(src)
    W, H = 1280, 720
    fps = args.render_fps or src_fps
    start, end = 0.0, tl["duration_s"]
    if args.range:
        a, b = args.range.split("-")
        start, end = float(a), float(b)
    dur = end - start

    print(f"[render] {src.name}  {W}x{H}  src {src_fps:g} fps → out {fps:g} fps")
    print(f"[render] window {start:g}–{end:g}s ({dur:g}s)  events={len(events)}"
          f"  only={sorted(only) if only else 'all'}")

    dec = subprocess.Popen(
        ["ffmpeg", "-hide_banner", "-loglevel", "error",
         "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", str(src),
         "-an", "-vf", f"fps={fps:g},scale={W}:{H}:flags=lanczos",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"],
        stdout=subprocess.PIPE, bufsize=W * H * 3 * 8)

    encoder = build_encoder(out, W, H, fps, args.crf, args.preset,
                            None if args.no_audio else src, dur)
    build_encoder._start = start
    enc = subprocess.Popen(encoder, stdin=subprocess.PIPE, bufsize=W * H * 4 * 8)

    frame_bytes = W * H * 3
    n = 0
    t0 = time.time()
    last = t0
    total = int(dur * fps)
    # only composite when at least one event is live at that time
    active_windows = sorted([(e["t0"], e["t1"]) for e in events
                             if not only or e["kind"] in only])

    def any_active(t: float) -> bool:
        for a, b in active_windows:
            if a - 0.001 <= t <= b + 0.001:
                return True
        return False

    try:
        while True:
            buf = dec.stdout.read(frame_bytes)
            if len(buf) < frame_bytes:
                break
            t = start + n / fps
            if any_active(t):
                base = Image.frombytes("RGB", (W, H), buf).convert("RGBA")
                base.alpha_composite(OL.render_frame(W, H, events, t, wf, only))
                enc.stdin.write(base.convert("RGBA").tobytes())
            else:
                # pass the decoded frame straight through (no re-composite cost)
                enc.stdin.write(Image.frombytes("RGB", (W, H), buf)
                                .convert("RGBA").tobytes())
            n += 1
            if args.progress_every and time.time() - last >= args.progress_every:
                last = time.time()
                pct = min(100.0, n / max(total, 1) * 100)
                rate = n / max(time.time() - t0, 1e-6)
                eta = (total - n) / max(rate, 1e-6)
                print(f"  {pct:5.1f}%  frame {n}/{total}  {rate:5.1f} fps  eta {eta/60:4.1f} min",
                      flush=True)
    finally:
        try:
            enc.stdin.close()
        except Exception:
            pass
        dec.wait()
        enc.wait()

    if dec.returncode not in (0, None):
        print(f"[render] WARNING decoder exit {dec.returncode}")
    if enc.returncode != 0:
        raise SystemExit(f"[render] encoder failed ({enc.returncode})")
    if not out.exists():
        raise SystemExit("[render] no output produced")
    mb = out.stat().st_size / 1e6
    print(f"[render] wrote {out}  {mb:.1f} MB  {n} frames  "
          f"in {(time.time()-t0)/60:.1f} min")


if __name__ == "__main__":
    main()
