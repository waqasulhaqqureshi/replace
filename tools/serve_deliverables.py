#!/usr/bin/env python3
"""
serve_deliverables.py — download server for the rendered media.

Serves render/ and out/ over HTTP with the two things a 148 MB video needs and
python -m http.server does not give you:

  * Range requests  → resumable downloads (`curl -C -`) and in-browser seeking
  * Content-Disposition: attachment → clicking a link downloads instead of
    trying to play a 27-minute file inside the preview iframe

    python3 tools/serve_deliverables.py            # 0.0.0.0:8000
    python3 tools/serve_deliverables.py --port 8080

The index page lists every media file with its size and SHA-256, so a download
can be verified on the other end:

    curl -L -O http://<host>:8000/deepseek_overlay_ffmpeg_full.mp4
    shasum -a 256 deepseek_overlay_ffmpeg_full.mp4
"""
from __future__ import annotations

import argparse
import hashlib
import html
import mimetypes
import os
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIRS = [ROOT / "render", ROOT / "out"]
EXTS = {".mp4", ".mov", ".m4a", ".wav", ".ass", ".jpg", ".png"}
CHUNK = 1024 * 256
_sha_cache: dict[Path, tuple[float, str]] = {}

PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Deliverables — download</title>
<style>
 :root {{ color-scheme: dark }}
 body {{ margin:0; padding:40px clamp(16px,6vw,72px); background:#05070d; color:#f2f6ff;
        font:15px/1.55 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif }}
 h1 {{ font-size:clamp(22px,3vw,30px); margin:0 0 6px; letter-spacing:-.02em }}
 p.sub {{ color:#8fa2c4; margin:0 0 28px; max-width:70ch }}
 table {{ border-collapse:collapse; width:100%; max-width:1100px }}
 th,td {{ text-align:left; padding:12px 14px; border-bottom:1px solid #22304b; vertical-align:top }}
 th {{ color:#8fa2c4; font-size:12px; letter-spacing:.14em; text-transform:uppercase; font-weight:600 }}
 td.name a {{ color:#2fe9ff; text-decoration:none; font-weight:600 }}
 td.name a:hover {{ text-decoration:underline }}
 code {{ font-family:ui-monospace,"SF Mono",Menlo,monospace; font-size:12.5px; color:#b6ff3c }}
 .hash {{ color:#6d7f9e; font-size:11.5px; word-break:break-all; display:block; margin-top:4px }}
 .sz {{ color:#8fa2c4; white-space:nowrap }}
 .cmd {{ margin-top:32px; padding:18px 20px; background:#0b1020; border:1px solid #22304b;
         border-radius:10px; max-width:1100px }}
 .cmd h2 {{ font-size:13px; letter-spacing:.14em; text-transform:uppercase; color:#8fa2c4;
            margin:0 0 10px; font-weight:600 }}
 .cmd pre {{ margin:0; overflow-x:auto; color:#e7eeff; font-size:13px; line-height:1.7 }}
 .empty {{ color:#8fa2c4 }}
</style></head><body>
<h1>Deliverables</h1>
<p class="sub">Rendered media from this workspace. Links download the file directly
(Content-Disposition: attachment) and support resuming with <code>curl -C -</code>.</p>
<table><thead><tr><th>File</th><th>Size</th><th>SHA-256</th></tr></thead><tbody>
{rows}
</tbody></table>
<div class="cmd"><h2>Download on your machine</h2><pre>{cmd}</pre></div>
</body></html>
"""


def sha256(path: Path) -> str:
    mtime = path.stat().st_mtime
    hit = _sha_cache.get(path)
    if hit and hit[0] == mtime:
        return hit[1]
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    _sha_cache[path] = (mtime, h.hexdigest())
    return h.hexdigest()


def human(n: float) -> str:
    if n < 1024:
        return f"{n:.0f} B"
    for unit in ("KB", "MB", "GB"):
        n /= 1024.0
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}"
    return f"{n:.1f} GB"


def files() -> list[Path]:
    found: list[Path] = []
    for d in DIRS:
        if d.is_dir():
            found += [p for p in sorted(d.iterdir())
                      if p.is_file() and p.suffix.lower() in EXTS]
    return found


def index_html(port: int, host_header: str, proto: str = "") -> bytes:
    rows, names = [], []
    for p in files():
        size = p.stat().st_size
        names.append(p.name)
        rows.append(
            f'<tr><td class="name"><a href="/{html.escape(p.name)}">{html.escape(p.name)}</a>'
            f'<span class="hash">{sha256(p)}</span></td>'
            f'<td class="sz">{human(size)}</td>'
            f'<td class="sz">{size:,} bytes</td></tr>'
        )
    if not rows:
        rows.append('<tr><td colspan="3" class="empty">no media rendered yet — '
                    'run <code>make render-highlights</code> first</td></tr>')
    host = host_header or f"localhost:{port}"
    # behind the preview proxy the public URL is https, and the Host header is the
    # public one, so the copy-paste commands have to mirror it rather than assume
    # http://localhost.
    scheme = "https" if (proto == "https" or "." in host.split(":")[0]) else "http"
    base = f"{scheme}://{host}"
    cmd = "\n".join(f"curl -L -O {base}/{n}" for n in names) or \
          "bash scripts/ffmpeg_overlay.sh 0 \"\" render/deepseek_overlay_ffmpeg_full.mp4"
    return PAGE.format(rows="\n".join(rows), cmd=html.escape(cmd)).encode()


class Handler(BaseHTTPRequestHandler):
    server_version = "deliverables/1.0"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:  # compact log
        print(f"  {self.address_string()} {fmt % args}")

    def _resolve(self) -> Path | None:
        name = os.path.basename(self.path.split("?")[0]).lstrip("/")
        for d in DIRS:
            cand = d / name
            if cand.is_file() and cand.suffix.lower() in EXTS:
                return cand
        return None

    def do_HEAD(self) -> None:
        self._send(head_only=True)

    def do_GET(self) -> None:
        self._send(head_only=False)

    def _send(self, head_only: bool) -> None:
        if self.path in ("/", "/index.html"):
            body = index_html(self.server.server_port, self.headers.get("Host", ""),
                              self.headers.get("X-Forwarded-Proto", ""))
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if not head_only:
                self.wfile.write(body)
            return

        path = self._resolve()
        if path is None:
            self.send_error(404, "not found")
            return

        size = path.stat().st_size
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        start, end = 0, size - 1
        status = 200
        rng = self.headers.get("Range", "")
        m = re.match(r"bytes=(\d*)-(\d*)$", rng.strip()) if rng else None
        if m:
            a, b = m.group(1), m.group(2)
            if a:
                start = int(a)
                end = int(b) if b else size - 1
            elif b:                                # suffix range: last N bytes
                start = max(0, size - int(b))
            if start >= size or start > end:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            status = 206

        length = end - start + 1
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(length))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Disposition",
                         f'attachment; filename="{path.name}"')
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Last-Modified", time.strftime(
            "%a, %d %b %Y %H:%M:%S GMT", time.gmtime(path.stat().st_mtime)))
        self.end_headers()
        if head_only:
            return
        with path.open("rb") as fh:
            fh.seek(start)
            left = length
            while left > 0:
                block = fh.read(min(CHUNK, left))
                if not block:
                    break
                try:
                    self.wfile.write(block)
                except (BrokenPipeError, ConnectionResetError):
                    return
                left -= len(block)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="0.0.0.0")
    args = ap.parse_args()
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    srv.daemon_threads = True
    print(f"serving {len(files())} file(s) from render/ and out/")
    print(f"  http://{args.host}:{args.port}/")
    for p in files():
        print(f"    {p.name:42} {human(p.stat().st_size):>9}  {sha256(p)[:16]}…")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
