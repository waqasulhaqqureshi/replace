import { motion } from 'framer-motion'
import { useEffect, useRef } from 'react'
import { ease, useFrame } from '../../lib/useFrame'
import type { TimelineEvent, Waveform } from '../../lib/types'
import { ACCENT_HEX, Beat, Kicker } from './shared'

/** ticker — infinite marquee whose scroll is tied to the playhead, not CSS time,
 *  so it stays frame-locked when you scrub, pause or slow the video down. */
export function Ticker({ ev, clock }: { ev: TimelineEvent; clock: React.MutableRefObject<number> }) {
  const track = useRef<HTMLDivElement>(null)
  useFrame(clock, (t) => {
    if (!track.current) return
    const span = track.current.scrollWidth / 2 || 1
    const x = -(((t - ev.t0) * 46) % span)
    track.current.style.transform = `translate3d(${x}px,0,0)`
  }, [ev.id])
  const text = ev.title ?? ''
  return (
    <Beat ev={ev} animate={ev.motion === 'wipe'}>
      <div className="relative overflow-hidden border-y bg-[#080c16]/90 py-1.5"
           style={{ borderColor: `${ACCENT_HEX[ev.accent]}55` }}>
        <div ref={track} className="flex w-max whitespace-nowrap will-change-transform">
          {[0, 1].map((k) => (
            <div key={k} className="flex">
              {[0, 1, 2].map((j) => (
                <span key={j} className="flex items-center font-mono text-[11px] font-bold tracking-[0.12em] text-paper/90">
                  <span className="px-4">{text}</span>
                  <span style={{ color: ACCENT_HEX[ev.accent] }}>•</span>
                </span>
              ))}
            </div>
          ))}
        </div>
      </div>
    </Beat>
  )
}

/** ring — highlight ring that tracks a focal point on the plate */
export function Ring({ ev, clock }: { ev: TimelineEvent; clock: React.MutableRefObject<number> }) {
  const g = useRef<SVGGElement>(null)
  const [ax, ay] = ev.anchor ?? [0.5, 0.5]
  useFrame(clock, (t) => {
    if (!g.current) return
    const pin = ease.out(ease.clamp01((t - ev.t0) / 0.6))
    const rot = (t * 26) % 360
    g.current.style.transform = `rotate(${rot}deg)`
    g.current.style.transformOrigin = `${ax * 1280}px ${ay * 720}px`
    g.current.style.opacity = String(pin)
    const outer = g.current.querySelector<SVGCircleElement>('circle.outer')
    if (outer) outer.style.transform = `scale(${0.92 + 0.05 * Math.sin(t * 2.2)})`
  }, [ev.id])
  const R = 54
  return (
    <svg className="pointer-events-none absolute inset-0 h-full w-full" viewBox="0 0 1280 720" preserveAspectRatio="none">
      <circle cx={ax * 1280} cy={ay * 720} r={R} fill="none" stroke={ACCENT_HEX[ev.accent]} strokeWidth={2}
              strokeDasharray={`${2 * Math.PI * R * 0.65} ${2 * Math.PI * R}`} />
      <circle className="outer" cx={ax * 1280} cy={ay * 720} r={R * 1.24} fill="none"
              stroke={ACCENT_HEX[ev.accent]} strokeOpacity={0.35} strokeWidth={1} strokeDasharray="3 7" />
      <g ref={g}>
        {[0, 90, 180, 270].map((a) => (
          <line key={a}
                x1={ax * 1280 + Math.cos((a * Math.PI) / 180) * R * 0.62}
                y1={ay * 720 + Math.sin((a * Math.PI) / 180) * R * 0.62}
                x2={ax * 1280 + Math.cos((a * Math.PI) / 180) * R * 0.9}
                y2={ay * 720 + Math.sin((a * Math.PI) / 180) * R * 0.9}
                stroke={ACCENT_HEX[ev.accent]} strokeOpacity={0.7} strokeWidth={1.2} />
        ))}
      </g>
      <g>
        <rect x={ax * 1280 - 62} y={ay * 720 + R * 1.5} width={124} height={20} fill="rgba(8,12,22,.86)" />
        <text x={ax * 1280} y={ay * 720 + R * 1.5 + 13} textAnchor="middle" fontSize={10.5}
              fontWeight={700} fill={ACCENT_HEX[ev.accent]} fontFamily="monospace" letterSpacing={1.2}>
          {(ev.title ?? '').toUpperCase()}
        </text>
      </g>
    </svg>
  )
}

/** waveform — Canvas API, 60fps, device-pixel-ratio aware, driven by the playhead */
export function Waveform({
  ev, clock, wave,
}: { ev: TimelineEvent; clock: React.MutableRefObject<number>; wave: Waveform }) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const size = useRef({ w: 0, h: 0, dpr: 1 })

  useEffect(() => {
    const c = canvas.current
    if (!c) return
    const ro = new ResizeObserver(() => {
      const r = c.getBoundingClientRect()
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      size.current = { w: r.width, h: r.height, dpr }
      c.width = Math.max(1, Math.floor(r.width * dpr))
      c.height = Math.max(1, Math.floor(r.height * dpr))
    })
    ro.observe(c)
    return () => ro.disconnect()
  }, [])

  useFrame(clock, (t) => {
    const c = canvas.current
    if (!c) return
    const { w, h, dpr } = size.current
    if (!w || !h) return
    const ctx = c.getContext('2d')
    if (!ctx) return
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, w, h)

    const accent = ACCENT_HEX[ev.accent]
    const span = ev.t1 - ev.t0
    const bars = Math.max(24, Math.floor(w / 5))
    const mid = h * 0.62
    const amp = (h - 22) / 2
    const playhead = ease.clamp01((t - ev.t0) / span)

    for (let i = 0; i < bars; i++) {
      const q = i / (bars - 1)
      const src = Math.floor((q * span + ev.t0) * wave.hz)
      const v = 0.12 + 0.88 * (wave.peak[Math.min(src, wave.peak.length - 1)] ?? 0.2)
      const bh = amp * v
      const x = i * (w / bars)
      const played = q <= playhead
      ctx.fillStyle = played ? accent : 'rgba(255,255,255,.22)'
      ctx.fillRect(x, mid - bh, Math.max(1.6, w / bars * 0.55), bh * 2)
    }
    // playhead
    ctx.fillStyle = '#FFB020'
    ctx.fillRect(playhead * w - 1, 2, 2, h - 4)
  }, [ev.id])

  return (
    <Beat ev={ev} animate={ev.motion !== 'wipe'}>
      <div className="relative overflow-hidden rounded-lg border bg-[#080c16]/90"
           style={{ borderColor: `${ACCENT_HEX[ev.accent]}44` }}>
        <div className="flex items-center justify-between px-2 pt-1">
          <Kicker accent={ev.accent}>{ev.title}</Kicker>
          <span className="font-mono text-[9px] text-muted">{ev.sub}</span>
        </div>
        <canvas ref={canvas} className="block h-10 w-full" />
      </div>
    </Beat>
  )
}

/** ad_break — broadcast stinger */
export function AdBreak({ ev }: { ev: TimelineEvent }) {
  return (
    <Beat ev={ev}>
      <div className="relative overflow-hidden"
           style={{ background: 'linear-gradient(90deg, rgba(10,6,14,.96), rgba(24,8,18,.96))',
                    clipPath: 'polygon(10px 0, 100% 0, calc(100% - 10px) 100%, 0 100%)',
                    borderTop: `2px solid ${ACCENT_HEX[ev.accent]}`,
                    borderBottom: `2px solid ${ACCENT_HEX[ev.accent]}` }}>
        <div className="flex items-center justify-between px-3 pt-1 font-mono text-[9px]">
          <span style={{ color: ACCENT_HEX[ev.accent] }}>AD BREAK</span>
          <motion.span animate={{ opacity: [1, 0.15, 1] }} transition={{ duration: 1.4, repeat: Infinity }}
                       className="text-magenta">● REC</motion.span>
        </div>
        <div className="px-3 pb-2">
          <div className="font-display text-[22px] font-extrabold leading-tight text-paper">{ev.title}</div>
          {ev.sub && <div className="font-mono text-[10px] text-muted">{ev.sub}</div>}
        </div>
      </div>
    </Beat>
  )
}

/** chapter — kinetic typography with a masked reveal */
export function Chapter({ ev }: { ev: TimelineEvent }) {
  const words = (ev.title ?? '').split(' ')
  return (
    <Beat ev={ev}>
      <Kicker accent={ev.accent}>{ev.kicker}</Kicker>
      <div className={`flex flex-wrap gap-x-3 ${ev.serif ? 'font-serif' : 'font-display'}`}>
        {words.map((w, i) => (
          <span key={i} className="overflow-hidden">
            <motion.span
              className="block text-[42px] font-extrabold leading-[1.05] text-paper"
              initial={{ y: '110%' }}
              animate={{ y: 0 }}
              transition={{ delay: i * 0.07, duration: 0.62, ease: [0.16, 1, 0.3, 1] }}
            >
              {w}
            </motion.span>
          </span>
        ))}
      </div>
      {ev.sub && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}
                    className="mt-2 text-[20px] text-muted">
          {ev.sub}
        </motion.div>
      )}
    </Beat>
  )
}
