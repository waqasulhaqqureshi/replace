import { useEffect, useRef } from 'react'

/**
 * useFrame — run a callback inside a single shared rAF loop.
 * The callback receives the live playhead (seconds) and delta.
 * No React re-render is scheduled: write to refs / DOM directly.
 */
export function useFrame(
  clock: React.MutableRefObject<number>,
  cb: (t: number, dt: number) => void,
  deps: unknown[] = [],
) {
  const fn = useRef(cb)
  fn.current = cb
  useEffect(() => {
    let raf = 0
    let prev = performance.now()
    const loop = (now: number) => {
      const dt = Math.min((now - prev) / 1000, 0.1)
      prev = now
      fn.current(clock.current, dt)
      raf = requestAnimationFrame(loop)
    }
    raf = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(raf)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
}

/** easing shared by React + the Python renderer */
export const ease = {
  out: (p: number) => 1 - Math.pow(1 - Math.min(Math.max(p, 0), 1), 3),
  in: (p: number) => Math.pow(Math.min(Math.max(p, 0), 1), 3),
  inOut: (p: number) => {
    const x = Math.min(Math.max(p, 0), 1)
    return x < 0.5 ? 4 * x ** 3 : 1 - Math.pow(-2 * x + 2, 3) / 2
  },
  outBack: (p: number, s = 1.7) => {
    const x = Math.min(Math.max(p, 0), 1) - 1
    return 1 + x * x * ((s + 1) * x + s)
  },
  clamp01: (p: number) => (p < 0 ? 0 : p > 1 ? 1 : p),
}

/** Decelerating count-up (mirrors overlay_lib.count_at). */
export const countAt = (target: number, p: number) =>
  target * (1 - Math.pow(1 - ease.clamp01(p), 2.2))

export const fmt = (v: number, mode: 'comma' | 'compact' | 'pct' = 'comma', suffix = '') => {
  if (mode === 'compact') return (v >= 1e6 ? `${(v / 1e6).toFixed(0)}M` : `${(v / 1e3).toFixed(0)}K`) + suffix
  if (mode === 'pct') return `${v.toFixed(1)}%`
  return Math.round(v).toLocaleString('en-US') + suffix
}

export const mmss = (s: number) => {
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60)
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}
