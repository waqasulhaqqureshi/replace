# Architecture

One timeline, three consumers. The point of this project is that the *decision* about what
graphic appears when lives in exactly one file, and every renderer reads it.

```
Deepseek strikes again.mp4  (1280×720 · 30 fps · 27:21)
        │
        ├── scripts/analyze_video.py ──────► analysis/metrics.json       (1 fps measurements)
        │                                    analysis/audio.wav
        │                                    analysis/blocks/*.jpg       (visual review sheets)
        │
        ├── scripts/build_timeline.py ─────► graphics/timeline.json      ◄── THE SOURCE OF TRUTH
        │        (annotation + measured)     graphics/waveform.json
        │
        ├── scripts/render_overlay.py ─────► render/*.mp4                (PIL burn-in, 30/60 fps)
        │   └── scripts/overlay_lib.py       19 motion primitives
        │
        ├── scripts/make_ffmpeg_ass.py ────► render/overlay.ass          (libass burn-in)
        │   └── scripts/ffmpeg_overlay.sh    one-pass native FFmpeg
        │
        └── web/ ──────────────────────────► live player                  (React + Framer + GSAP)
             └── src/data/timeline.json     (same JSON, shipped to the client)
```

## Why a single JSON timeline

| Problem | Naive approach | What we do |
|---|---|---|
| Index drifts from the render | Markdown table, hand-edited | `make_docs.py` generates the table *from* the JSON |
| Web player disagrees with the burned-in file | Rebuild the graphics twice | The web app ships the same events and the same primitives |
| A graphic lands on top of important content | Eyeballing frames | Every event carries `measured.lum / motion / black` for its span, so placement is data-driven |
| Rework after a note ("move it off the face") | Re-time by hand | Edit one `box` value in `build_timeline.py`, re-run three scripts |

## Data model (`graphics/timeline.json`)

```jsonc
{
  "brand": { "palette": {...}, "motion": { "enter_s": 0.46, "exit_s": 0.34, "stagger_s": 0.055 } },
  "duration_s": 1641,
  "chapters": [ { "id": "ch01", "t0": 0, "t1": 151.5, "title": "Cold Open" } ],
  "events": [{
    "id": "e005",
    "t0": 20.5, "t1": 28.6,             // absolute seconds — the trigger contract
    "kind": "callout",                   // selects the primitive
    "box": [0.055, 0.10, 0.33, 0.30],    // normalised x, y, w, h on a 1280×720 stage
    "accent": "lime",                    // palette token
    "motion": "slide_up",                // enter/exit grammar
    "anchor": [0.40, 0.52], "pointer": true,   // optional leader line target
    "title": "HLE (w/o tools)", "value": 42.0, "suffix": "%",
    "measured": { "motion": 34.3, "lum": 26.8, "audio_db": -22.3, "recommended_ink": "light" }
  }],
  "audio_cues": [ { "t": 491.3, "type": "silence", "note": "measured 0.96 s gap — hold all motion" } ]
}
```

**Coordinate contract:** the stage is always 1280×720. The Python renderer scales by
`H/720`; the web player applies `transform: scale(containerWidth/1280)`. That is why the live
player and the burned-in file are pixel-equivalent even at 1080p or 4K.

## The 19 motion primitives

| Primitive | Purpose | Renderer support |
|---|---|---|
| `id_card`, `lower_third` | nameplates, chapter ID | PIL · ASS · web |
| `callout` | glass card + optional leader line to a focal point | PIL · ASS · web |
| `stat` | counted metric | PIL · ASS · web |
| `corner` | margin annotation for plates that already carry big type | PIL · ASS · web |
| `chapter`, `caption` | kinetic typography, typewriter / word-mask | PIL · ASS · web |
| `ticker` | scrub-safe marquee rail | PIL · ASS · web |
| `bracket` | HUD frame + ticks + crosshair around a region | PIL · web |
| `leaderboard` | ranked rows with delta chips | PIL · web |
| `bars` | staggered horizontal bars | PIL · web |
| `progress` | value rail with live fraction | PIL · web |
| `gauge`, `donut` | needle sweep / ring sweep | PIL · web |
| `quadrant` | cost × speed scatter with frontier curve | PIL · web |
| `equation` | proof beat with underline sweep | PIL · ASS · web |
| `speed_hud` | delta + speed streaks | PIL · web |
| `ring` | tracking ring on a focal point | PIL · web |
| `waveform` | canvas waveform from the real audio envelope | PIL · web |
| `ad_break` | broadcast stinger | PIL · ASS · web |
| `end_card` | pulse rings + play glyph | PIL · ASS · web |

`ASS` is a subset by design: libass is excellent at type and rectangles, but bars, gauges and
canvas waveforms belong on the Python/web paths.

## Web player internals

```
web/src/
  lib/useVideoClock.ts    rAF clock: rVFC anchor + wall-time interpolation, 80 ms drift guard
  lib/useActiveEvents.ts  timestamp trigger: setState only when the active SET changes
  lib/useFrame.ts         shared rAF, easing + count-up (mirrors overlay_lib)
  overlay/TimelineOverlay.tsx   compositor: AnimatePresence over active events
  overlay/primitives/*.tsx      Framer Motion components (Cards / Data / Motion)
  ui/Transport.tsx        transport, scrub, rate, sync-offset calibration
  ui/Overview.tsx         canvas timeline map (chapters, envelope, event ticks) + GSAP head
  ui/SceneIndex.tsx       searchable timestamp table (same data as the docs)
  ui/Telemetry.tsx        live measured plate stats for the current playhead
```

Three performance rules make 60 fps achievable with ~30 DOM nodes animating:

1. **The playhead never re-renders React.** `useVideoClock` exposes a `MutableRefObject<number>`
   and a separate state mirror throttled to 20 Hz for chrome only.
2. **Counters write `textContent` directly** instead of setting state per frame.
3. **Every animated node is transform/opacity only** (`translate3d`, `scaleX`), marked
   `will-change: transform` — no layout or paint on the compositor path.

`useActiveEvents` also fires `onEnter` / `onExit`, and the app re-broadcasts these as
`window.dispatchEvent(new CustomEvent('dg:enter', { detail: ev }))`, so a host page can hang
sound design, analytics or a CMS preview off the same timestamps.

## Render pipeline

`scripts/render_overlay.py` decodes with ffmpeg to raw RGB, composites per frame in PIL, and
pipes RGBA into a second ffmpeg for x264. Two optimisations matter:

- Frames outside every event window are passed through **without** compositing.
- `--render-fps 60` re-times the deltas so overlay motion is authored at 60 fps even though the
  source plate is 30 fps (ffmpeg's `fps` filter frame-doubles the plate). Counters, rings and
  rails therefore animate smoothly; the plate stays untouched.

Measured throughput on this sandbox (1 vCPU): **45–55 fps** at 720p for the 30 fps pipeline,
**~50 fps** for the 60 fps pipeline, i.e. roughly **17–20 minutes** for the full 27-minute film.

## Reproduce everything

```bash
python3 scripts/analyze_video.py          # ~70 s   → analysis/metrics.json
python3 scripts/build_timeline.py         # instant → graphics/timeline.json
python3 scripts/make_docs.py              # instant → docs/SCENE_INDEX.md
python3 scripts/make_ffmpeg_ass.py        # instant → render/overlay.ass
python3 scripts/render_overlay.py --segments "0-62,150-240,..." --render-fps 60
python3 scripts/synth_audio.py            # ~5 s    → render/intro_bed.m4a
python3 scripts/render_intro.py           # ~8 min  → render/intro_1017.mp4
cd web && npm install && npm run dev      # live player on :5173
```
