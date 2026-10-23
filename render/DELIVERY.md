# Delivery

Everything here is generated from `graphics/timeline.json` — nothing is hand-edited.

## The file that ships in git

| | |
|---|---|
| `deepseek_overlay_full_720p.mp4` | the whole 27:21 source with the overlay burn-in |
| Video | 1280×720 · 30 fps · H.264 High · CRF 27 · 308 kb/s |
| Audio | AAC-LC 44.1 kHz stereo, copied from the source timeline |
| Length | 1641.08 s (27:21.08), 49,231 frames — no dropped frames |
| Size | 98,118,215 bytes (93.6 MiB) |
| SHA-256 | `7b05b26b30f6ac7bcbf9877accb8d3c749ab6b64b55b59826b207de4fd1823dd` |

Verify after pulling:

```bash
shasum -a 256 render/deepseek_overlay_full_720p.mp4
# macOS/Linux: shasum -a 256   |   Windows: certutil -hashfile <file> SHA256
```

## Why CRF 27 and not the master

GitHub rejects any single file over 100 MiB, and `git-lfs` is not installable in the environment
this was built in (no packaged binary, and the LFS upload endpoint is not reachable). The master
render is encoded at CRF 20 and is 148 MB, so it cannot live in the repository. The committed copy
is a fresh encode *from the source + ASS* at CRF 27 — not a re-encode of the master, so there is
no generation loss, just a higher quantiser.

Both are one command:

```bash
bash scripts/ffmpeg_overlay.sh 0 "" render/master.mp4              # CRF 20, ~148 MB
CRF=27 bash scripts/ffmpeg_overlay.sh 0 "" render/review.mp4       # CRF 27, ~94 MB
```

## The rest

`deepseek_overlay_highlights.mp4` (8:04, 60 fps), `intro_1017.mp4` (48 s, 1080p60),
`intro_bed.m4a` and `overlay.ass` are all under the limit but are still git-ignored to keep clone
size sane; `make serve` streams them with HTTP Range support.
