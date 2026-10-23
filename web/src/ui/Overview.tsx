import gsap from 'gsap'
import { useEffect, useRef } from 'react'
import type { Timeline, Waveform } from '../lib/types'

/**
 * Overview — the full 27-minute map drawn on a Canvas: audio envelope,
 * chapter bands, and one tick per graphics event. The GSAP tween drives the
 * playhead so it glides between rAF samples instead of snapping.
 */
export function Overview({
  timeline, wave, clock, onSeek,
}: {
  timeline: Timeline
  wave: Waveform
  clock: React.MutableRefObject<number>
  onSeek: (t: number) => void
}) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const head = useRef<HTMLDivElement>(null)
  const wrap = useRef<HTMLDivElement>(null)
  const dur = timeline.duration_s

  useEffect(() => {
    const c = canvas.current
    if (!c) return
    const draw = () => {
      const r = c.getBoundingClientRect()
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      c.width = Math.floor(r.width * dpr)
      c.height = Math.floor(r.height * dpr)
      const ctx = c.getContext('2d')!
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      const w = r.width
      const h = r.height
      ctx.clearRect(0, 0, w, h)

      // chapter bands
      timeline.chapters.forEach((ch, i) => {
        const x0 = (ch.t0 / dur) * w
        const x1 = (ch.t1 / dur) * w
        ctx.fillStyle = i % 2 ? 'rgba(255,255,255,.025)' : 'rgba(255,255,255,.055)'
        ctx.fillRect(x0, 0, x1 - x0, h)
        ctx.strokeStyle = 'rgba(34,48,75,.9)'
        ctx.beginPath(); ctx.moveTo(x0, 0); ctx.lineTo(x0, h); ctx.stroke()
      })

      // audio envelope
      const mid = h * 0.52
      const bars = Math.floor(w / 2)
      ctx.fillStyle = 'rgba(47,233,255,.42)'
      for (let i = 0; i < bars; i++) {
        const t = (i / bars) * dur
        const v = wave.peak[Math.min(wave.peak.length - 1, Math.floor(t * wave.hz))] ?? 0
        const bh = (h * 0.34) * v
        ctx.fillRect(i * 2, mid - bh, 1.2, bh * 2)
      }

      // event ticks
      timeline.events.forEach((ev) => {
        const x = (ev.t0 / dur) * w
        const accent = (({
          cyan: '#2FE9FF', electric: '#4D6BFE', lime: '#B6FF3C',
          amber: '#FFB020', magenta: '#FF2D6F', paper: '#F2F6FF', muted: '#8FA2C4',
        }) as Record<string, string>)[ev.accent] ?? '#2FE9FF'
        ctx.fillStyle = accent
        ctx.globalAlpha = 0.85
        ctx.fillRect(x, h - 7, Math.max(1.5, ((ev.t1 - ev.t0) / dur) * w), 3)
        ctx.globalAlpha = 1
      })
    }
    draw()
    const ro = new ResizeObserver(draw)
    if (wrap.current) ro.observe(wrap.current)
    return () => ro.disconnect()
  }, [timeline, wave, dur])

  useEffect(() => {
    const el = head.current
    if (!el) return
    const obj = { x: 0 }
    const tween = gsap.to(obj, {
      x: dur, duration: dur, ease: 'none', paused: true,
      onUpdate: () => {
        if (head.current) head.current.style.transform = `translate3d(${(obj.x / dur) * 100}%,0,0)`
      },
    })
    let raf = 0
    const loop = () => {
      // keep the GSAP head in lockstep with the video clock
      tween.progress(Math.min(1, Math.max(0, clock.current / dur)))
      raf = requestAnimationFrame(loop)
    }
    raf = requestAnimationFrame(loop)
    return () => { cancelAnimationFrame(raf); tween.kill() }
  }, [clock, dur])

  const seekFromEvent = (e: React.MouseEvent<HTMLDivElement>) => {
    const r = e.currentTarget.getBoundingClientRect()
    onSeek(((e.clientX - r.left) / r.width) * dur)
  }

  return (
    <div ref={wrap} className="relative h-16 w-full cursor-crosshair overflow-hidden rounded-lg border border-line/70 bg-ink/60"
         onClick={seekFromEvent}>
      <canvas ref={canvas} className="block h-full w-full" />
      <div className="pointer-events-none absolute inset-0">
        {timeline.chapters.map((ch) => (
          <span key={ch.id}
                className="absolute top-1 truncate font-mono text-[8.5px] uppercase tracking-wider text-muted/80"
                style={{ left: `${(ch.t0 / dur) * 100}%`, maxWidth: `${((ch.t1 - ch.t0) / dur) * 100}%` }}>
            {ch.title}
          </span>
        ))}
        <div ref={head} className="absolute inset-y-0 left-0 w-px bg-amber will-change-transform">
          <span className="absolute -left-[3px] top-0 h-2 w-[7px] rounded-sm bg-amber" />
        </div>
      </div>
    </div>
  )
}
