import { useEffect, useRef, useState } from 'react'
import type { Timeline, TimelineEvent } from '../lib/types'

/**
 * Telemetry — live measured statistics for the current playhead position:
 * frame motion, plate luminance, audio level and the beat count in view.
 * Values come straight from analysis/metrics.json (via timeline.measured).
 */
export function Telemetry({
  timeline, active, clock, chapter,
}: {
  timeline: Timeline
  active: TimelineEvent[]
  clock: React.MutableRefObject<number>
  chapter: { title: string; sub: string; t0: number; t1: number }
}) {
  const [read, setRead] = useState({ motion: 0, lum: 0, audio: -60, hue: 0 })
  const last = useRef(0)

  useEffect(() => {
    let raf = 0
    const loop = () => {
      const now = performance.now()
      if (now - last.current > 250) {
        last.current = now
        // nearest annotated beat gives us measured plate stats for this moment
        const t = clock.current
        let best: TimelineEvent | undefined
        for (const e of timeline.events) {
          if (t >= e.t0 && t <= e.t1) { best = e; break }
        }
        const m = best?.measured
        setRead({
          motion: m?.motion ?? 0,
          lum: m?.lum ?? 0,
          audio: m?.audio_db ?? -60,
          hue: m?.dominant_hue_deg ?? 0,
        })
      }
      raf = requestAnimationFrame(loop)
    }
    raf = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(raf)
  }, [clock, timeline.events])

  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
      <Cell label="chapter" value={chapter.title} sub={chapter.sub} accent="text-cyan" />
      <Cell label="plate motion" value={read.motion.toFixed(1)} sub="mean abs Δ / frame" accent="text-lime" bar={Math.min(1, read.motion / 40)} />
      <Cell label="plate luminance" value={read.lum.toFixed(0)} sub="/ 255" accent="text-amber" bar={read.lum / 255} />
      <Cell label="audio" value={`${read.audio.toFixed(0)} dB`} sub={`${active.length} graphic${active.length === 1 ? '' : 's'} live`} accent="text-magenta" bar={Math.min(1, (read.audio + 60) / 45)} />
    </div>
  )
}

function Cell({ label, value, sub, accent, bar }: { label: string; value: string; sub?: string; accent: string; bar?: number }) {
  return (
    <div className="relative overflow-hidden rounded-lg border border-line/70 bg-panel/60 px-2.5 py-2">
      <div className="font-mono text-[8.5px] uppercase tracking-[0.18em] text-muted">{label}</div>
      <div className={`mt-0.5 truncate font-display text-sm font-bold ${accent}`}>{value}</div>
      {sub && <div className="truncate font-mono text-[8.5px] text-muted/80">{sub}</div>}
      {bar !== undefined && (
        <div className="mt-1 h-[2px] w-full overflow-hidden rounded-full bg-white/10">
          <div className="h-full rounded-full bg-current transition-[width] duration-200" style={{ width: `${Math.max(2, bar * 100)}%` }} />
        </div>
      )}
    </div>
  )
}
