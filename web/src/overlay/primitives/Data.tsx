import { motion } from 'framer-motion'
import { useRef } from 'react'
import { ease, useFrame } from '../../lib/useFrame'
import type { TimelineEvent } from '../../lib/types'
import { ACCENT_HEX, Beat, CornerTicks, Glass, Kicker, SvgCounter, useBeat } from './shared'

const svg = (w = 1280, h = 720) => `absolute inset-0 h-full w-full pointer-events-none`

/** leaderboard — ranked score rows with delta chips */
export function Leaderboard({ ev, clock }: { ev: TimelineEvent; clock: React.MutableRefObject<number> }) {
  return (
    <Beat ev={ev}>
      <Glass accent={ev.accent}>
        <Kicker accent={ev.accent}>{ev.title}</Kicker>
        <div className="mb-1 flex justify-between font-mono text-[9px] uppercase tracking-widest text-muted">
          <span># / benchmark</span>
          <span>score</span>
        </div>
        <div className="divide-y divide-white/5">
          {ev.items?.map((it, i) => (
            <motion.div
              key={it.label}
              initial={{ opacity: 0, x: -14 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.08, duration: 0.34, ease: [0.16, 1, 0.3, 1] }}
              className={`flex items-center justify-between gap-2 py-[5px] ${i === 0 ? 'bg-white/[0.04]' : ''}`}
            >
              <span className="flex min-w-0 items-center gap-2">
                <span className="w-4 font-mono text-[9px]" style={{ color: ACCENT_HEX[ev.accent] }}>
                  {String(i + 1).padStart(2, '0')}
                </span>
                <span className="truncate text-[11.5px] text-paper/90">{it.label}</span>
              </span>
              <span className="flex shrink-0 items-center gap-1.5">
                {it.delta && (
                  <span className="rounded-full bg-lime/20 px-1.5 py-[1px] font-mono text-[9px] font-bold text-lime">
                    {it.delta}
                  </span>
                )}
                <span className="w-9 text-right font-mono text-[11px] font-bold" style={{ color: ACCENT_HEX[ev.accent] }}>
                  {it.value}
                </span>
              </span>
            </motion.div>
          ))}
        </div>
      </Glass>
    </Beat>
  )
}

/** bars — horizontal data bars that grow with a stagger */
export function Bars({ ev, clock }: { ev: TimelineEvent; clock: React.MutableRefObject<number> }) {
  return (
    <Beat ev={ev}>
      <Glass accent={ev.accent}>
        <Kicker accent={ev.accent}>{ev.title}</Kicker>
        <div className="space-y-1.5">
          {ev.items?.map((it, i) => (
            <div key={it.label} className="flex items-center gap-2 font-mono text-[10.5px]">
              <span className="w-[84px] shrink-0 truncate text-muted">{it.label}</span>
              <span className="relative h-[7px] flex-1 overflow-hidden rounded-full bg-white/[0.07]">
                <motion.span
                  className="absolute inset-y-0 left-0 rounded-full"
                  style={{ background: ACCENT_HEX[i === 0 ? ev.accent : 'lime'] }}
                  initial={{ scaleX: 0 }}
                  animate={{ scaleX: it.num ?? 0.5 }}
                  transition={{ delay: 0.12 + i * 0.07, duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
                  // transform-only growth keeps this on the compositor
                />
              </span>
              <span className="w-12 shrink-0 text-right text-paper">{it.value}</span>
            </div>
          ))}
        </div>
      </Glass>
    </Beat>
  )
}

/** progress — value rail with live label */
export function Progress({ ev, clock }: { ev: TimelineEvent; clock: React.MutableRefObject<number> }) {
  const fill = useRef<HTMLSpanElement>(null)
  const label = useRef<HTMLSpanElement>(null)
  const goal = ev.total ?? 1
  useFrame(clock, (t) => {
    const p = ease.clamp01((t - ev.t0) / 1.1)
    if (fill.current) fill.current.style.transform = `scaleX(${ease.out(p)})`
    if (label.current) {
      const shown = Math.round(goal * p)
      const txt = ev.label ?? ''
      label.current.textContent = txt.includes('/') ? txt.replace(/\d+/, String(shown)) : txt
    }
  }, [ev.id])
  return (
    <Beat ev={ev}>
      <Glass accent={ev.accent} className="py-1">
        <div className="flex items-center justify-between gap-3">
          <span className="font-mono text-[10px] font-bold uppercase tracking-[0.16em]"
                style={{ color: ACCENT_HEX[ev.accent] }}>
            {ev.title}
          </span>
          <span ref={label} className="font-mono text-[10px] text-paper/90">{ev.label}</span>
        </div>
        <span className="mt-2 block h-[5px] overflow-hidden rounded-full bg-white/10">
          <span ref={fill} className="block h-full origin-left rounded-full"
                style={{ background: ACCENT_HEX[ev.accent] }} />
        </span>
      </Glass>
    </Beat>
  )
}

/** gauge — 240° arc with needle, synced to the count */
export function Gauge({ ev, clock }: { ev: TimelineEvent; clock: React.MutableRefObject<number> }) {
  const arc = useRef<SVGPathElement>(null)
  const needle = useRef<SVGLineElement>(null)
  const val = useRef<SVGTextElement>(null)
  useFrame(clock, (t) => {
    const p = ease.clamp01((t - ev.t0) / 0.9)
    const v = (ev.value ?? 100) * ease.outBack(p, 1.2)
    if (arc.current) arc.current.style.strokeDashoffset = `${100 - 100 * (v / 100)}`
    const a = (150 + (240 * v) / 100) * (Math.PI / 180)
    if (needle.current) {
      needle.current.setAttribute('x2', String(100 + Math.cos(a) * 62))
      needle.current.setAttribute('y2', String(100 + Math.sin(a) * 62))
    }
    if (val.current) val.current.textContent = `${v.toFixed(0)}${ev.suffix ?? '%'}`
  }, [ev.id])
  return (
    <Beat ev={ev}>
      <div className="glass relative rounded-xl p-3">
        <Kicker accent={ev.accent}>{ev.title}</Kicker>
        <svg viewBox="0 0 200 150" className="w-full">
          <path d={arcPath(100, 100, 78, 150, 390)} fill="none" stroke="rgba(255,255,255,.1)" strokeWidth={5} strokeLinecap="round" />
          <path
            ref={arc}
            d={arcPath(100, 100, 78, 150, 390)}
            fill="none"
            stroke={ACCENT_HEX[ev.accent]}
            strokeWidth={5}
            strokeLinecap="round"
            pathLength={100}
            strokeDasharray={100}
            strokeDashoffset={100}
          />
          <line ref={needle} x1={100} y1={100} x2={100} y2={162} stroke={ACCENT_HEX[ev.accent]} strokeWidth={2.5} />
          <circle cx={100} cy={100} r={4} fill={ACCENT_HEX[ev.accent]} />
          <text ref={val} x={100} y={132} textAnchor="middle" className="tabnum"
                fontSize={22} fontWeight={800} fill={ACCENT_HEX[ev.accent]}>0%</text>
        </svg>
        {ev.label && <div className="text-center font-mono text-[9px] uppercase tracking-widest text-muted">{ev.label}</div>}
      </div>
    </Beat>
  )
}

function arcPath(cx: number, cy: number, r: number, a0: number, a1: number) {
  const p = (a: number) => [cx + r * Math.cos((a * Math.PI) / 180), cy + r * Math.sin((a * Math.PI) / 180)]
  const [x0, y0] = p(a0)
  const [x1, y1] = p(a1)
  const large = a1 - a0 > 180 ? 1 : 0
  return `M ${x0} ${y0} A ${r} ${r} 0 ${large} 1 ${x1} ${y1}`
}

/** donut — percentage ring */
export function Donut({ ev, clock }: { ev: TimelineEvent; clock: React.MutableRefObject<number> }) {
  const arc = useRef<SVGCircleElement>(null)
  useFrame(clock, (t) => {
    const p = ease.clamp01((t - ev.t0) / 1.0)
    if (arc.current) arc.current.style.strokeDashoffset = `${100 - 100 * ((ev.value ?? 96) / 100) * ease.out(p)}`
  }, [ev.id])
  const C = 2 * Math.PI * 54
  return (
    <Beat ev={ev}>
      <div className="glass relative rounded-xl p-3">
        <svg viewBox="0 0 140 140" className="w-full">
          <circle cx={70} cy={70} r={54} fill="none" stroke="rgba(255,255,255,.1)" strokeWidth={9} />
          <circle
            ref={arc}
            cx={70} cy={70} r={54} fill="none"
            stroke={ACCENT_HEX[ev.accent]} strokeWidth={9} strokeLinecap="round"
            strokeDasharray={C} strokeDashoffset={C}
            transform="rotate(-90 70 70)"
            style={{ transition: 'none' }}
          />
          <SvgCounter clock={clock} ev={ev} x={70} y={78} />
        </svg>
        <div className="mt-1 text-center font-mono text-[9px] uppercase tracking-widest text-muted">{ev.label}</div>
      </div>
    </Beat>
  )
}

/** quadrant — cost/speed scatter with frontier curve */
export function Quadrant({ ev, clock }: { ev: TimelineEvent; clock: React.MutableRefObject<number> }) {
  const curve = useRef<SVGPathElement>(null)
  const dot = useRef<SVGGElement>(null)
  useFrame(clock, (t) => {
    const p = ease.out(ease.clamp01((t - ev.t0) / 0.8))
    if (curve.current) curve.current.style.strokeDashoffset = `${100 - 100 * p}`
    if (dot.current) dot.current.style.opacity = p > 0.5 ? '1' : '0'
  }, [ev.id])
  const pts = Array.from({ length: 24 }, (_, i) => {
    const q = i / 23
    return [16 + q * 268, 148 - Math.pow(1 - q, 1.7) * 128]
  })
  const d = pts.map(([x, y], i) => `${i ? 'L' : 'M'} ${x.toFixed(1)} ${y.toFixed(1)}`).join(' ')
  const [ax, ay] = ev.anchor ?? [0.72, 0.4]
  return (
    <Beat ev={ev}>
      <div className="glass relative rounded-xl p-3">
        <Kicker accent={ev.accent}>{ev.title}</Kicker>
        <svg viewBox="0 0 300 170" className="w-full">
          {[0.2, 0.4, 0.6, 0.8].map((g) => (
            <g key={g} stroke="rgba(255,255,255,.07)">
              <line x1={16 + 268 * g} y1={16} x2={16 + 268 * g} y2={148} />
              <line x1={16} y1={16 + 132 * g} x2={284} y2={16 + 132 * g} />
            </g>
          ))}
          <line x1={16} y1={148} x2={284} y2={148} stroke="rgba(255,255,255,.35)" />
          <line x1={16} y1={16} x2={16} y2={148} stroke="rgba(255,255,255,.35)" />
          <path ref={curve} d={d} fill="none" stroke={ACCENT_HEX[ev.accent]} strokeWidth={1.6}
                pathLength={100} strokeDasharray={100} strokeDashoffset={100} />
          <g ref={dot} style={{ opacity: 0 }}>
            <circle cx={16 + 268 * ax} cy={16 + 132 * ay} r={4.5} fill={ACCENT_HEX[ev.accent]} />
            <circle cx={16 + 268 * ax} cy={16 + 132 * ay} r={10} fill="none"
                    stroke={ACCENT_HEX[ev.accent]} strokeWidth={1} opacity={0.6} />
          </g>
        </svg>
        <div className="space-y-0.5">
          {ev.items?.map((it, i) => (
            <div key={it.label} className="flex justify-between font-mono text-[9px]">
              <span className={i === 0 ? 'text-paper' : 'text-muted'}>— {it.label}</span>
              <span className="text-muted">{it.value}</span>
            </div>
          ))}
        </div>
      </div>
    </Beat>
  )
}

/** equation / chapter / caption — typographic beats */
export function Equation({ ev, clock }: { ev: TimelineEvent; clock: React.MutableRefObject<number> }) {
  const { local } = useBeat(clock, ev)
  const rule = useRef<HTMLDivElement>(null)
  useFrame(clock, () => {
    if (rule.current) rule.current.style.transform = `scaleX(${0.72 * ease.out(local.current)})`
  }, [ev.id])
  return (
    <Beat ev={ev}>
      <Kicker accent={ev.accent}>PROOF</Kicker>
      <div className="font-display text-[26px] font-extrabold leading-tight text-paper">{ev.title}</div>
      <div className="mt-1 font-mono text-[12px]" style={{ color: ACCENT_HEX[ev.accent] }}>{ev.sub}</div>
      <div ref={rule} className="mt-2 h-[1.5px] w-full origin-left" style={{ background: ACCENT_HEX[ev.accent] }} />
    </Beat>
  )
}

/** bracket — HUD frame that draws around a measured region of the plate */
export function Bracket({ ev, clock }: { ev: TimelineEvent; clock: React.MutableRefObject<number> }) {
  const { local } = useBeat(clock, ev)
  const [x, y, w, h] = ev.box
  const ref = useRef<SVGSVGElement>(null)
  useFrame(clock, () => {
    const p = ease.out(local.current)
    ref.current?.style.setProperty('--p', String(p))
    const g = ref.current
    if (g) {
      g.querySelectorAll<SVGPathElement>('path.frame').forEach((el) => {
        el.style.strokeDashoffset = `${100 - 100 * p}`
      })
      const tag = g.querySelector<SVGGElement>('g.tag')
      if (tag) tag.style.opacity = p > 0.55 ? '1' : '0'
      const cross = g.querySelector<SVGGElement>('g.cross')
      if (cross) cross.style.opacity = p > 0.8 ? '1' : '0'
    }
  }, [ev.id])

  return (
    <svg ref={ref} className={svg()} viewBox="0 0 1280 720" preserveAspectRatio="none">
      <BracketFrame x={x * 1280} y={y * 720} w={w * 1280} h={h * 720} color={ACCENT_HEX[ev.accent]} />
      {ev.title && (
        <g className="tag" style={{ opacity: 0 }}>
          <rect x={x * 1280} y={y * 720 - 24} width={Math.min(260, ev.title.length * 8 + 20)} height={18}
                fill="rgba(8,12,22,.92)" />
          <rect x={x * 1280} y={y * 720 - 24} width={3} height={18} fill={ACCENT_HEX[ev.accent]} />
          <text x={x * 1280 + 9} y={y * 720 - 11} fontSize={10.5} fontWeight={700} letterSpacing={1.4}
                fill={ACCENT_HEX[ev.accent]} fontFamily="monospace">
            {ev.title.toUpperCase()}
          </text>
        </g>
      )}
      {ev.anchor && (
        <g className="cross" style={{ opacity: 0 }} stroke={ACCENT_HEX[ev.accent]} strokeWidth={1.2}>
          <line x1={ev.anchor[0] * 1280 - 12} y1={ev.anchor[1] * 720} x2={ev.anchor[0] * 1280 - 5} y2={ev.anchor[1] * 720} />
          <line x1={ev.anchor[0] * 1280 + 5} y1={ev.anchor[1] * 720} x2={ev.anchor[0] * 1280 + 12} y2={ev.anchor[1] * 720} />
          <line x1={ev.anchor[0] * 1280} y1={ev.anchor[1] * 720 - 12} x2={ev.anchor[0] * 1280} y2={ev.anchor[1] * 720 - 5} />
          <line x1={ev.anchor[0] * 1280} y1={ev.anchor[1] * 720 + 5} x2={ev.anchor[0] * 1280} y2={ev.anchor[1] * 720 + 12} />
        </g>
      )}
    </svg>
  )
}

export function BracketFrame({ x, y, w, h, color }: { x: number; y: number; w: number; h: number; color: string }) {
  const L = Math.min(w, h) * 0.18
  const corners = [
    `M ${x} ${y + L} L ${x} ${y} L ${x + L} ${y}`,
    `M ${x + w - L} ${y} L ${x + w} ${y} L ${x + w} ${y + L}`,
    `M ${x + w} ${y + h - L} L ${x + w} ${y + h} L ${x + w - L} ${y + h}`,
    `M ${x + L} ${y + h} L ${x} ${y + h} L ${x} ${y + h - L}`,
  ]
  return (
    <g>
      {corners.map((d, i) => (
        <path key={i} className="frame" d={d} fill="none" stroke={color} strokeWidth={2}
              pathLength={100} strokeDasharray={100} strokeDashoffset={100} />
      ))}
      {Array.from({ length: 7 }, (_, i) => (
        <line key={i} x1={x + (w / 8) * (i + 1)} y1={y} x2={x + (w / 8) * (i + 1)}
              y2={y + (i % 4 === 0 ? 9 : 5)} stroke={color} strokeOpacity={0.5} strokeWidth={1} />
      ))}
    </g>
  )
}
