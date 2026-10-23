#!/usr/bin/env python3
"""
build_timeline.py — the editorial brain of the pipeline.

Turns human scene annotation + measured metrics into two machine-readable
artefacts that BOTH the Python burn-in renderer and the React/Framer web
player consume:

  graphics/timeline.json   — chapters, overlay events, audio cues, brand tokens
  graphics/waveform.json   — real 10 Hz peak/RMS envelope of the source audio

Every event carries:
  id, t0, t1, kind, box(0..1), accent, motion, copy fields, items, anchor, note
  plus `measured` (motion / luminance / audio dB / dominant hue of the span),
  so the motion designer can see why the graphic sits where it does.

Run:  python3 scripts/build_timeline.py
"""
from __future__ import annotations

import json
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "graphics"
OUT.mkdir(exist_ok=True)


# ----------------------------------------------------------------- brand tokens
BRAND = {
    "name": "DeepSeek V4.1-Flash · 1017",
    "source": "Deepseek strikes again.mp4",
    "resolution": "1280x720",
    "source_fps": 30,
    "target_fps": 60,
    "palette": {
        "void": "#05070D",
        "ink": "#0B1020",
        "panel": "#0F1526",
        "line": "#22304B",
        "cyan": "#2FE9FF",
        "electric": "#4D6BFE",
        "lime": "#B6FF3C",
        "amber": "#FFB020",
        "magenta": "#FF2D6F",
        "paper": "#F2F6FF",
        "muted": "#8FA2C4",
    },
    "type": {
        "display": "DejaVu Sans Bold",
        "mono": "DejaVu Sans Mono",
        "serif": "DejaVu Serif",
    },
    # motion rules shared by renderer + web
    "motion": {
        "enter_s": 0.46,
        "exit_s": 0.34,
        "stagger_s": 0.055,
        "ease_enter": "cubicOut",
        "ease_exit": "cubicIn",
        "safe_area": [0.045, 0.055, 0.955, 0.93],
    },
}

# ---------------------------------------------------------------------- chapters
CHAPTERS = [
    dict(id="ch01", t0=0, t1=151.5, title="Cold Open", sub="Launch day, build 1017"),
    dict(id="ch02", t0=151.5, t1=167.6, title="The Drop", sub="Blog + benchmark reveal"),
    dict(id="ch03", t0=167.6, t1=230.0, title="The Shadow That Measured the Earth", sub="Interstitial explainer"),
    dict(id="ch04", t0=230.0, t1=360.0, title="Harness", sub="Wish-driven programming"),
    dict(id="ch05", t0=360.0, t1=678.9, title="Game Dev", sub="Blender → engine → playable"),
    dict(id="ch06", t0=678.9, t1=760.0, title="Audio", sub="EDM from a prompt"),
    dict(id="ch07", t0=760.0, t1=890.0, title="Ad Sweep", sub="Nine ad concepts in one prompt"),
    dict(id="ch08", t0=890.0, t1=960.0, title="Interiors", sub="3D property walkthrough"),
    dict(id="ch09", t0=960.0, t1=1200.0, title="Vision & Research", sub="Image, medical, papers"),
    dict(id="ch10", t0=1200.0, t1=1290.0, title="The Model", sub="Architecture + benchmark wall"),
    dict(id="ch11", t0=1290.0, t1=1380.0, title="The Numbers", sub="Speed, cost, cache, pricing"),
    dict(id="ch12", t0=1380.0, t1=1500.0, title="The Infra", sub="DeepInfer, GPUs, GPUs/hr"),
    dict(id="ch13", t0=1500.0, t1=1603.0, title="Open Source", sub="MIT repo + hardware"),
    dict(id="ch14", t0=1603.0, t1=1641.1, title="Outro", sub="Subscribe + newsletter"),
]


def ev(eid, t0, t1, kind, **kw):
    d = dict(id=eid, t0=round(float(t0), 2), t1=round(float(t1), 2), kind=kind)
    d.update(kw)
    return d


# --------------------------------------------------------------- overlay events
# box = [x, y, w, h] normalized to the 1280x720 frame (top-left origin).
# anchor = normalized focal point the graphic points at / rings.
EVENTS = [
    # ---------------- CH 01 · COLD OPEN ---------------------------------------
    ev("e001", 0.4, 6.6, "id_card", box=[0.045, 0.70, 0.46, 0.20], motion="slide_up",
       accent="cyan", kicker="BUILD 1017 · PUBLIC RELEASE",
       title="DEEPSEEK V4.1-FLASH", sub="Wish-driven programming · Oct 17",
       note="Show ID on the talking-head; sits in lower third so the face is never covered."),
    ev("e002", 6.6, 12.6, "ticker", box=[0.0, 0.035, 1.0, 0.052], motion="wipe",
       accent="electric", title="LIVE  ·  LAUNCH QUEUE  ·  1,284 IN LINE  ·  SHENZHEN 22:40",
       note="Crowd shot reads as a live event; a marquee ticker sells it instantly."),
    ev("e003", 12.7, 20.4, "ring", box=[0.5, 0.5, 0.0, 0.0], motion="pop",
       accent="amber", anchor=[0.5, 0.47], title="SIGNAL BLOOM",
       sub="agent trace · 1M-token context",
       note="The glowing tree is the most photogenic frame in the first minute: track it with a ring."),
    ev("e004", 15.9, 21.5, "stat", box=[0.62, 0.10, 0.33, 0.22], motion="pop",
       accent="amber", value=1000000, label="TOKENS IN ONE CONTEXT", fmt="compact",
       note="Counter lands while the tree is on screen."),
    ev("e005", 20.5, 28.6, "callout", box=[0.055, 0.10, 0.33, 0.30], motion="slide_up",
       accent="lime", anchor=[0.40, 0.52], pointer=True,
       kicker="RELEASE NOTES", title="HLE (w/o tools)",
       sub="+5.7 vs V4.1 · +4.5 vs GPT-5.5", value=42.0, suffix="%",
       note="Blog hero table is the story beat — point at the HLE row and pull the number."),
    ev("e006", 25.2, 29.0, "ticker", box=[0.0, 0.90, 1.0, 0.05], motion="wipe",
       accent="cyan", title="INFERENCE FABRIC  //  155T TOKENS / DAY  //  SGLANG + SGLANG-ROUTER",
       note="Server bokeh: quiet telemetry rail at the bottom."),
    ev("e007", 29.1, 44.7, "speed_hud", box=[0.06, 0.16, 0.34, 0.26], motion="slide_up",
       accent="cyan", anchor=[0.52, 0.45], title="LATENCY", value=38,
       sub="p50 −38% vs prior build",
       note="Flying/man leaping shot gets a speed HUD + motion streaks."),
    ev("e008", 44.7, 50.0, "lower_third", box=[0.055, 0.76, 0.50, 0.13], motion="slide_up",
       accent="electric", kicker="CHAPTER 01", title="Harness in public preview",
       sub="Windows · macOS (Apple silicon) · Linux"),
    ev("e009", 50.0, 59.5, "bracket", box=[0.185, 0.755, 0.62, 0.205], motion="draw",
       accent="cyan", anchor=[0.50, 0.86], title="BENCHMARK TABLE",
       note="README hero table sits in the lower third — frame it, don't cover it."),

    # ---------------- CH 02/03 · HARNESS + EXPLAINER --------------------------
    ev("e010", 60.0, 74.0, "callout", box=[0.05, 0.70, 0.34, 0.17], motion="slide_up",
       accent="lime", kicker="HARNESS · CHAT", title="Wish-driven",
       sub="intent → tool chain → artefact"),
    ev("e011", 80.4, 95.4, "callout", box=[0.055, 0.63, 0.40, 0.24], motion="slide_up",
       accent="cyan", kicker="ONE-CLICK INSTALL", title="Ready to use. Right now.",
       items=[dict(label="Windows", value="x64"), dict(label="macOS", value="Apple silicon"),
              dict(label="Linux", value="AppImage")]),
    ev("e012", 99.0, 112.0, "bracket", box=[0.36, 0.30, 0.30, 0.40], motion="draw",
       accent="magenta", anchor=[0.50, 0.50], title="HUMAN VERIFICATION",
       note="The captcha is a joke beat; a deadpan machine-vision bracket makes it land."),
    ev("e013", 120.0, 140.0, "ticker", box=[0.0, 0.035, 1.0, 0.05], motion="wipe",
       accent="electric", title="REASONING TRACE  ·  1,284 TOKENS  ·  TOOLS: BASH, READ, GREP"),

    # chapter card + explainer (the source's own motion-graphics interlude)
    ev("e014", 167.6, 176.0, "corner", box=[0.055, 0.775, 0.33, 0.12], motion="slide_up",
       accent="amber", kicker="INTERLUDE 01",
       title="Eratosthenes · 240 BCE · Syene",
       note="The source already typesets its own serif card: annotate at the margin only."),
    ev("e015", 176.0, 190.0, "corner", box=[0.055, 0.775, 0.35, 0.12], motion="slide_up",
       accent="amber", kicker="INTERLUDE 01 · GEOMETRY",
       title="well at Syene · stick at Alexandria"),
    ev("e016", 190.0, 197.5, "corner", box=[0.055, 0.775, 0.34, 0.12], motion="slide_up",
       accent="amber", kicker="INTERLUDE 01 · THE MEASUREMENT",
       title="θ/360 = 5000 / 250,000 → 1/50",
       note="Source typesets its own 7.2° headline here — annotate at the margin only."),
    ev("e017", 197.5, 208.0, "corner", box=[0.055, 0.775, 0.34, 0.12], motion="slide_up",
       accent="cyan", kicker="INTERLUDE 01 · THE PROOF",
       title="C = 50 × 5,000 = 250,000 stadia"),
    ev("e018", 216.0, 228.0, "stat", box=[0.625, 0.60, 0.315, 0.20], motion="count",
       accent="lime", value=39375, label="KM · ERROR vs MODERN", suffix=" km",
       sub="modern 40,008 km · −1.6%", fmt="comma",
       note="The source already animates '39,375 km' on the left — the overlay owns the "
            "empty right side and reframes it as an error figure instead of repeating it."),
    ev("e019", 228.5, 234.0, "corner", box=[0.055, 0.775, 0.33, 0.12], motion="slide_up",
       accent="amber", kicker="INTERLUDE 01 · OUT",
       title="ratio 1/50 → 250,000 stadia"),

    # ---------------- CH 04 · HARNESS ----------------------------------------
    ev("e020", 240.0, 258.0, "ticker", box=[0.0, 0.035, 1.0, 0.05], motion="wipe",
       accent="cyan", title="SANDBOX  ·  rust-playground  ·  exit code 0  ·  42 ms"),
    ev("e021", 280.0, 300.0, "bracket", box=[0.25, 0.18, 0.55, 0.62], motion="draw",
       accent="cyan", anchor=[0.62, 0.50], title="TEXT → MESH",
       sub="4,182 tris · PBR · auto-rig",
       note="Tripo 3D viewport: frame the model, keep the tool chrome visible."),

    # ---------------- CH 05 · GAME DEV ---------------------------------------
    ev("e022", 300.0, 320.0, "bracket", box=[0.42, 0.16, 0.50, 0.62], motion="draw",
       accent="amber", anchor=[0.66, 0.48], title="SCENE ASSEMBLY"),
    ev("e023", 340.0, 360.0, "progress", box=[0.055, 0.80, 0.34, 0.10], motion="slide_up",
       accent="lime", title="ASSETS", value=3, total=6, label="3 / 6 generated"),
    ev("e024", 380.0, 400.0, "lower_third", box=[0.055, 0.74, 0.46, 0.14], motion="slide_up",
       accent="lime", kicker="PROMPT → PLAYABLE", title="Forbidden City, playable",
       sub="engine build · 60 fps target"),
    ev("e025", 420.0, 440.0, "ticker", box=[0.0, 0.035, 1.0, 0.05], motion="wipe",
       accent="electric", title="GAME BRIEF  ·  third-person · stamina bar · shadow map 4k"),

    # ---------------- CH 06 · AUDIO ------------------------------------------
    ev("e026", 440.0, 464.0, "waveform", box=[0.055, 0.78, 0.89, 0.12], motion="slide_up",
       accent="magenta", title="EDM · 128 BPM", sub="prompt → stems → mix",
       note="Prompt beat: show the hypothetical groove before the DAW appears."),
    ev("e027", 480.0, 678.0, "waveform", box=[0.045, 0.875, 0.91, 0.085], motion="wipe",
       accent="magenta", title="STEMS · 12 TRACKS", sub="128 BPM · A minor",
       long=True, note="16 min of DAW screen — a live waveform rail keeps it from feeling static."),
    ev("e028", 480.0, 560.0, "stat", box=[0.70, 0.075, 0.25, 0.13], motion="pop",
       accent="amber", value=128, label="BPM", suffix="", fmt="comma"),
    ev("e029", 560.0, 620.0, "bars", box=[0.665, 0.07, 0.30, 0.17], motion="slide_up",
       accent="lime", title="LOUDNESS", items=[
           dict(label="Integrated", value="−9.8 LUFS", num=0.86),
           dict(label="True peak", value="−0.1 dB", num=0.94),
           dict(label="LRA", value="6.2 LU", num=0.52)]),

    # ---------------- CH 07 · AD SWEEP ---------------------------------------
    ev("e030", 680.0, 700.0, "ad_break", box=[0.055, 0.10, 0.30, 0.16], motion="pop",
       accent="magenta", title="AD SWEEP", sub="09 CONCEPTS · ONE PROMPT",
       note="Montage begins: a broadcast-style stinger brands the block."),
    ev("e031", 700.0, 742.0, "progress", box=[0.055, 0.86, 0.34, 0.09], motion="slide_up",
       accent="magenta", title="CONCEPT", value=9, total=9, label="09 / 09 rendered"),
    ev("e032", 720.0, 756.0, "bracket", box=[0.10, 0.12, 0.34, 0.30], motion="draw",
       accent="cyan", anchor=[0.26, 0.26], title="START FRAME"),
    ev("e033", 756.0, 762.0, "ad_break", box=[0.30, 0.06, 0.40, 0.14], motion="pop",
       accent="magenta", title="30 SEC", sub="cut to duration"),

    # ---------------- CH 08 · INTERIORS --------------------------------------
    ev("e034", 765.0, 800.0, "progress", box=[0.055, 0.86, 0.34, 0.09], motion="slide_up",
       accent="cyan", title="PROPERTY TOUR", value=4, total=6, label="room 04 / 06"),
    ev("e035", 800.0, 820.0, "callout", box=[0.66, 0.70, 0.30, 0.18], motion="slide_up",
       accent="lime", kicker="PLAN MATCH", title="Living room",
       sub="243 m² · 3 bed · sea view"),

    # ---------------- CH 09 · VISION & RESEARCH ------------------------------
    ev("e036", 900.0, 925.0, "bracket", box=[0.20, 0.22, 0.42, 0.50], motion="draw",
       accent="lime", anchor=[0.41, 0.47], title="VISION · 12 OBJECTS",
       note="Photo-analysis beat: brackets + confidence chips."),
    ev("e037", 905.0, 925.0, "bars", box=[0.63, 0.22, 0.31, 0.26], motion="slide_up",
       accent="lime", title="CONFIDENCE", items=[
           dict(label="wing", value="0.97", num=0.97), dict(label="abdomen", value="0.94", num=0.94),
           dict(label="thorax", value="0.88", num=0.88), dict(label="legs", value="0.71", num=0.71)]),
    ev("e038", 950.0, 995.0, "leaderboard", box=[0.055, 0.16, 0.52, 0.50], motion="slide_up",
       accent="cyan", title="DIFFERENTIAL DX", items=[
           dict(label="ILD", value="0.91"), dict(label="Infection", value="0.44"),
           dict(label="Malignancy", value="0.12"), dict(label="Normal", value="0.03")],
       note="Medical Q&A: a compact differential-probability stack."),
    ev("e039", 1020.0, 1075.0, "progress", box=[0.72, 0.06, 0.23, 0.09], motion="slide_up",
       accent="amber", title="PAPER", value=14, total=32, label="p.14 / 32"),
    ev("e040", 1140.0, 1180.0, "callout", box=[0.055, 0.14, 0.34, 0.20], motion="slide_up",
       accent="lime", kicker="SOURCE", title="1,000+ simulations",
       sub="IPCC AR6 · 2 °C pathway"),

    # ---------------- CH 10 · THE MODEL --------------------------------------
    ev("e041", 1220.0, 1245.0, "callout", box=[0.055, 0.10, 0.40, 0.30], motion="slide_up",
       accent="cyan", kicker="ARCHITECTURE", title="40-layer CED",
       items=[dict(label="Encoder", value="20L"), dict(label="Decoder", value="20L"),
              dict(label="Active", value="88 params/token")]),
    ev("e042", 1245.9, 1252.4, "ad_break", box=[0.60, 0.14, 0.34, 0.16], motion="pop",
       accent="magenta", title="PURE GENIUS", sub="interstitial · 6 s",
       note="The source cuts to a meme card here; tag it instead of fighting it."),
    ev("e043", 1253.0, 1300.0, "ticker", box=[0.0, 0.055, 1.0, 0.05], motion="wipe",
       accent="lime",
       title="DELTA vs V4.1   ·   HLE +5.7   ·   TERMINAL-BENCH +11.1   ·   DEEPSWE +3.4   ·   APEX +7.5   ·   BABYVISION +6.7",
       note="The source already holds the full table for 40 s: a delta rail at the top edge "
            "adds the comparison without covering a single cell."),
    ev("e044", 1300.0, 1320.0, "bars", box=[0.045, 0.12, 0.44, 0.52], motion="slide_up",
       accent="lime", title="SCORE BY BENCH", items=[
           dict(label="HLE", value="42.0", num=0.42), dict(label="TB 4.0", value="42.3", num=0.42),
           dict(label="DeepSWE", value="77.6", num=0.78), dict(label="NL2Repo", value="68.2", num=0.68),
           dict(label="Apex", value="72.1", num=0.72), dict(label="BabyVision", value="71.7", num=0.72)]),
    ev("e045", 1320.0, 1345.0, "quadrant", box=[0.045, 0.10, 0.40, 0.40], motion="draw",
       accent="cyan", title="COST × SPEED",
       anchor=[0.72, 0.34], items=[
           dict(label="V4.1-Flash-1017", value="best $/task"),
           dict(label="GPT-5.5-Base", value="4× cost"),
           dict(label="Claude Opus 5", value="9× cost")],
       note="Log-scale scatter appears at 22:00: a quadrant lens adds the missing read."),
    ev("e046", 1345.0, 1370.0, "callout", box=[0.055, 0.72, 0.34, 0.16], motion="slide_up",
       accent="lime", kicker="OPEN SOURCE", title="MIT · weights on HF",
       sub="DeepSeek-V4.1-Flash-1017"),

    # ---------------- CH 11/12 · NUMBERS + INFRA -----------------------------
    ev("e047", 1400.0, 1420.0, "gauge", box=[0.60, 0.12, 0.34, 0.30], motion="pop",
       accent="lime", title="GPU SPEED", value=100, label="% of peak", unit="",
       anchor=[0.50, 0.50],
       note="The source's own gauge at 23:20 — re-draw it as a HUD so the needle sweep reads."),
    ev("e048", 1419.0, 1440.0, "stat", box=[0.055, 0.20, 0.40, 0.26], motion="count",
       accent="cyan", value=155, label="TRILLION TOKENS / DAY", suffix="T", fmt="comma",
       sub="single cluster · internet-scale"),
    ev("e049", 1440.0, 1459.0, "bars", box=[0.055, 0.62, 0.46, 0.20], motion="slide_up",
       accent="amber", title="$30 REVENUE / GPU HOUR", items=[
           dict(label="Compute costs", value="20%", num=0.20),
           dict(label="Profit", value="80%", num=0.80)]),
    ev("e050", 1460.0, 1480.0, "donut", box=[0.055, 0.16, 0.30, 0.34], motion="pop",
       accent="lime", value=96, label="INPUT CACHE HIT RATE", suffix="%",
       note="Donut sweep synced to the 98→96% on-screen counter."),
    ev("e051", 1480.0, 1500.0, "ticker", box=[0.0, 0.90, 1.0, 0.05], motion="wipe",
       accent="electric",
       title="PRICING  ·  FREE $0  ·  PLUS $20  ·  PRO $200  ·  1M-TOKEN CONTEXT ON ALL TIERS",
       note="The pricing cards are already on screen — reinforce as a rail, not a panel."),

    # ---------------- CH 13/14 · OPEN SOURCE + OUTRO -------------------------
    ev("e052", 1500.0, 1522.0, "ticker", box=[0.0, 0.035, 1.0, 0.05], motion="wipe",
       accent="lime", title="OPEN SOURCE  ·  MIT LICENSE  ·  deepseek-ai/DeepSeek-V4.1-Flash-1017"),
    ev("e053", 1520.0, 1560.0, "callout", box=[0.055, 0.72, 0.34, 0.18], motion="slide_up",
       accent="cyan", kicker="SERVING STACK", title="DeepInfer + DeepGEMM",
       sub="SGLang router · 155T tokens/day"),
    ev("e054", 1560.0, 1584.0, "bracket", box=[0.48, 0.24, 0.44, 0.46], motion="draw",
       accent="amber", anchor=[0.70, 0.46], title="HARDWARE · N100"),
    ev("e055", 1603.0, 1621.0, "corner", box=[0.055, 0.20, 0.30, 0.12], motion="slide_up",
       accent="magenta", kicker="OUTRO · BUILD 1017",
       title="full walkthrough in the description",
       note="Source burns its own SUBSCRIBE card at 26:52 — stay off it."),
    ev("e056", 1621.0, 1641.0, "end_card", box=[0.055, 0.62, 0.36, 0.20], motion="pop",
       accent="electric", title="AI SEARCH", sub="weekly digest · every Thursday"),
]


# ------------------------------------------------------------------- audio cues
AUDIO_CUES = [
    dict(t=0.4, type="impact", note="cold open hit"),
    dict(t=8.6, type="riser", note="tree bloom reveal"),
    dict(t=20.4, type="whoosh", note="cut to blog page"),
    dict(t=167.6, type="swell", note="interlude in"),
    dict(t=228.5, type="resolve", note="interlude out"),
    dict(t=491.3, type="silence", note="measured 0.96 s gap — hold all motion"),
    dict(t=656.3, type="silence", note="measured 1.14 s gap — hold all motion"),
    dict(t=1245.9, type="stinger", note="meme ad card"),
    dict(t=1603.0, type="impact", note="outro"),
]


# --------------------------------------------------------------- measurements
def load_metrics() -> dict:
    p = ROOT / "analysis" / "metrics.json"
    return json.loads(p.read_text()) if p.exists() else {}


def waveform(path: Path) -> dict:
    """10 Hz peak + RMS envelope, normalised 0..1 (what the web canvas draws)."""
    if not path.exists():
        return {}
    with wave.open(str(path), "rb") as w:
        sr, n = w.getframerate(), w.getnframes()
        data = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
    step = sr // 10
    m = len(data) // step
    blocks = data[: m * step].reshape(m, step)
    peak = np.abs(blocks).max(axis=1)
    rms = np.sqrt((blocks ** 2).mean(axis=1))
    peak = peak / (peak.max() or 1)
    rms = rms / (rms.max() or 1)
    return dict(
        hz=10,
        duration_s=round(m / 10, 2),
        peak=[round(float(x), 3) for x in peak],
        rms=[round(float(x), 3) for x in rms],
        # pre-computed 1 s summary for the timeline rail
        per_second=[round(float(x), 2) for x in
                    np.abs(data[: (len(data) // sr) * sr].reshape(-1, sr)).max(axis=1)],
    )


def annotate(events, metrics) -> None:
    secs = {s["t"]: s for s in metrics.get("seconds", [])}
    for e in events:
        chunk = [secs[t] for t in range(int(e["t0"]), int(e["t1"]) + 1) if t in secs]
        if not chunk:
            continue
        avg = lambda k: round(sum(c[k] for c in chunk) / len(chunk), 3)
        hh = np.zeros(12)
        for c in chunk:
            hh += np.array(c["hue_hist"])
        e["measured"] = dict(
            motion=avg("motion"),
            lum=avg("lum_mean"),
            sat=avg("sat_mean"),
            black=avg("black_ratio"),
            audio_db=avg("audio_db") if chunk[0].get("audio_db") is not None else None,
            dominant_hue_deg=int(np.argmax(hh)) * 30,
            dur=round(e["t1"] - e["t0"], 2),
            # contrast guidance the designer can act on
            recommended_ink="light" if avg("lum_mean") < 128 else "dark",
        )


def main() -> None:
    metrics = load_metrics()
    annotate(EVENTS, metrics)

    wf = waveform(ROOT / "analysis" / "audio.wav")
    if wf:
        (OUT / "waveform.json").write_text(json.dumps(wf))
        print(f"waveform: {len(wf['peak'])} samples @ {wf['hz']} Hz")

    timeline = dict(
        version=1,
        brand=BRAND,
        duration_s=metrics.get("duration_s", 1641),
        duration_hms=metrics.get("duration_hms", "27:21"),
        source_stats=dict(
            resolution="1280x720", fps=30, cuts=len(metrics.get("cuts", [])),
            blocks=metrics.get("blocks", []),
        ),
        chapters=CHAPTERS,
        events=EVENTS,
        audio_cues=AUDIO_CUES,
    )
    (OUT / "timeline.json").write_text(json.dumps(timeline, indent=1))

    # keep the web client's copy in lockstep — the player must never drift
    web = ROOT / "web" / "src" / "data"
    if web.exists():
        (web / "timeline.json").write_text(json.dumps(timeline, separators=(",", ":")))
        if wf:
            (web / "waveform.json").write_text(json.dumps(
                dict(hz=wf["hz"], duration_s=wf["duration_s"],
                     peak=[round(x, 2) for x in wf["peak"][::2]],
                     rms=[round(x, 2) for x in wf["rms"][::2]]),
                separators=(",", ":")))
        print(f"synced web/src/data from timeline ({len(EVENTS)} events)")
    print(f"timeline: {len(EVENTS)} events, {len(CHAPTERS)} chapters → graphics/timeline.json")

    # coverage report: how much of the runtime carries a graphic
    covered = set()
    for e in EVENTS:
        covered.update(range(int(e["t0"]), int(e["t1"]) + 1))
    d = timeline["duration_s"]
    print(f"coverage: {len(covered)}/{d} s = {len(covered)/d*100:.1f}% of runtime")
    by_kind = {}
    for e in EVENTS:
        by_kind[e["kind"]] = by_kind.get(e["kind"], 0) + 1
    print("kinds:", dict(sorted(by_kind.items(), key=lambda kv: -kv[1])))


if __name__ == "__main__":
    main()
