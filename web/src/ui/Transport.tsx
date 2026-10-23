import { useEffect, useRef } from 'react'
import { mmss } from '../lib/useFrame'
import type { VideoClock } from '../lib/useVideoClock'

const RATES = [0.5, 1, 1.5, 2]

export function Transport({
  clock, overlayOn, setOverlayOn, offset, setOffset,
}: {
  clock: VideoClock
  overlayOn: boolean
  setOverlayOn: (v: boolean) => void
  offset: number
  setOffset: (v: number) => void
}) {
  const { time, duration, playing, rate, buffered } = clock
  const pct = duration ? (time / duration) * 100 : 0

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA') return
      if (e.code === 'Space') { e.preventDefault(); clock.toggle() }
      if (e.code === 'ArrowRight') clock.seek(clock.t.current + (e.shiftKey ? 30 : 5))
      if (e.code === 'ArrowLeft') clock.seek(clock.t.current - (e.shiftKey ? 30 : 5))
      if (e.key === 'g') setOverlayOn(!overlayOn)
      if (e.key === 'j') clock.setRate(Math.max(0.25, rate - 0.25))
      if (e.key === 'k') clock.setRate(1)
      if (e.key === 'l') clock.setRate(Math.min(4, rate + 0.25))
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [clock, overlayOn, rate, setOverlayOn])

  return (
    <div className="rounded-xl border border-line/80 bg-panel/70 p-3 backdrop-blur">
      <div className="flex items-center gap-3">
        <button
          onClick={clock.toggle}
          aria-label={playing ? 'Pause' : 'Play'}
          className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-cyan text-void shadow-glow transition hover:scale-105 active:scale-95"
        >
          {playing ? (
            <svg viewBox="0 0 24 24" className="h-4 w-4" fill="currentColor"><path d="M7 5h4v14H7zM13 5h4v14h-4z" /></svg>
          ) : (
            <svg viewBox="0 0 24 24" className="h-4 w-4 translate-x-[1px]" fill="currentColor"><path d="M8 5v14l11-7z" /></svg>
          )}
        </button>

        <div className="font-mono text-xs tabnum text-paper/80">
          <span className="text-cyan">{mmss(time)}</span>
          <span className="text-muted"> / {mmss(duration)}</span>
        </div>

        {/* scrub bar with buffered + event-density underlay */}
        <div className="relative h-6 flex-1">
          <input
            type="range" min={0} max={Math.max(duration, 0.1)} step={0.02} value={time}
            onChange={(e) => clock.scrubTo(parseFloat(e.target.value))}
            aria-label="Seek"
            className="absolute inset-0 z-10 w-full cursor-pointer"
          />
          <div className="pointer-events-none absolute left-0 right-0 top-[11px] h-[2px] rounded-full bg-white/10">
            <div className="h-full rounded-full bg-white/20" style={{ width: `${buffered * 100}%` }} />
            <div className="absolute inset-y-0 left-0 rounded-full bg-cyan/80" style={{ width: `${pct}%` }} />
          </div>
        </div>

        <div className="flex items-center gap-1 rounded-lg border border-line/70 p-0.5">
          {RATES.map((r) => (
            <button
              key={r}
              onClick={() => clock.setRate(r)}
              className={`rounded px-2 py-1 font-mono text-[10px] transition ${
                rate === r ? 'bg-cyan/20 text-cyan' : 'text-muted hover:text-paper'
              }`}
            >
              {r}×
            </button>
          ))}
        </div>

        <button
          onClick={() => setOverlayOn(!overlayOn)}
          className={`rounded-lg border px-2.5 py-1.5 font-mono text-[10px] font-bold uppercase tracking-widest transition ${
            overlayOn ? 'border-lime/60 bg-lime/15 text-lime' : 'border-line text-muted hover:text-paper'
          }`}
          title="Toggle motion graphics (G)"
        >
          {overlayOn ? 'GFX on' : 'GFX off'}
        </button>
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-[10px] text-muted">
        <span>space play · ←/→ 5s (shift 30s) · J/K/L shuttle · G graphics</span>
        <label className="ml-auto flex items-center gap-2">
          <span className="uppercase tracking-widest">sync offset</span>
          <input
            type="range" min={-300} max={300} step={10} value={offset * 1000}
            onChange={(e) => setOffset(parseFloat(e.target.value) / 1000)}
            className="h-1 w-24 accent-amber"
          />
          <span className="w-14 tabnum text-amber">{(offset * 1000).toFixed(0)} ms</span>
        </label>
      </div>
    </div>
  )
}
