import { motion } from 'framer-motion'
import { useRef } from 'react'
import { ease, useFrame } from '../../lib/useFrame'
import type { TimelineEvent } from '../../lib/types'
import { ACCENT_HEX, Beat, CornerTicks, Counter, Glass, Kicker, useBeat } from './shared'

/** id_card / lower_third — nameplate with tracked kicker + headline */
export function IdCard({ ev, clock }: { ev: TimelineEvent; clock: React.MutableRefObject<number> }) {
  const { local } = useBeat(clock, ev)
  const rule = useRef<HTMLDivElement>(null)
  useFrame(clock, () => {
    if (rule.current) rule.current.style.transform = `scaleX(${0.42 * ease.out(local.current)})`
  }, [ev.id])
  return (
    <Beat ev={ev}>
      <Glass accent={ev.accent}>
        <Kicker accent={ev.accent}>{ev.kicker}</Kicker>
        <div className="font-display text-[26px] font-extrabold leading-none tracking-tight text-paper">
          {ev.title}
        </div>
        {ev.sub && <div className="mt-1.5 font-mono text-[11px] text-muted">{ev.sub}</div>}
        <div
          ref={rule}
          className="mt-3 h-[2px] w-full origin-left"
          style={{ background: ACCENT_HEX[ev.accent] }}
        />
      </Glass>
    </Beat>
  )
}

/** callout — kicker → title → hero value → key/value rows → sub */
export function Callout({ ev, clock }: { ev: TimelineEvent; clock: React.MutableRefObject<number> }) {
  const { local } = useBeat(clock, ev)
  const pointer = useRef<SVGPathElement>(null)
  const dot = useRef<SVGCircleElement>(null)
  const [ax, ay] = ev.anchor ?? [0.5, 0.5]
  useFrame(clock, () => {
    if (ev.pointer && pointer.current) {
      const p = ease.out(local.current)
      pointer.current.style.strokeDashoffset = `${100 - 100 * p}`
      if (dot.current) dot.current.style.opacity = p > 0.9 ? '1' : '0'
    }
  }, [ev.id])

  return (
    <>
      <Beat ev={ev}>
        <Glass accent={ev.accent}>
          <Kicker accent={ev.accent}>{ev.kicker}</Kicker>
          {ev.title && (
            <div className="font-display text-[22px] font-extrabold leading-tight text-paper">{ev.title}</div>
          )}
          {ev.value !== undefined && (
            <div className="mt-1 font-display text-[30px] font-extrabold leading-none tabnum"
                 style={{ color: ACCENT_HEX[ev.accent] }}>
              <Counter clock={clock} ev={ev} />
            </div>
          )}
          {!!ev.items?.length && (
            <div className="mt-2.5 space-y-1.5">
              {ev.items.slice(0, 3).map((it, i) => (
                <motion.div
                  key={it.label}
                  initial={{ opacity: 0, x: -6 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.12 + i * 0.055, duration: 0.3 }}
                  className="flex items-center justify-between gap-3 font-mono text-[11px]"
                >
                  <span className="flex min-w-0 items-center gap-2 text-muted">
                    <span className="h-[3px] w-[3px] shrink-0" style={{ background: ACCENT_HEX[ev.accent] }} />
                    <span className="truncate">{it.label}</span>
                  </span>
                  <span className="shrink-0 text-paper">{it.value}</span>
                </motion.div>
              ))}
            </div>
          )}
          {ev.sub && <div className="mt-2 font-mono text-[10.5px] leading-snug text-muted">{ev.sub}</div>}
        </Glass>
      </Beat>
      {ev.pointer && ev.anchor && (
        <svg className="pointer-events-none absolute inset-0 h-full w-full" viewBox="0 0 1280 720" preserveAspectRatio="none">
          <path
            ref={pointer}
            d={leader(ev, ax * 1280, ay * 720)}
            fill="none"
            stroke={ACCENT_HEX[ev.accent]}
            strokeWidth={1.5}
            pathLength={100}
            strokeDasharray={100}
            strokeDashoffset={100}
          />
          <circle ref={dot} cx={ax * 1280} cy={ay * 720} r={5} fill={ACCENT_HEX[ev.accent]} opacity={0} />
        </svg>
      )}
    </>
  )
}

function leader(ev: TimelineEvent, ax: number, ay: number) {
  const [bx, by, bw, bh] = ev.box
  const fx = (bx + bw / 2) * 1280
  const fy = (by + bh / 2) * 720
  const mx = fx + (ax - fx) * 0.55
  return `M ${fx} ${fy} L ${mx} ${fy} L ${mx} ${ay} L ${ax} ${ay}`
}

/** stat — big number, label, sub */
export function Stat({ ev, clock }: { ev: TimelineEvent; clock: React.MutableRefObject<number> }) {
  const { local } = useBeat(clock, ev)
  const bar = useRef<HTMLDivElement>(null)
  useFrame(clock, () => {
    if (bar.current) bar.current.style.transform = `scaleX(${ease.clamp01(local.current)})`
  }, [ev.id])
  return (
    <Beat ev={ev}>
      <Glass accent={ev.accent}>
        <div className="font-display text-[38px] font-extrabold leading-none tabnum"
             style={{ color: ACCENT_HEX[ev.accent] }}>
          <Counter clock={clock} ev={ev} />
        </div>
        {ev.label && (
          <div className="mt-2 font-mono text-[10px] font-bold uppercase tracking-[0.16em] text-muted">
            {ev.label}
          </div>
        )}
        {ev.sub && <div className="mt-1 font-mono text-[10px] text-muted">{ev.sub}</div>}
        <div ref={bar} className="mt-3 h-[2px] w-full origin-left" style={{ background: ACCENT_HEX[ev.accent] }} />
      </Glass>
    </Beat>
  )
}

/** speed_hud — delta number + streaks */
export function SpeedHud({ ev, clock }: { ev: TimelineEvent; clock: React.MutableRefObject<number> }) {
  const streaks = useRef<HTMLDivElement>(null)
  useFrame(clock, (t) => {
    if (!streaks.current) return
    streaks.current.querySelectorAll<HTMLElement>('span').forEach((el, i) => {
      const a = (t * 1.8 + i * 0.37) % 1
      el.style.transform = `translateX(${a * 300}px)`
      el.style.opacity = `${(1 - a) * 0.75}`
    })
  }, [ev.id])
  return (
    <Beat ev={ev}>
      <Glass accent={ev.accent}>
        <Kicker accent={ev.accent}>PERFORMANCE</Kicker>
        <div className="font-display text-[38px] font-extrabold leading-none tabnum"
             style={{ color: ACCENT_HEX[ev.accent] }}>
          −<Counter clock={clock} ev={ev} render={(v) => `${Math.round(v)}%`} />
        </div>
        {ev.sub && <div className="mt-1 font-mono text-[10px] text-muted">{ev.sub}</div>}
        <div ref={streaks} className="mt-3 flex gap-2 overflow-hidden">
          {Array.from({ length: 6 }).map((_, i) => (
            <span key={i} className="h-[2px] w-8 shrink-0" style={{ background: ACCENT_HEX[ev.accent] }} />
          ))}
        </div>
      </Glass>
    </Beat>
  )
}

/** corner — minimal annotation for plates that already carry big type */
export function Corner({ ev, clock }: { ev: TimelineEvent; clock: React.MutableRefObject<number> }) {
  const { local } = useBeat(clock, ev)
  const rule = useRef<HTMLDivElement>(null)
  useFrame(clock, () => {
    if (rule.current) rule.current.style.transform = `scaleX(${ease.out(local.current)})`
  }, [ev.id])
  return (
    <Beat ev={ev}>
      <div className="relative">
        <Kicker accent={ev.accent}>{ev.kicker}</Kicker>
        <div ref={rule} className="h-[1.5px] w-1/2 origin-left" style={{ background: ACCENT_HEX[ev.accent] }} />
        {ev.title && <div className="mt-1.5 font-mono text-[11px] text-paper/80">{ev.title}</div>}
      </div>
    </Beat>
  )
}

/** end_card */
export function EndCard({ ev, clock }: { ev: TimelineEvent; clock: React.MutableRefObject<number> }) {
  const ring = useRef<HTMLDivElement>(null)
  useFrame(clock, (t) => {
    if (ring.current) {
      const p = 1 + 0.06 * Math.sin(t * 2.4)
      ring.current.style.transform = `scale(${p})`
    }
  }, [ev.id])
  return (
    <Beat ev={ev}>
      <div className="glass relative overflow-hidden rounded-2xl px-6 py-5 text-center">
        <div ref={ring} className="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-full"
             style={{ background: ACCENT_HEX[ev.accent], boxShadow: `0 0 40px ${ACCENT_HEX[ev.accent]}` }}>
          <svg viewBox="0 0 24 24" className="h-5 w-5 translate-x-[1px]" fill="#05070D">
            <path d="M8 5v14l11-7z" />
          </svg>
        </div>
        <div className="font-display text-[24px] font-extrabold tracking-tight text-paper">{ev.title}</div>
        {ev.sub && <div className="mt-1 font-mono text-[11px] text-muted">{ev.sub}</div>}
        <CornerTicks accent={ev.accent} />
      </div>
    </Beat>
  )
}
