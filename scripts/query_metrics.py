#!/usr/bin/env python3
"""Query helper: print per-second metrics for a window, and detect stable 'card' spans."""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
M = json.loads((ROOT / "analysis/metrics.json").read_text())
S = M["seconds"]

def window(a, b, step=1):
    for s in S[int(a):int(b):step]:
        t = s["t"]
        print(f"{t//60:02d}:{t%60:02d} lum={s['lum_mean']:6.1f} p95={s['lum_p95']:5.1f} "
              f"sat={s['sat_mean']:.2f} mot={s['motion']:6.2f} edge={s['edge_density']:.3f} "
              f"text={s['text_density']:.3f} blk={s['black_ratio']:.2f} aud={s['audio_db']}")

def cards(a, b, max_motion=1.0):
    """Spans where the frame is nearly frozen (title cards / table dwells)."""
    out, cur = [], None
    for s in S[int(a):int(b)]:
        if s["motion"] < max_motion:
            cur = [s["t"], s["t"]] if cur is None else [cur[0], s["t"]]
        else:
            if cur and cur[1] - cur[0] >= 3:
                out.append(cur)
            cur = None
    if cur and cur[1] - cur[0] >= 3:
        out.append(cur)
    for lo, hi in out:
        ch = S[lo:hi + 1]
        print(f"  FREEZE {lo//60:02d}:{lo%60:02d}-{hi//60:02d}:{hi%60:02d} ({hi-lo+1}s) "
              f"lum={sum(c['lum_mean'] for c in ch)/len(ch):5.1f} "
              f"blk={sum(c['black_ratio'] for c in ch)/len(ch):.2f} "
              f"text={sum(c['text_density'] for c in ch)/len(ch):.3f}")

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "win":
        window(float(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4]) if len(sys.argv) > 4 else 1)
    elif cmd == "cards":
        cards(float(sys.argv[2]), float(sys.argv[3]),
              float(sys.argv[4]) if len(sys.argv) > 4 else 1.0)
    elif cmd == "cuts":
        a, b = float(sys.argv[2]), float(sys.argv[3])
        print([round(c, 2) for c in M["cuts"] if a <= c <= b])
