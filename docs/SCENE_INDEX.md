# Timestamp Scene Index — 30-Minute Source

**Source:** `Deepseek strikes again.mp4` · 1280×720 · 30 fps · duration **27:21** (the file is 27:21, not a full 30:00 — the index covers every second of it).

**Beats:** 56 graphics events across 14 chapters · **1641** seconds analysed at 1 fps · **777** hard cuts detected by ffmpeg scene scoring.


> Every row is machine-generated from `graphics/timeline.json`, which is the same file the burn-in renderer and the React player consume. `motion / lum` are the measured mean frame-delta and plate luminance of the beat's span — they tell you how much visual headroom the graphic has to work with.


## CH01 · Cold Open (`00:00–02:32`)
*Launch day, build 1017*

| In | Out | Dur | Graphic | Copy / data | Motion | plate motion / lum | Why this beat |
|----|-----|-----|---------|-------------|--------|---------------------|----------------|
| `00:00` | `00:07` | 6.2s | **Nameplate** | BUILD 1017 · PUBLIC RELEASE — DEEPSEEK V4.1-FLASH — Wish-driven programming · Oct 17 | accent bar wipe · kicker fade · headline rise · rule scaleX | 16.8 / 27 | Show ID on the talking-head; sits in lower third so the face is never covered. |
| `00:07` | `00:13` | 6.0s | **Ticker rail** | LIVE  ·  LAUNCH QUEUE  ·  1,284 IN LINE  ·  SHENZHEN 22:40 | marquee offset = (t − t0) × 46 px/s (scrub-safe) | 17.5 / 32 | Crowd shot reads as a live event; a marquee ticker sells it instantly. |
| `00:13` | `00:20` | 7.7s | **Tracking ring** | SIGNAL BLOOM — agent trace · 1M-token context | arc sweep + rotating dashed orbit · pulsing centre dot | 50.4 / 189 | The glowing tree is the most photogenic frame in the first minute: track it with a ring. |
| `00:16` | `00:22` | 5.6s | **Metric counter** | 1e+06 — TOKENS IN ONE CONTEXT | count-up (decelerating) · label fade · hairline progress | 34.0 / 175 | Counter lands while the tree is on screen. |
| `00:20` | `00:29` | 8.1s | **Callout card** | RELEASE NOTES — 42% — HLE (w/o tools) — +5.7 vs V4.1 · +4.5 vs GPT-5.5 | panel rise 26 px · staggered rows · leader line draws to anchor | 34.3 / 26 | Blog hero table is the story beat — point at the HLE row and pull the number. |
| `00:25` | `00:29` | 3.8s | **Ticker rail** | INFERENCE FABRIC  //  155T TOKENS / DAY  //  SGLANG + SGLANG-ROUTER | marquee offset = (t − t0) × 46 px/s (scrub-safe) | 38.6 / 49 | Server bokeh: quiet telemetry rail at the bottom. |
| `00:29` | `00:45` | 15.6s | **Speed HUD** | 38 — LATENCY — p50 −38% vs prior build | delta count-up · speed streaks translate | 50.5 / 91 | Flying/man leaping shot gets a speed HUD + motion streaks. |
| `00:45` | `00:50` | 5.3s | **Lower third** | CHAPTER 01 — Harness in public preview — Windows · macOS (Apple silicon) · Linux | as nameplate | 37.5 / 86 |  |
| `00:50` | `01:00` | 9.5s | **HUD bracket** | BENCHMARK TABLE | corner strokes draw (pathLength) · tick marks · crosshair | 17.1 / 204 | README hero table sits in the lower third — frame it, don't cover it. |
| `01:00` | `01:14` | 14.0s | **Callout card** | HARNESS · CHAT — Wish-driven — intent → tool chain → artefact | panel rise 26 px · staggered rows · leader line draws to anchor | 30.0 / 84 |  |
| `01:20` | `01:35` | 15.0s | **Callout card** | ONE-CLICK INSTALL — Ready to use. Right now. — Windows=x64 · macOS=Apple silicon · Linux=AppImage | panel rise 26 px · staggered rows · leader line draws to anchor | 8.1 / 50 |  |
| `01:39` | `01:52` | 13.0s | **HUD bracket** | HUMAN VERIFICATION | corner strokes draw (pathLength) · tick marks · crosshair | 28.9 / 88 | The captcha is a joke beat; a deadpan machine-vision bracket makes it land. |
| `02:00` | `02:20` | 20.0s | **Ticker rail** | REASONING TRACE  ·  1,284 TOKENS  ·  TOOLS: BASH, READ, GREP | marquee offset = (t − t0) × 46 px/s (scrub-safe) | 0.5 / 34 |  |

## CH02 · The Drop (`02:32–02:48`)
*Blog + benchmark reveal*

_No overlay — intentional breathing room._

## CH03 · The Shadow That Measured the Earth (`02:48–03:50`)
*Interstitial explainer*

| In | Out | Dur | Graphic | Copy / data | Motion | plate motion / lum | Why this beat |
|----|-----|-----|---------|-------------|--------|---------------------|----------------|
| `02:48` | `02:56` | 8.4s | **Margin note** | INTERLUDE 01 — Eratosthenes · 240 BCE · Syene | kicker track-in · rule wipe | 3.5 / 9 | The source already typesets its own serif card: annotate at the margin only. |
| `02:56` | `03:10` | 14.0s | **Margin note** | INTERLUDE 01 · GEOMETRY — well at Syene · stick at Alexandria | kicker track-in · rule wipe | 0.9 / 4 |  |
| `03:10` | `03:18` | 7.5s | **Margin note** | INTERLUDE 01 · THE MEASUREMENT — θ/360 = 5000 / 250,000 → 1/50 | kicker track-in · rule wipe | 0.6 / 2 | Source typesets its own 7.2° headline here — annotate at the margin only. |
| `03:18` | `03:28` | 10.5s | **Margin note** | INTERLUDE 01 · THE PROOF — C = 50 × 5,000 = 250,000 stadia | kicker track-in · rule wipe | 0.7 / 3 |  |
| `03:36` | `03:48` | 12.0s | **Metric counter** | 39,375 km — modern 40,008 km · −1.6% — KM · ERROR vs MODERN | count-up (decelerating) · label fade · hairline progress | 1.1 / 3 | The source already animates '39,375 km' on the left — the overlay owns the empty right side and reframes it as an error figure instead of repeating it. |
| `03:48` | `03:54` | 5.5s | **Margin note** | INTERLUDE 01 · OUT — ratio 1/50 → 250,000 stadia | kicker track-in · rule wipe | 1.6 / 5 |  |

## CH04 · Harness (`03:50–06:00`)
*Wish-driven programming*

| In | Out | Dur | Graphic | Copy / data | Motion | plate motion / lum | Why this beat |
|----|-----|-----|---------|-------------|--------|---------------------|----------------|
| `04:00` | `04:18` | 18.0s | **Ticker rail** | SANDBOX  ·  rust-playground  ·  exit code 0  ·  42 ms | marquee offset = (t − t0) × 46 px/s (scrub-safe) | 2.9 / 30 |  |
| `04:40` | `05:00` | 20.0s | **HUD bracket** | TEXT → MESH — 4,182 tris · PBR · auto-rig | corner strokes draw (pathLength) · tick marks · crosshair | 15.3 / 134 | Tripo 3D viewport: frame the model, keep the tool chrome visible. |
| `05:00` | `05:20` | 20.0s | **HUD bracket** | SCENE ASSEMBLY | corner strokes draw (pathLength) · tick marks · crosshair | 11.6 / 42 |  |
| `05:40` | `06:00` | 20.0s | **Progress rail** | 3 — ASSETS — 3 / 6 generated | bar fills over 1.1 s · live fraction label | 0.1 / 39 |  |

## CH05 · Game Dev (`06:00–11:19`)
*Blender → engine → playable*

| In | Out | Dur | Graphic | Copy / data | Motion | plate motion / lum | Why this beat |
|----|-----|-----|---------|-------------|--------|---------------------|----------------|
| `06:20` | `06:40` | 20.0s | **Lower third** | PROMPT → PLAYABLE — Forbidden City, playable — engine build · 60 fps target | as nameplate | 38.5 / 86 |  |
| `07:00` | `07:20` | 20.0s | **Ticker rail** | GAME BRIEF  ·  third-person · stamina bar · shadow map 4k | marquee offset = (t − t0) × 46 px/s (scrub-safe) | 32.1 / 67 |  |
| `07:20` | `07:44` | 24.0s | **Live waveform** | EDM · 128 BPM — prompt → stems → mix | canvas redraw @60fps from real audio envelope + playhead | 16.2 / 42 | Prompt beat: show the hypothetical groove before the DAW appears. |
| `08:00` | `11:18` | 198.0s | **Live waveform** | STEMS · 12 TRACKS — 128 BPM · A minor | canvas redraw @60fps from real audio envelope + playhead | 1.3 / 65 | 16 min of DAW screen — a live waveform rail keeps it from feeling static. |
| `08:00` | `09:20` | 80.0s | **Metric counter** | 128 — BPM | count-up (decelerating) · label fade · hairline progress | 1.4 / 61 |  |
| `09:20` | `10:20` | 60.0s | **Bar chart** | LOUDNESS — Integrated=−9.8 LUFS · True peak=−0.1 dB · LRA=6.2 LU | bars grow scaleX, 70 ms stagger | 1.2 / 69 |  |

## CH06 · Audio (`11:19–12:40`)
*EDM from a prompt*

| In | Out | Dur | Graphic | Copy / data | Motion | plate motion / lum | Why this beat |
|----|-----|-----|---------|-------------|--------|---------------------|----------------|
| `11:20` | `11:40` | 20.0s | **Broadcast stinger** | AD SWEEP — 09 CONCEPTS · ONE PROMPT | skewed stinger scale-in · REC dot blink | 30.7 / 37 | Montage begins: a broadcast-style stinger brands the block. |
| `11:40` | `12:22` | 42.0s | **Progress rail** | 9 — CONCEPT — 09 / 09 rendered | bar fills over 1.1 s · live fraction label | 31.1 / 62 |  |
| `12:00` | `12:36` | 36.0s | **HUD bracket** | START FRAME | corner strokes draw (pathLength) · tick marks · crosshair | 48.1 / 101 |  |
| `12:36` | `12:42` | 6.0s | **Broadcast stinger** | 30 SEC — cut to duration | skewed stinger scale-in · REC dot blink | 52.9 / 64 |  |

## CH07 · Ad Sweep (`12:40–14:50`)
*Nine ad concepts in one prompt*

| In | Out | Dur | Graphic | Copy / data | Motion | plate motion / lum | Why this beat |
|----|-----|-----|---------|-------------|--------|---------------------|----------------|
| `12:45` | `13:20` | 35.0s | **Progress rail** | 4 — PROPERTY TOUR — room 04 / 06 | bar fills over 1.1 s · live fraction label | 24.0 / 95 |  |
| `13:20` | `13:40` | 20.0s | **Callout card** | PLAN MATCH — Living room — 243 m² · 3 bed · sea view | panel rise 26 px · staggered rows · leader line draws to anchor | 25.6 / 57 |  |

## CH08 · Interiors (`14:50–16:00`)
*3D property walkthrough*

| In | Out | Dur | Graphic | Copy / data | Motion | plate motion / lum | Why this beat |
|----|-----|-----|---------|-------------|--------|---------------------|----------------|
| `15:00` | `15:25` | 25.0s | **HUD bracket** | VISION · 12 OBJECTS | corner strokes draw (pathLength) · tick marks · crosshair | 9.4 / 41 | Photo-analysis beat: brackets + confidence chips. |
| `15:05` | `15:25` | 20.0s | **Bar chart** | CONFIDENCE — wing=0.97 · abdomen=0.94 · thorax=0.88 · legs=0.71 | bars grow scaleX, 70 ms stagger | 10.9 / 45 |  |
| `15:50` | `16:35` | 45.0s | **Leaderboard** | DIFFERENTIAL DX — ILD=0.91 · Infection=0.44 · Malignancy=0.12 · Normal=0.03 | rows slide in 80 ms stagger · delta chips pop | 9.1 / 39 | Medical Q&A: a compact differential-probability stack. |

## CH09 · Vision & Research (`16:00–20:00`)
*Image, medical, papers*

| In | Out | Dur | Graphic | Copy / data | Motion | plate motion / lum | Why this beat |
|----|-----|-----|---------|-------------|--------|---------------------|----------------|
| `17:00` | `17:55` | 55.0s | **Progress rail** | 14 — PAPER — p.14 / 32 | bar fills over 1.1 s · live fraction label | 14.2 / 200 |  |
| `19:00` | `19:40` | 40.0s | **Callout card** | SOURCE — 1,000+ simulations — IPCC AR6 · 2 °C pathway | panel rise 26 px · staggered rows · leader line draws to anchor | 5.7 / 32 |  |

## CH10 · The Model (`20:00–21:30`)
*Architecture + benchmark wall*

| In | Out | Dur | Graphic | Copy / data | Motion | plate motion / lum | Why this beat |
|----|-----|-----|---------|-------------|--------|---------------------|----------------|
| `20:20` | `20:45` | 25.0s | **Callout card** | ARCHITECTURE — 40-layer CED — Encoder=20L · Decoder=20L · Active=88 params/token | panel rise 26 px · staggered rows · leader line draws to anchor | 18.2 / 69 |  |
| `20:46` | `20:52` | 6.5s | **Broadcast stinger** | PURE GENIUS — interstitial · 6 s | skewed stinger scale-in · REC dot blink | 32.8 / 87 | The source cuts to a meme card here; tag it instead of fighting it. |
| `20:53` | `21:40` | 47.0s | **Ticker rail** | DELTA vs V4.1   ·   HLE +5.7   ·   TERMINAL-BENCH +11.1   ·   DEEPSWE +3.4   ·   APEX +7.5   ·   BABYVISION +6.7 | marquee offset = (t − t0) × 46 px/s (scrub-safe) | 1.9 / 236 | The source already holds the full table for 40 s: a delta rail at the top edge adds the comparison without covering a single cell. |

## CH11 · The Numbers (`21:30–23:00`)
*Speed, cost, cache, pricing*

| In | Out | Dur | Graphic | Copy / data | Motion | plate motion / lum | Why this beat |
|----|-----|-----|---------|-------------|--------|---------------------|----------------|
| `21:40` | `22:00` | 20.0s | **Bar chart** | SCORE BY BENCH — HLE=42.0 · TB 4.0=42.3 · DeepSWE=77.6 · NL2Repo=68.2 | bars grow scaleX, 70 ms stagger | 16.7 / 58 |  |
| `22:00` | `22:25` | 25.0s | **Quadrant lens** | COST × SPEED — V4.1-Flash-1017=best $/task · GPT-5.5-Base=4× cost · Claude Opus 5=9× cost | frontier curve draws · focal dot pulses | 7.3 / 177 | Log-scale scatter appears at 22:00: a quadrant lens adds the missing read. |
| `22:25` | `22:50` | 25.0s | **Callout card** | OPEN SOURCE — MIT · weights on HF — DeepSeek-V4.1-Flash-1017 | panel rise 26 px · staggered rows · leader line draws to anchor | 13.6 / 135 |  |

## CH12 · The Infra (`23:00–25:00`)
*DeepInfer, GPUs, GPUs/hr*

| In | Out | Dur | Graphic | Copy / data | Motion | plate motion / lum | Why this beat |
|----|-----|-----|---------|-------------|--------|---------------------|----------------|
| `23:20` | `23:40` | 20.0s | **Gauge** | 100 — GPU SPEED — % of peak | needle sweep with easeOutBack overshoot · arc dashoffset | 17.2 / 27 | The source's own gauge at 23:20 — re-draw it as a HUD so the needle sweep reads. |
| `23:39` | `24:00` | 21.0s | **Metric counter** | 155T — single cluster · internet-scale — TRILLION TOKENS / DAY | count-up (decelerating) · label fade · hairline progress | 13.9 / 34 |  |
| `24:00` | `24:19` | 19.0s | **Bar chart** | $30 REVENUE / GPU HOUR — Compute costs=20% · Profit=80% | bars grow scaleX, 70 ms stagger | 6.6 / 28 |  |
| `24:20` | `24:40` | 20.0s | **Donut** | 96% — INPUT CACHE HIT RATE | ring sweep from 12 o'clock · value counts with it | 10.5 / 21 | Donut sweep synced to the 98→96% on-screen counter. |
| `24:40` | `25:00` | 20.0s | **Ticker rail** | PRICING  ·  FREE $0  ·  PLUS $20  ·  PRO $200  ·  1M-TOKEN CONTEXT ON ALL TIERS | marquee offset = (t − t0) × 46 px/s (scrub-safe) | 31.8 / 67 | The pricing cards are already on screen — reinforce as a rail, not a panel. |

## CH13 · Open Source (`25:00–26:43`)
*MIT repo + hardware*

| In | Out | Dur | Graphic | Copy / data | Motion | plate motion / lum | Why this beat |
|----|-----|-----|---------|-------------|--------|---------------------|----------------|
| `25:00` | `25:22` | 22.0s | **Ticker rail** | OPEN SOURCE  ·  MIT LICENSE  ·  deepseek-ai/DeepSeek-V4.1-Flash-1017 | marquee offset = (t − t0) × 46 px/s (scrub-safe) | 12.5 / 38 |  |
| `25:20` | `26:00` | 40.0s | **Callout card** | SERVING STACK — DeepInfer + DeepGEMM — SGLang router · 155T tokens/day | panel rise 26 px · staggered rows · leader line draws to anchor | 14.4 / 50 |  |
| `26:00` | `26:24` | 24.0s | **HUD bracket** | HARDWARE · N100 | corner strokes draw (pathLength) · tick marks · crosshair | 14.7 / 105 |  |

## CH14 · Outro (`26:43–27:21`)
*Subscribe + newsletter*

| In | Out | Dur | Graphic | Copy / data | Motion | plate motion / lum | Why this beat |
|----|-----|-----|---------|-------------|--------|---------------------|----------------|
| `26:43` | `27:01` | 18.0s | **Margin note** | OUTRO · BUILD 1017 — full walkthrough in the description | kicker track-in · rule wipe | 36.3 / 60 | Source burns its own SUBSCRIBE card at 26:52 — stay off it. |
| `27:01` | `27:21` | 20.0s | **End card** | AI SEARCH — weekly digest · every Thursday | pulse rings · play glyph scale | 36.3 / 229 |  |
