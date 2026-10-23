# Block Analysis — 5-Minute Windows

Measured on the source at 1 fps: luminance, saturation, frame-to-frame motion, edge density, UI/text density, near-black ratio, audio level and dominant hue. `static UI %` is the share of seconds that are frozen text screens — the signal that a section needs an animated rail rather than more panels.

| Block | Window | Lum | Sat | Motion (mean/max) | Edge | Text | Black | Static UI | Dominant hue | Audio dB |
|-------|--------|-----|-----|-------------------|------|------|-------|-----------|--------------|----------|
| 1 | `00:00-05:00` | 56 | 0.12 | 13.7 / 213 | 0.084 | 0.089 | 0.33 | 49% | 240° | -22.5 |
| 2 | `05:00-10:00` | 57 | 0.17 | 10.7 / 157 | 0.141 | 0.138 | 0.05 | 72% | 240° | -23.3 |
| 3 | `10:00-15:00` | 69 | 0.23 | 22.7 / 179 | 0.118 | 0.105 | 0.17 | 44% | 240° | -23.1 |
| 4 | `15:00-20:00` | 84 | 0.07 | 9.5 / 182 | 0.132 | 0.130 | 0.05 | 52% | 240° | -22.3 |
| 5 | `20:00-25:00` | 94 | 0.26 | 13.6 / 229 | 0.133 | 0.129 | 0.40 | 48% | 210° | -23.1 |
| 6 | `25:00-27:21` | 84 | 0.22 | 19.4 / 219 | 0.092 | 0.091 | 0.48 | 28% | 210° | -23.9 |

## What the numbers say

- **Busiest plate:** block 3 (`10:00-15:00`) at 22.7 mean Δ — graphics must be light-touch here.
- **Stillest plate:** block 4 (`15:00-20:00`) at 9.5 mean Δ — the safest place for dense data panels.
- **Darkest plate:** block 1 at luminance 56/255 — accents must be bright (cyan/lime), never mid-grey.
- **Most text-heavy:** block 2 at text density 0.138 — overlay only in margins, never over copy.
- **Colour identity:** all six blocks are blue-dominant (210–240°); every overlay accent was chosen to *contrast* with that field, which is why the system leads with cyan, lime and amber rather than more blue.

## Creative calls — where the graphics stay out of the way

The measured plate decides the treatment. Where the source already animates its own data, adding a second chart reads as clutter, so those windows get margin notes or nothing at all. These are the deliberate gaps:

- `02:50–03:50` — the Eratosthenes interlude animates itself (map, shadow, type) — margin corner notes only, no panels.
- `16:25–18:40` — the model section carries its own tables and charts — callouts sit in the left margin, never over the data.
- `21:20–22:25` — the Numbers chapter runs a benchmark table → bar race → cost/speed scatter, all full-frame. Earlier drafts drew our own bars and a quadrant lens over them and were unreadable; the window is now clean apart from the top-edge delta ticker, which rides the source's browser chrome.
- `23:20–24:40` — the infrastructure section already shows a gauge, a 20/80 bar and a cache donut, so the three HUDs here deliberately measure *different* quantities (fabric utilisation, $/GPU-hour, prefill avoided) instead of restating the source's own numbers.
