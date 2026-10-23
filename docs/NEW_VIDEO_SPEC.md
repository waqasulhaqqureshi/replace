# New Video Specification — "1017"

**Deliverable:** `render/intro_1017.mp4` · 48 s · 1920×1080 · 60 fps · H.264 High · AAC 192 kbps

A standalone cold-open / channel ident **derived from** the 27-minute source. It does not
recap the video; it compresses the video's *argument* into 48 seconds and reuses the source's
own visual language (the Eratosthenes interlude, the benchmark numbers, the model card).

---

## 1. Why these 48 seconds

The source has three structural signals that a trailer should amplify, all measured in
`analysis/metrics.json`:

| Signal | Evidence in the source | How the intro uses it |
|---|---|---|
| The source already edits itself as motion graphics | `02:50–03:50` is a fully animated serif explainer ("The shadow that measured the Earth"), the only section with near-zero plate motion and full typographic control | The intro borrows its two-line serif/italic lockup rhythm and its 7.2° motif |
| The payload is four numbers | `00:16` 1M context · `20:45` benchmark table · `23:50` 155T tokens/day · `24:30` 96% cache hit | Scene 4 is a three-up stat wall, the trailer's data beat |
| The source's own stinger vocabulary | `11:20` montage uses pink "30 SEC / DURATION / OMNI REFERENCE" broadcast furniture; `12:36` uses a black card with a lime wordmark | The intro's skyline is *measurement* furniture (graticule, ticks, gauges), not meme furniture |

Runtime was fixed at **48 s**: long enough for a 3-beat narrative at 120 BPM (24 bars), short
enough to sit in front of a 27-minute video without taxing retention.

---

## 2. Storyboard

Frame numbers are at 60 fps. `t` is seconds.

### Scene 1 — IGNITION · `t 0.0 – 4.2` · frames 0–252
- **Picture:** single point of light on a deep navy field; it blooms into an elliptical glow and
  a horizon line sweeps out to full width. Grid fades up underneath.
- **Type:** margin note, lower-left — kicker `BUILD 1017 · OCT 17`, line `a new model, released in public`.
- **Motion:** point scale 0→1 with `easeOutCubic`, glow radius +190 px over 0.5 s, horizon
  `scaleX 0→1.05` starting at 25% of the scene.
- **Audio cue:** impact at `t 0.35` (sub drop + noise burst).
- **Transition out:** hard cut on the beat.

### Scene 2 — THE FIELD · `t 4.2 – 10.5` · frames 252–630
- **Picture:** wireframe graticule globe, 12 meridians / 6 parallels, rotating at 0.42 rad/s,
  with 48 orbit ticks.
- **Type (hero):** kicker `01 · THE FIELD`, `Every model predicts.` at 62–132 px auto-fit,
  sub `Few can build.`
- **Motion:** globe radius 0.85→1.0, line alpha 0→200 over 0.9 s; headline rises 26 px.
- **Audio cue:** riser tail at `t 4.2`.
- **Transition:** the globe is kept as a 60%-alpha ghost into scene 3 (no cut).

### Scene 3 — THE LOOP · `t 10.5 – 18.0` · frames 630–1080
- **Picture:** the same globe, held as a ghost, while three words replace each other.
- **Type:** `Prompt.` → `Agent.` → `Artefact.` — one word per 2.3–3.0 s, each with the same
  rise-and-underline motion. Third word switches accent to lime (resolution colour).
- **Motion:** word swap is a 120 ms cross-dissolve; underline wipes left→right.
- **Audio cue:** low hit on each word (`t 10.5 / 13.7 / 16.1`).
- **Transition:** hard cut into the stat wall.

### Scene 4 — NUMBERS · `t 18.0 – 24.0` · frames 1080–1440
- **Picture:** three glass stat cards on the graticule ghost, placed on a strict 1/3 grid
  (`x = 0.075 / 0.365 / 0.655`).
- **Type:** `155T` tokens/day · `1M` context window · `42%` HLE (no tools).
- **Motion:** cards pop in at 18.3 / 18.7 / 19.1 s (400 ms apart), numbers count up with a
  decelerating ease over 460 ms each.
- **Audio cue:** three percussive ticks locked to the card entries.
- **Transition:** cards exit upward, staggered by 60 ms.

### Scene 5 — MESH · `t 24.0 – 30.0` · frames 1440–1800
- **Picture:** a rotating cube wireframe (8 vertices, 12 edges) that relaxes toward a sphere
  over the second half of the scene — "a wish becomes an artefact".
- **Type:** callout card, left third — `WISH-DRIVEN / Say the outcome. / the harness finds the path`.
- **Motion:** vertex interpolation `p = easeOut((t-27)/3)`; vertices are lime dots, edges cyan.
- **Audio cue:** filter sweep up across the morph.
- **Transition:** cut on the sphere completing.

### Scene 6 — SHADOW · `t 30.0 – 36.0` · frames 1800–2160
- **Picture:** the source's Eratosthenes diagram, rebuilt: vertical stick, five amber sun rays,
  and a 7.2° wedge that draws itself; the ground shadow extends with the wedge.
- **Type:** `PROOF / 7.2° = 1/50 / two cities · one shadow`.
- **Motion:** arc sweep 0→7.2° over 1.0 s, shadow length `tan(θ)·h`.
- **Audio cue:** riser begins at `t 30.0`, peaks at 36.0.
- **Transition:** white-hot bloom into the title.

### Scene 7 — TITLE · `t 36.0 – 43.5` · frames 2160–2610
- **Picture:** six concentric ellipse rings behind the lockup, plus a lime arc sweeping at
  40°/s.
- **Type (hero):** kicker `DEEPSEEK`, `V4.1-Flash 1017` at up to 132 px auto-fit,
  sub `wish-driven programming`.
- **Motion:** pop scale 0.93→1.0 with `easeOutBack(2.0)`; rings draw outward.
- **Audio cue:** impact + sub drop at 36.0 (the loudest event in the bed).

### Scene 8 — OUTRO · `t 43.5 – 48.0` · frames 2610–2880
- **Picture:** rings persist, dimmed.
- **Type:** kicker `OPEN SOURCE · MIT LICENSE`, `Weights, harness, DeepInfer.`,
  sub `MIT · published today`, plus a lime margin note `wish-driven programming`.
- **Motion:** pop-in, then a 1.2 s audio fade and a video fade to black.
- **Audio cue:** resolve at 43.5, tail fades.

---

## 3. Visual style guide

| Token | Value | Used for |
|---|---|---|
| `void` | `#05070D` | plate base |
| `ink` / `panel` | `#0B1020` / `#0F1526` | card fills |
| `cyan` | `#2FE9FF` | primary structure, graticule, first accent |
| `lime` | `#B6FF3C` | resolution / success / "artefact" |
| `amber` | `#FFB020` | proof, sun rays, caution |
| `magenta` | `#FF2D6F` | only in the ad-break stinger language |
| `paper` | `#F2F6FF` | headlines |
| `muted` | `#8FA2C4` | secondary copy |

- **Type:** display = DejaVu Sans Bold (in-repo, deterministic); mono = DejaVu Sans Mono;
  serif = DejaVu Serif for the interlude callback. Fit rule: hero auto-shrinks from 132 px to
  a 34 px floor rather than overflow the safe area.
- **Safe area:** 4.5% left/right, 5.5% top, 7% bottom.
- **Motion grammar:** enter 460 ms `cubicOut`, exit 340 ms `cubicIn`, 55 ms child stagger,
  `easeOutBack(1.7)` on pops only. Nothing linear except the marquee and orbit rotation.
- **Texture:** 8 pre-rendered grain plates cycled per frame (σ = 2.6), quarter-res blurred
  vignette and volumetric washes.

---

## 4. Background audio — sync map

The bed is **procedurally generated** (`scripts/synth_audio.py`): 120 BPM, A minor 9 pad,
four-on-the-floor sub + kick, off-beat hats, noise riser, sub-drop impacts. No licensed music
is used or required.

| t | Cue | Layer |
|---|---|---|
| 0.35 | impact | noise burst + 62 Hz sub drop |
| 4.20 | riser tail | band-passed noise |
| 10.50 | low hit | burst + sub drop |
| 13.70 | low hit | burst + sub drop |
| 16.10 | low hit (lime accented) | burst + sub drop |
| 18.00 | beats enter | kick + sub on every beat |
| 24.00 | morph swell | filter opening across 6 s |
| 30.00 | riser | 6 s noise sweep, peaking at 36.0 |
| 36.00 | title impact | loudest event |
| 43.50 | resolve | pad-only, 1.2 s fade out |

Regenerate with `python3 scripts/synth_audio.py --dur 48`; swap in a licensed track by
replacing `render/intro_bed.m4a` and re-running `render_intro.py` — the cue map above is where
the cuts land, so any track at 120 BPM drops in cleanly.

---

## 5. Transition logic

| From → To | Transition | Duration | Reason |
|---|---|---|---|
| 1 → 2 | hard cut on the beat | 0 | beat-locked edit |
| 2 → 3 | **no cut** — globe persists as 60% ghost | — | keeps continuity through the three words |
| 3 → 4 | hard cut | 0 | energy step |
| 4 → 5 | cards exit up, staggered 60 ms | 340 ms | directional continuity |
| 5 → 6 | cut on sphere completion | 0 | "solve" beat |
| 6 → 7 | bloom (glow plate brightens 0→1) | 400 ms | light-leak into the title |
| 7 → 8 | dip to 20% rings, no cut | 600 ms | the outro is the title, dimmed |

---

## 6. Asset generator parameters

```bash
# 1. soundtrack (deterministic, no external assets)
python3 scripts/synth_audio.py --dur 48 --out render/intro_bed.wav

# 2. film — backgrounds are procedural, type comes from overlay_lib primitives
python3 scripts/render_intro.py --out render/intro_1017.mp4 --crf 19

# 3. derivations (social cuts) — no re-render needed, stream copy + crop
ffmpeg -i render/intro_1017.mp4 -vf "crop=1080:1080:420:0,scale=1080:1080" -c:a copy out/intro_square.mp4
ffmpeg -i render/intro_1017.mp4 -vf "crop=608:1080:656:0,scale=608:1080" -c:a copy out/intro_vertical.mp4
ffmpeg -i render/intro_1017.mp4 -vf "crop=1080:1920" -c:a copy out/intro_story.mp4   # needs re-layout, see note
```

> The vertical cut is a crop for preview only — the safe area is authored for 16:9. For a real
> 9:16 master, re-run `render_intro.py` with `W, H = 1080, 1920` and shift the event boxes into
> the vertical safe area; the primitives are already resolution-independent.

**Determinism:** every frame is a pure function of `t` — grain is cycled from a fixed seed set,
backgrounds cache on a 0.25 s grid. Re-rendering the same command produces a bit-identical
mp4 (same x264 build and CRF).
