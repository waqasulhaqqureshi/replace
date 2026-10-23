import { motion } from 'framer-motion'
import { useRef } from 'react'
import { countAt, ease, fmt, useFrame } from '../../lib/useFrame'
import type { Accent, TimelineEvent } from '../../lib/types'

export const ACCENT_HEX: Record<Accent, string> = {
  cyan: '#2FE9FF', electric: '#4D6BFE', lime: '#B6FF3C',
  amber: '#FFB020', magenta: '#FF2D6F', paper: '#F2F6FF', muted: '#8FA2C4',
}

export const ENTER = 0.46
export const EXIT = 0.34

/** Local progress for a beat, read from the live clock without re-rendering. */
export function useBeat(clock: React.MutableRefObject<number>, ev: TimelineEvent) {
  const local = useRef(0)
  const alpha = useRef(1)
  useFrame(clock, (t) => {
    const pin = ease.clamp01((t - ev.t0) / ENTER)
    const pout = ease.clamp01((ev.t1 - t) / EXIT)
    local.current = pin
    alpha.current = ease.out(pin) * (pout < 1 ? ease.in(pout) : 1)
  }, [ev.id])
  return { local, alpha }
}

/** Container that positions a beat by its normalised box. */
export function Beat({
  ev, children, className = '', animate = true, style,
}: {
  ev: TimelineEvent
  children: React.ReactNode
  className?: string
  animate?: boolean
  style?: React.CSSProperties
}) {
  const [x, y, w] = ev.box
  const motionProps =
    ev.motion === 'pop'
      ? { initial: { opacity: 0, scale: 0.93 }, animate: { opacity: 1, scale: 1 },
          exit: { opacity: 0, scale: 0.97 }, transition: { duration: ENTER, ease: [0.16, 1, 0.3, 1] } }
      : ev.motion === 'wipe'
      ? { initial: { opacity: 0 }, animate: { opacity: 1 }, exit: { opacity: 0 },
          transition: { duration: 0.28 } }
      : { initial: { opacity: 0, y: 26 }, animate: { opacity: 1, y: 0 },
          exit: { opacity: 0, y: -12 }, transition: { duration: ENTER, ease: [0.16, 1, 0.3, 1] } }

  return (
    <motion.div
      className={`absolute gpu ${className}`}
      style={{ left: `${x * 100}%`, top: `${y * 100}%`, width: w > 0 ? `${w * 100}%` : undefined, ...style }}
      {...(animate ? motionProps : {})}
    >
      {children}
    </motion.div>
  )
}

export function Glass({
  accent, children, className = '', bar = true,
}: { accent: Accent; children: React.ReactNode; className?: string; bar?: boolean }) {
  return (
    <div className={`relative glass rounded-xl overflow-hidden ${className}`}>
      {bar && (
        <span
          className="absolute left-0 top-0 bottom-0 w-[3px]"
          style={{ background: ACCENT_HEX[accent], boxShadow: `0 0 14px ${ACCENT_HEX[accent]}` }}
        />
      )}
      <div className="relative p-4 pl-[18px]">{children}</div>
      <CornerTicks accent={accent} />
    </div>
  )
}

export function CornerTicks({ accent }: { accent: Accent }) {
  const c = ACCENT_HEX[accent]
  const common = 'absolute w-2 h-2 border-current'
  return (
    <div className="pointer-events-none absolute inset-0" style={{ color: c }}>
      <span className={`${common} left-0 top-0 border-l border-t`} />
      <span className={`${common} right-0 top-0 border-r border-t`} />
      <span className={`${common} left-0 bottom-0 border-l border-b`} />
      <span className={`${common} right-0 bottom-0 border-r border-b`} />
    </div>
  )
}

export function Kicker({ accent, children }: { accent: Accent; children?: string }) {
  if (!children) return null
  return (
    <div className="mb-2 flex items-center gap-2">
      <span className="h-[5px] w-[5px] shrink-0" style={{ background: ACCENT_HEX[accent] }} />
      <span
        className="truncate font-mono text-[10px] font-bold uppercase tracking-[0.18em]"
        style={{ color: ACCENT_HEX[accent] }}
      >
        {children}
      </span>
    </div>
  )
}

/** Imperative count-up: mutates textContent, never re-renders React. */
export function Counter({
  clock, ev, className = '', style, prefix = '', render,
}: {
  clock: React.MutableRefObject<number>
  ev: TimelineEvent
  className?: string
  style?: React.CSSProperties
  prefix?: string
  render?: (v: number) => string
}) {
  const ref = useRef<HTMLSpanElement>(null)
  const last = useRef(-1)
  useFrame(clock, (t) => {
    const p = ease.clamp01((t - ev.t0) / ENTER)
    const v = countAt(ev.value ?? 0, p)
    const txt = prefix + (render ? render(v) : fmt(v, ev.fmt ?? 'comma', ev.suffix ?? ''))
    if (ref.current && txt !== ref.current.textContent) {
      ref.current.textContent = txt
      last.current = v
    }
  }, [ev.id])
  return (
    <span ref={ref} className={`tabnum ${className}`} style={style}>
      {prefix}
      {render ? render(0) : fmt(0, ev.fmt ?? 'comma', ev.suffix ?? '')}
    </span>
  )
}

/** SVG-safe counter: writes into <tspan> textContent on the rAF clock. */
export function SvgCounter({
  clock, ev, x, y, className = '',
}: {
  clock: React.MutableRefObject<number>
  ev: TimelineEvent
  x: number
  y: number
  className?: string
}) {
  const ref = useRef<SVGTextElement>(null)
  useFrame(clock, (t) => {
    const p = ease.clamp01((t - ev.t0) / ENTER)
    const txt = fmt(countAt(ev.value ?? 0, p), ev.fmt ?? 'comma', ev.suffix ?? '')
    if (ref.current && ref.current.textContent !== txt) ref.current.textContent = txt
  }, [ev.id])
  return (
    <text ref={ref} x={x} y={y} textAnchor="middle" className={`tabnum ${className}`}
          fontSize={26} fontWeight={800} fill={ACCENT_HEX[ev.accent]}>
      0
    </text>
  )
}
