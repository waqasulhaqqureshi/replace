#!/usr/bin/env python3
"""
synth_audio.py — procedural background bed for the new intro/outro.

There is no licensed music in this repository, so the spec's "background audio
sync cues" are generated here: a deliberately minimal 120 BPM electronic bed
whose transients land exactly on the storyboard's scene boundaries.

Layers
  · sub    — 48 Hz sine on every beat, short exponential decay
  · kick   — sine pitch-drop 120→44 Hz, 90 ms
  · hat    — band-passed white noise on the off-beats
  · pad    — detuned saw stack (A minor 9) through a one-pole low-pass
  · riser  — noise sweep with rising band-pass into the title lockup (t=36 s)
  · impact — reverse-decay noise burst + sub drop on hard cuts

Output: 48 kHz / 16-bit stereo WAV, then AAC via ffmpeg.

Usage: python3 scripts/synth_audio.py --dur 48 --out render/intro_bed.wav
"""
from __future__ import annotations

import argparse
import subprocess
import wave
from pathlib import Path

import numpy as np

SR = 48000
BPM = 120
BEAT = 60.0 / BPM


def env(n: int, a: float, d: float, sustain: float = 0.0) -> np.ndarray:
    """Attack/decay envelope in seconds, sampled at n points."""
    t = np.arange(n) / SR
    e = np.exp(-t / max(d, 1e-4))
    if a > 0:
        e *= np.clip(t / a, 0, 1)
    return (e * (1 - sustain) + sustain) if sustain else e


def sine(freq, n, phase=0.0):
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * freq * t + phase)


def kick(n: int) -> np.ndarray:
    t = np.arange(n) / SR
    f = 120 * np.exp(-t * 26) + 44
    phase = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(phase) * env(n, 0.001, 0.09)


def noise(n: int) -> np.ndarray:
    return np.random.default_rng(7).normal(0, 1, n)


def bandpass(x: np.ndarray, lo: float, hi: float) -> np.ndarray:
    """Cheap FFT band-pass — good enough for percussion."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    mask = ((f > lo) & (f < hi)).astype(float)
    # soft edges
    lo_e = np.clip((f - lo) / max(lo * 0.3, 1), 0, 1)
    hi_e = np.clip((hi - f) / max(hi * 0.3, 1), 0, 1)
    return np.fft.irfft(X * np.clip(mask * lo_e * hi_e, 0, 1), len(x))


def lowpass(x: np.ndarray, cutoff: float, res: float = 0.9) -> np.ndarray:
    """One-pole resonant-ish low-pass with a slowly opening cutoff."""
    a = np.clip(2 * np.pi * cutoff / SR, 1e-5, 1)
    y = np.zeros_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += a * (x[i] - acc)
        y[i] = acc
    return y * (1 + res)


def saw_stack(freqs, n, detune=0.12, voices=5):
    out = np.zeros(n)
    for f in freqs:
        for v in range(voices):
            d = 1 + (v - voices // 2) * detune / 100
            ph = np.arange(n) / SR * f * d
            out += 2 * ((ph % 1.0) - 0.5)
    return out / (len(freqs) * voices)


def build(dur: float, cue_list: tuple[float, ...]) -> np.ndarray:
    n = int(dur * SR)
    mix = np.zeros((n, 2))

    def add(sig: np.ndarray, at: float, gain: float, pan: float = 0.0):
        i = int(at * SR)
        if i >= n:
            return
        seg = sig[: n - i] * gain
        # equal-power pan
        l = np.cos((pan + 1) * np.pi / 4)
        r = np.sin((pan + 1) * np.pi / 4)
        mix[i:i + len(seg), 0] += seg * l
        mix[i:i + len(seg), 1] += seg * r

    # ---- rhythm grid ------------------------------------------------------
    beats = int(dur / BEAT) + 1
    for b in range(beats):
        t = b * BEAT
        add(kick(int(0.35 * SR)), t, 0.55 if b % 4 == 0 else 0.38)
        add(sine(48, int(0.5 * SR)) * env(int(0.5 * SR), 0.002, 0.18), t, 0.30)
        if b % 2 == 1:  # off-beat hat
            h = bandpass(noise(int(0.06 * SR)), 6000, 13000)
            add(h * env(len(h), 0.0005, 0.02), t, 0.10, pan=0.25)
        if b % 4 == 2:  # open hat
            h = bandpass(noise(int(0.22 * SR)), 5000, 12000)
            add(h * env(len(h), 0.001, 0.07), t, 0.075, pan=-0.2)

    # ---- pad (A minor 9: A2 C3 E3 B3) -------------------------------------
    pad = saw_stack([110.0, 130.81, 164.81, 246.94], n)
    pad = lowpass(pad, 380, 0.4)
    # slow swell + tremolo
    t = np.arange(n) / SR
    swell = np.clip(t / 6, 0, 1) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.09 * t))
    pad *= swell * 0.22
    mix[:, 0] += pad * 1.05
    mix[:, 1] += np.roll(pad, 4800) * 0.95  # haas widening

    # ---- riser into the title lockup -------------------------------------
    rise_start, rise_end = 30.0, 36.0
    rn = int((rise_end - rise_start) * SR)
    r = bandpass(noise(rn), 400, 9000)
    r *= np.linspace(0, 1, rn) ** 2.2
    add(r, rise_start, 0.16)
    add(sine(220, rn) * np.linspace(0, 1, rn) ** 3 * 0.5, rise_start, 0.12)

    # ---- cues (scene boundaries from the storyboard) ----------------------
    for i, c in enumerate(cue_list):
        ln = int(0.9 * SR)
        burst = bandpass(noise(ln), 120, 7000) * np.exp(-np.arange(ln) / SR / 0.28)
        add(burst, c, 0.30, pan=0.15 if i % 2 else -0.15)
        # sub drop under each hit
        drop = sine(62, int(0.7 * SR)) * np.exp(-np.arange(int(0.7 * SR)) / SR / 0.22) * 0.35
        add(drop, c, 0.5)

    # ---- master ----------------------------------------------------------
    mix = np.tanh(mix * 0.9) * 0.92
    fade = int(1.2 * SR)
    mix[:fade] *= np.linspace(0, 1, fade)[:, None]
    mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
    peak = np.abs(mix).max() or 1.0
    return mix / peak * 0.89


def write_wav(path: Path, data: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.clip(data, -1, 1)
    pcm = (pcm * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dur", type=float, default=48.0)
    ap.add_argument("--out", default="render/intro_bed.wav")
    args = ap.parse_args()

    # hard cuts from the storyboard (see docs/NEW_VIDEO_SPEC.md)
    cues = (0.35, 4.2, 10.5, 18.0, 24.0, 30.0, 36.0, 43.5)
    data = build(args.dur, cues)
    out = Path(__file__).resolve().parent.parent / args.out
    write_wav(out, data)
    print(f"[audio] {out}  {args.dur:g}s  {out.stat().st_size/1e6:.1f} MB")

    aac = out.with_suffix(".m4a")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(out),
                    "-c:a", "aac", "-b:a", "192k", str(aac)], check=False)
    if aac.exists():
        print(f"[audio] {aac}  {aac.stat().st_size/1e6:.1f} MB")


if __name__ == "__main__":
    main()
