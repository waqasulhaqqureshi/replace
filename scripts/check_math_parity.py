#!/usr/bin/env python3
"""
check_math_parity.py — proves the React player and the Python burn-in renderer
animate to the same numbers.

Both runtimes implement the same easing curves and the same decelerating
count-up. If they drift, a counter in the live player lands on a different value
than the burned-in file at the same timestamp. This compares them numerically.

    python3 scripts/check_math_parity.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import overlay_lib as OL  # noqa: E402

WEB = ROOT / "web"


def main() -> int:
    if not (WEB / "node_modules").exists():
        print("web/node_modules missing — run `cd web && npm install` first")
        return 1
    out = Path("/tmp/_parity.ts")
    src = (ROOT / "scripts" / "checks" / "math_parity.ts").read_text()
    out.write_text(src.replace("/home/user/replace", str(ROOT)))
    js = Path("/tmp/_parity.cjs")
    subprocess.run(["npx", "esbuild", str(out), "--bundle", "--platform=node",
                    "--format=cjs", f"--outfile={js}", "--log-level=error"],
                   cwd=WEB, check=True)
    res = subprocess.run(["node", str(js)], capture_output=True, text=True, check=True)

    bad = n = 0
    for line in res.stdout.strip().splitlines():
        f = line.split("|")
        p = float(f[0])
        if f[1] == "ease":
            pairs = zip((OL.ease_out(p), OL.ease_in(p), OL.ease_out_back(p)),
                        (float(f[2]), float(f[3]), float(f[4])))
            for a, b in pairs:
                n += 1
                if abs(a - b) > 2e-3:
                    bad += 1
                    print(f"  MISMATCH ease p={p}: py={a:.6f} js={b:.6f}")
            continue
        target, js_val = float(f[1]), float(f[2])
        py_val = OL.count_at(target, p)
        n += 1
        if abs(py_val - js_val) > max(0.01, abs(py_val) * 1e-4):
            bad += 1
            print(f"  MISMATCH count p={p} target={target}: py={py_val:.4f} js={js_val}")

    print(f"compared {n} values across the Python renderer and the React player · "
          f"mismatches: {bad}")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
